from django.conf import settings
import httpx

__all__ = ["PRICES", "get_price_kopeks", "create_invoice"]


def get_price_kopeks(tier, period_days):
    from payments.models import PricingPlan

    plan = PricingPlan.objects.filter(tier=tier, is_active=True).first()
    if not plan:
        return 0
    base = plan.base_price_kopeks
    multiplier = {30: 1.0, 60: 1.98, 90: 2.85}.get(period_days, 1.0)
    return int(base * multiplier)


def create_invoice(
    chat_id,
    title,
    description,
    payload,
    prices,
):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return None
    try:
        response = httpx.post(
            (f"https://api.telegram.org/" f"bot{token}/sendInvoice"),
            json={
                "chat_id": chat_id,
                "title": title,
                "description": description,
                "payload": payload,
                "provider_token": "",
                "currency": "RUB",
                "prices": prices,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None
