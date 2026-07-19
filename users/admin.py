from django.contrib import admin

from users.models import TelegramUser

__all__ = []


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "username",
        "subscription_tier",
        "requests_used",
        "requests_limit",
        "subscription_expires",
    )
    list_filter = ("subscription_tier",)
    search_fields = (
        "telegram_id",
        "username",
        "first_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
