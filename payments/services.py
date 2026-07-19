from django.conf import settings
import httpx

__all__ = ["get_price_kopeks", "create_invoice"]


def get_price_kopeks(plan):
    return plan.price_rub * 100


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
            f"https://api.telegram.org/bot{token}/sendInvoice",
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
