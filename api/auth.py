import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs

from django.conf import settings
from rest_framework import (
    authentication,
    exceptions,
)

from users.models import TelegramUser

__all__ = ["TelegramAuth"]


def validate_init_data(init_data, bot_token):
    parsed = parse_qs(init_data)
    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        return None

    check_data = sorted(f"{k}={v[0]}" for k, v in parsed.items())
    check_string = "\n".join(check_data)

    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()

    computed_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if computed_hash != received_hash:
        return None

    auth_date = int(parsed.get("auth_date", [0])[0])
    if time.time() - auth_date > 86400:
        return None

    user_data = parsed.get("user", [None])[0]
    if not user_data:
        return None

    try:
        return json.loads(user_data)
    except (json.JSONDecodeError, TypeError):
        return None


import logging

logger = logging.getLogger("api")


class TelegramAuth(authentication.BaseAuthentication):
    keyword = "tma"

    def authenticate(self, request):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        tg_user_header = request.headers.get("X-Telegram-User", "")

        logger.warning(
            "AUTH: init_data=%s",
            init_data[:50] if init_data else "EMPTY",
        )

        if not init_data:
            if settings.DEBUG:
                defaults = {
                    "username": "debug_user",
                    "first_name": "Debug",
                    "last_name": "User",
                    "photo_url": "",
                }
                telegram_id = 999999999
                if tg_user_header:
                    try:
                        tg_user = json.loads(tg_user_header)
                        telegram_id = tg_user.get("id", telegram_id)
                        defaults["username"] = tg_user.get("username", "")
                        defaults["first_name"] = tg_user.get("first_name", "")
                        defaults["last_name"] = tg_user.get("last_name", "")
                        defaults["photo_url"] = tg_user.get("photo_url", "")
                    except (json.JSONDecodeError, TypeError):
                        pass
                user, created = TelegramUser.objects.get_or_create(
                    telegram_id=telegram_id,
                    defaults=defaults,
                )
                if not created and tg_user_header:
                    update_fields = []
                    try:
                        tg_user = json.loads(tg_user_header)
                        if (
                            tg_user.get("photo_url")
                            and user.photo_url != tg_user["photo_url"]
                        ):
                            user.photo_url = tg_user["photo_url"]
                            update_fields.append("photo_url")
                        if (
                            tg_user.get("first_name")
                            and user.first_name != tg_user["first_name"]
                        ):
                            user.first_name = tg_user["first_name"]
                            update_fields.append("first_name")
                        if update_fields:
                            user.save(update_fields=update_fields)
                    except (json.JSONDecodeError, TypeError):
                        pass
                return (user, "debug")
            return None

        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            if settings.DEBUG:
                user, _ = TelegramUser.objects.get_or_create(
                    telegram_id=999999999,
                    defaults={
                        "username": "debug_user",
                        "first_name": "Debug",
                        "last_name": "User",
                    },
                )
                return (user, "debug")
            raise exceptions.AuthenticationFailed("Bot token not configured")

        user_data = validate_init_data(init_data, bot_token)

        logger.warning(
            "AUTH: user_data=%s",
            user_data,
        )

        if not user_data:
            raise exceptions.AuthenticationFailed("Invalid Telegram init data")

        telegram_id = user_data.get("id")
        if not telegram_id:
            raise exceptions.AuthenticationFailed("Missing user ID")

        photo_url = user_data.get("photo_url", "")

        user, _ = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                "username": user_data.get("username", ""),
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "photo_url": photo_url,
            },
        )

        if photo_url and user.photo_url != photo_url:
            user.photo_url = photo_url
            user.save(update_fields=["photo_url"])

        return (user, init_data)
