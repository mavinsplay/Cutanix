import json
import logging

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
from api.serializers import (  # noqa: ABS101
    AnalysisResultSerializer,
    AnalysisTaskSerializer,
    HistorySerializer,
    PaymentCreateSerializer,
    PricingSerializer,
    UserProfileSerializer,
)

__all__ = []

logger = logging.getLogger("api")


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
                {"error": ("Лимит запросов исчерпан")},
                status=(status.HTTP_403_FORBIDDEN),
            )

        text = request.data.get("text", "").strip()
        image = request.data.get("image")

        if not text and not image:
            return Response(
                {"error": ("Требуется текст или фото")},
                status=(status.HTTP_400_BAD_REQUEST),
            )

        if len(text) > MAX_INCI_LENGTH:
            return Response(
                {
                    "error": (
                        "Слишком длинный состав "
                        f"(макс. {MAX_INCI_LENGTH} "
                        "символов)"
                    )
                },
                status=(status.HTTP_400_BAD_REQUEST),
            )

        if text:
            try:
                text = sanitize_inci_input(text, strict=True)
            except PromptInjectionError:
                logger.warning(
                    "Prompt injection blocked " "for user %s",
                    getattr(user, "telegram_id", "?"),
                )
                return Response(
                    {
                        "error": (
                            "Недопустимый ввод: "
                            "текст должен содержать "
                            "только состав (INCI)"
                        )
                    },
                    status=(status.HTTP_400_BAD_REQUEST),
                )

        tier = user.subscription_tier
        if tier == "free" and image:
            return Response(
                {"error": ("Фото доступно в Pro")},
                status=(status.HTTP_403_FORBIDDEN),
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
            status=(status.HTTP_201_CREATED),
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
        if user.subscription_tier == "free":
            return AnalysisTask.objects.none()
        return AnalysisTask.objects.filter(user=user)


class PricingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = PricingPlan.objects.filter(is_active=True).order_by(
            "-is_featured", "base_price_kopeks"
        )
        pricing = []
        for plan in plans:
            base = plan.base_price_kopeks
            for days, multiplier in [(30, 1.0), (60, 1.98), (90, 2.85)]:
                price_kop = int(base * multiplier)
                pricing.append(
                    {
                        "tier": plan.tier,
                        "period_days": days,
                        "price_kopeks": price_kop,
                        "price_rub": int(price_kop / 100),
                        "features": plan.features,
                        "is_featured": plan.is_featured,
                    }
                )
        serializer = PricingSerializer(pricing, many=True)
        return Response(serializer.data)


class PaymentCreateView(APIView):
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tier = data["tier"]
        period_days = data["period_days"]
        amount = get_price_kopeks(tier, period_days)

        payment = Payment.objects.create(
            user=request.user,
            tier=tier,
            period_days=period_days,
            amount_kopeks=amount,
        )

        chat_id = request.user.telegram_id
        title = f"Cutanix {tier.upper()}"
        description = f"Подписка {tier.upper()} " f"на {period_days} дней"
        payload = json.dumps(
            {
                "payment_id": payment.id,
                "tier": tier,
                "period_days": period_days,
            }
        )
        prices = [
            {
                "label": (f"Cutanix {tier.upper()}"),
                "amount": amount,
            }
        ]

        result = create_invoice(
            chat_id,
            title,
            description,
            payload,
            prices,
        )

        if result and result.get("ok"):
            return Response({"invoice": (result["result"])})

        return Response(
            {"error": ("Не удалось создать счёт")},
            status=(status.HTTP_500_INTERNAL_SERVER_ERROR),
        )


class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        update = request.data
        query = update.get("pre_checkout_query")
        if query:
            return Response({"ok": True})

        payment = update.get("successful_payment")
        if payment:
            try:
                payload = json.loads(payment["invoice_payload"])
                payment_obj = Payment.objects.get(id=payload["payment_id"])
                payment_obj.telegram_payment_id = payment[
                    "telegram_payment_id"
                ]
                payment_obj.status = "succeeded"
                payment_obj.save()

                payment_obj.user.activate_subscription(  # noqa: E501
                    payload["tier"],
                    payload["period_days"],
                )
            except Exception as exc:
                logger.error(
                    "Payment error: %s",
                    exc,
                )

        return Response({"ok": True})
