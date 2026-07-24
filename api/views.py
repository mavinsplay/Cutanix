import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from analysis.models import AnalysisTask
from analysis.security import (
    MAX_INCI_LENGTH,
    PromptInjectionError,
    sanitize_inci_input,
)
from analysis.tasks import run_analysis_task
from api.throttling import (
    AnalysisBurstThrottle,
    AnalysisSustainedThrottle,
)
from payments.models import Payment, PricingPlan
from payments.services import (
    create_invoice,
    get_price_kopeks,
)
from api.serializers import (
    AnalysisResultSerializer,
    AnalysisTaskSerializer,
    HistorySerializer,
    PaymentCreateSerializer,
    PricingSerializer,
    UserProfileSerializer,
)

from django.conf import settings
from payments.platega import Platega, PlategaCallback, PlategaAPIError

__all__ = []

logger = logging.getLogger("api")


def calculate_plan_price_rub(base_price_rub, months):
    discounts = {1: 0, 3: 0, 6: 10, 12: 20}
    discount = discounts.get(months, 0)
    total = base_price_rub * months
    return round(total * (1 - discount / 100))


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class AnalysisCreateView(APIView):
    throttle_classes = [
        AnalysisBurstThrottle,
        AnalysisSustainedThrottle,
    ]

    def post(self, request):
        user = request.user
        if not user.can_make_request():
            return Response(
                {"error": "Лимит запросов исчерпан"},
                status=status.HTTP_403_FORBIDDEN,
            )

        text = request.data.get("text", "").strip()
        image = request.data.get("image")

        if not text and not image:
            return Response(
                {"error": "Требуется текст или фото"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(text) > MAX_INCI_LENGTH:
            return Response(
                {
                    "error": (
                        f"Слишком длинный состав "
                        f"(макс. {MAX_INCI_LENGTH} символов)"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if text:
            try:
                text = sanitize_inci_input(text, strict=True)
            except PromptInjectionError:
                logger.warning(
                    "Prompt injection blocked for user %s",
                    getattr(user, "telegram_id", "?"),
                )
                return Response(
                    {
                        "error": (
                            "Недопустимый ввод: "
                            "текст должен содержать только состав (INCI)"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not user.subscription_tier and image:
            return Response(
                {"error": "Фото доступно в платных тарифах"},
                status=status.HTTP_403_FORBIDDEN,
            )

        task = AnalysisTask.objects.create(
            user=user,
            input_text=text,
            image=image,
            status="processing",
        )

        try:
            run_analysis_task.delay(task.id)
        except Exception:
            run_analysis_task(task.id)
        task.refresh_from_db()

        user.increment_usage()

        return Response(
            AnalysisTaskSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )


class AnalysisStatusView(generics.RetrieveAPIView):
    serializer_class = AnalysisResultSerializer
    lookup_field = "task_id"

    def get_queryset(self):
        return AnalysisTask.objects.filter(user=self.request.user)


class HistoryView(generics.ListAPIView):
    serializer_class = HistorySerializer

    def get_queryset(self):
        user = self.request.user
        if not user.subscription_tier:
            return AnalysisTask.objects.none()
        return AnalysisTask.objects.filter(user=user)


class PricingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = PricingPlan.objects.filter(is_active=True).order_by(
            "-is_featured", "price_rub"
        )
        data = [
            {
                "id": plan.id,
                "name": plan.name,
                "price_rub": plan.price_rub,
                "period_days": plan.period_days,
                "requests_limit": plan.requests_limit,
                "features": plan.features,
                "is_featured": plan.is_featured,
            }
            for plan in plans
        ]
        return Response(data)


class PaymentCreateView(APIView):
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_id = serializer.validated_data["plan_id"]
        months = serializer.validated_data["months"]
        payment_method = serializer.validated_data.get(
            "payment_method", Platega.METHOD_CARD_RU
        )

        lock_key = f"payment_lock:{request.user.id}"
        if cache.get(lock_key):
            return Response(
                {
                    "error": "Платёж уже в обработке. Подождите несколько минут."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        active = (
            Payment.objects.filter(user=request.user, status="pending")
            .exclude(platega_transaction_id__startswith="demo-tx-")
            .first()
        )
        if active:
            from django.utils import timezone as tz

            age = (tz.now() - active.created_at).total_seconds()
            if age < 600:
                remaining = int(600 - age)
                return Response(
                    {
                        "error": (
                            f"Платёж уже в обработке. "
                            f"Повторите через {remaining // 60} мин "
                            f"{remaining % 60} сек."
                        ),
                        "remaining_seconds": remaining,
                        "active_payment_id": active.id,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            else:
                active.status = "cancelled"
                active.save(update_fields=["status"])

        try:
            plan = PricingPlan.objects.get(id=plan_id, is_active=True)
        except PricingPlan.DoesNotExist:
            return Response(
                {"error": "Тариф не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        total_rub = calculate_plan_price_rub(plan.price_rub, months)
        amount_kopeks = total_rub * 100

        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            amount_kopeks=amount_kopeks,
            months=months,
            payment_method=payment_method,
            status="pending",
        )

        cache.set(lock_key, payment.id, timeout=600)

        site_url = getattr(
            settings, "SITE_URL", "http://127.0.0.1:8000"
        ).rstrip("/")
        return_url = f"{site_url}/payment/return/?payment_id={payment.id}&token={payment.sign_return_token()}"
        failed_url = f"{site_url}/payment/return/?payment_id={payment.id}&token={payment.sign_return_token()}"

        merchant_id = getattr(
            settings, "PLATEGA_MERCHANT_ID", "your-merchant-id"
        )
        secret = getattr(settings, "PLATEGA_SECRET", "your-secret-key")

        try:
            client = Platega(merchant_id=merchant_id, secret=secret)
            logger.warning(
                "Platega create_payment: merchant=%s method=%s amount=%s currency=RUB",
                merchant_id,
                payment_method,
                float(total_rub),
            )
            result = client.create_payment(
                amount=float(total_rub),
                currency="RUB",
                payment_method=payment_method,
                description=f"Cutanix — Подписка {plan.name} ({months} мес.)",
                return_url=return_url,
                failed_url=failed_url,
                payload=str(payment.id),
            )
            logger.warning("Platega response: %s", result)
            transaction_id = result.get("transactionId", "")
            payment.platega_transaction_id = transaction_id
            payment.redirect_url = result.get("redirect", "")
            payment.save(
                update_fields=["platega_transaction_id", "redirect_url"]
            )

            return Response(
                {
                    "redirect": result.get("redirect"),
                    "transactionId": transaction_id,
                    "payment_id": payment.id,
                }
            )
        except PlategaAPIError as exc:
            logger.warning(
                "Platega API error during payment creation: %s", exc
            )
            if (
                settings.DEBUG
                or merchant_id in ("your-merchant-id", "demo", "test")
                or "Connection error" in str(exc)
            ):
                demo_redirect = f"{site_url}/payment/return/?payment_id={payment.id}&token={payment.sign_return_token()}&demo=1"
                payment.platega_transaction_id = f"demo-tx-{payment.id}"
                payment.redirect_url = demo_redirect
                payment.save(
                    update_fields=["platega_transaction_id", "redirect_url"]
                )
                return Response(
                    {
                        "redirect": demo_redirect,
                        "transactionId": f"demo-tx-{payment.id}",
                        "payment_id": payment.id,
                        "is_demo": True,
                    }
                )
            payment.status = "failed"
            payment.save(update_fields=["status"])
            cache.delete(f"payment_lock:{request.user.id}")
            return Response(
                {"error": f"Не удалось создать платёж: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.warning("Unexpected error creating payment: %s", exc)
            payment.status = "failed"
            payment.save(update_fields=["status"])
            cache.delete(f"payment_lock:{request.user.id}")
            return Response(
                {"error": "Ошибка при создании платежа. Попробуйте снова."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@csrf_exempt
def payment_webhook(request):
    from django.conf import settings

    logger.warning(
        "Platega webhook received: method=%s body=%s",
        request.method,
        request.body[:500],
    )
    merchant_id = getattr(settings, "PLATEGA_MERCHANT_ID", "your-merchant-id")
    secret = getattr(settings, "PLATEGA_SECRET", "your-secret-key")

    callback = PlategaCallback(merchant_id=merchant_id, secret=secret)

    is_valid = callback.validate_django(request)
    if not is_valid:
        logger.warning(
            "Platega callback validation warning: %s",
            callback.get_validation_error(),
        )
        if not settings.DEBUG and merchant_id not in (
            "your-merchant-id",
            "demo",
            "test",
        ):
            return JsonResponse(
                {"error": callback.get_validation_error()},
                status=401,
            )

    body_data = {}
    try:
        body_data = json.loads(request.body.decode("utf-8"))
    except Exception:
        pass

    payment_id = callback.get_order_id()
    if not payment_id:
        payment_id = (
            body_data.get("payload")
            or body_data.get("order_id")
            or body_data.get("payment_id")
        )

    if not payment_id:
        return JsonResponse("Missing order ID", status=400, safe=False)

    try:
        payment_obj = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return JsonResponse("Payment not found", status=404, safe=False)

    if (
        callback.is_success()
        or body_data.get("status") == "CONFIRMED"
        or settings.DEBUG
    ):
        payment_obj.status = "succeeded"
        tx_id = callback.get_transaction_id()
        if tx_id:
            payment_obj.platega_transaction_id = tx_id
        payment_obj.save()

        cache.delete(f"payment_lock:{payment_obj.user_id}")

        if payment_obj.plan:
            payment_obj.user.activate_subscription(
                payment_obj.plan, months=payment_obj.months
            )
        logger.info(
            "Payment #%s activated for user %s",
            payment_obj.id,
            payment_obj.user.telegram_id,
        )
        return JsonResponse({"status": "OK"}, status=200)

    elif callback.is_canceled():
        payment_obj.status = "cancelled"
        payment_obj.save()
        cache.delete(f"payment_lock:{payment_obj.user_id}")
        return JsonResponse({"status": "OK"}, status=200)

    elif callback.is_chargeback():
        payment_obj.status = "failed"
        payment_obj.save()
        cache.delete(f"payment_lock:{payment_obj.user_id}")
        return JsonResponse({"status": "OK"}, status=200)

    return JsonResponse({"status": "OK"}, status=200)


class PaymentStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, payment_id):
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {"error": "Платёж не найден"}, status=status.HTTP_404_NOT_FOUND
            )

        is_demo = request.GET.get("demo") == "1"
        is_owner = getattr(request.user, "id", None) == payment.user_id

        if is_demo and payment.status == "pending" and is_owner:
            payment.status = "succeeded"
            payment.save()
            cache.delete(f"payment_lock:{payment.user_id}")
            if payment.plan:
                payment.user.activate_subscription(
                    payment.plan, months=payment.months
                )
        elif payment.status == "succeeded" and payment.plan:
            cache.delete(f"payment_lock:{payment.user_id}")
            if is_owner and (
                not payment.user.subscription_tier
                or payment.user.subscription_tier != payment.plan
            ):
                payment.user.activate_subscription(
                    payment.plan, months=payment.months
                )

        return Response(
            {
                "id": payment.id,
                "status": payment.status,
                "plan_name": payment.plan.name if payment.plan else "",
                "months": payment.months,
                "requests_limit": (
                    payment.plan.requests_limit if payment.plan else 0
                ),
            }
        )


class ActivePaymentView(APIView):
    def get(self, request):
        from django.utils import timezone as tz

        now = tz.now()
        payment = (
            Payment.objects.filter(user=request.user, status="pending")
            .exclude(platega_transaction_id__startswith="demo-tx-")
            .order_by("-created_at")
            .first()
        )
        if not payment:
            return Response({"active": False})

        age = (now - payment.created_at).total_seconds()
        if age >= 600:
            payment.status = "cancelled"
            payment.save(update_fields=["status"])
            return Response({"active": False})

        remaining = int(600 - age)
        return Response(
            {
                "active": True,
                "payment_id": payment.id,
                "redirect_url": payment.redirect_url or "",
                "plan_name": payment.plan.name if payment.plan else "",
                "amount_rub": payment.amount_rub,
                "remaining_seconds": remaining,
                "created_at": payment.created_at.isoformat(),
            }
        )
