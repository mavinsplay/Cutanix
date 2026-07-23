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
    payment = None
    status = "pending"
    plan_name = ""
    amount_rub = 0
    status_display = "Проверяем..."

    if payment_id:
        try:
            payment = Payment.objects.get(id=payment_id)
            status = payment.status
            plan_name = payment.plan.name if payment.plan else ""
            amount_rub = payment.amount_rub

            if status == "succeeded":
                status_display = "Оплачено"
            elif status == "failed":
                status_display = "Ошибка"
            elif status == "cancelled":
                status_display = "Отменено"
            else:
                status_display = "Ожидает подтверждения"
        except Payment.DoesNotExist:
            status = "failed"
            status_display = "Платёж не найден"

    return render(
        request,
        "cutanix/payment_return.html",
        {
            "status": status,
            "plan_name": plan_name,
            "amount_rub": amount_rub,
            "status_display": status_display,
        },
    )
