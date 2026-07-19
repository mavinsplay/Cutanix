from django.contrib import admin
from django.utils.html import format_html

from payments.models import Payment, PricingPlan

__all__ = []


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price_display",
        "period_days",
        "requests_limit",
        "is_featured_display",
        "is_active",
    )
    list_editable = ("is_active",)
    list_filter = ("is_active", "is_featured")
    ordering = ("price_rub",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "price_rub",
                    "period_days",
                    "requests_limit",
                    "is_active",
                ),
            },
        ),
        (
            "Внешний вид",
            {
                "fields": (
                    "is_featured",
                    "features",
                ),
                "description": (
                    "features — список строк в формате JSON, "
                    'например: ["До 50 запросов", "Фото этикетки"]'
                ),
            },
        ),
    )

    def price_display(self, obj):
        return f"{obj.price_rub} ₽"

    price_display.short_description = "Цена"

    def is_featured_display(self, obj):
        if obj.is_featured:
            return format_html(
                '<span style="color:#00c853;font-weight:bold;">⭐ Лучший выбор</span>'
            )
        return "—"

    is_featured_display.short_description = "Плашка"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_payment_id",
        "user",
        "plan",
        "amount_display",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    readonly_fields = ("created_at",)

    def amount_display(self, obj):
        return f"{obj.amount_rub} ₽"

    amount_display.short_description = "Сумма"
