from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from users.models import TelegramUser

__all__ = []


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "username",
        "tier_display",
        "requests_used",
        "requests_limit",
        "subscription_expires",
    )
    search_fields = (
        "telegram_id",
        "username",
        "first_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def tier_display(self, obj):
        if obj.subscription_tier:
            return obj.subscription_tier.name
        return "Free"

    tier_display.short_description = "Тариф"

    def save_model(self, request, obj, form, change):
        if "subscription_tier" in form.changed_data:
            plan = obj.subscription_tier
            if plan:
                obj.requests_limit = plan.requests_limit
                obj.requests_used = 0
                obj.subscription_expires = timezone.now() + timezone.timedelta(
                    days=plan.period_days
                )
            else:
                obj.requests_limit = 3
                obj.requests_used = 0
                obj.subscription_expires = None
        super().save_model(request, obj, form, change)
