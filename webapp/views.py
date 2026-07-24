from django.http import Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

__all__ = []


@require_GET
@csrf_exempt
def serve_index(request):
    return render(request, "cutanix/base.html")


@require_GET
@csrf_exempt
def payment_return(request):
    from payments.models import Payment

    payment_id = request.GET.get("payment_id")
    token = request.GET.get("token")

    if not payment_id or not token:
        raise Http404

    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        raise Http404

    data = Payment.verify_return_token(token)
    if (
        not data
        or data.get("pid") != payment.id
        or data.get("uid") != payment.user_id
    ):
        raise Http404

    status = payment.status
    status_display = "Ожидает подтверждения"
    if status == "succeeded":
        status_display = "Оплачено"
    elif status == "failed":
        status_display = "Ошибка"
    elif status == "cancelled":
        status_display = "Отменено"

    return render(
        request,
        "cutanix/payment_return.html",
        {
            "status": status,
            "status_display": status_display,
            "plan_name": payment.plan.name if payment.plan else "",
            "amount_rub": payment.amount_rub,
        },
    )
