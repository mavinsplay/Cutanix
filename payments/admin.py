from django.contrib import admin
from django.utils.html import format_html

from payments.models import Payment, PricingPlan

__all__ = []


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = (
        "tier",
        "price_rub_display",
        "is_featured_display",
        "is_active",
    )
    list_editable = ("is_active",)
    list_filter = ("tier", "is_active", "is_featured")
    ordering = ("base_price_kopeks",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "tier",
                    "base_price_kopeks",
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

    def price_rub_display(self, obj):
        return f"{obj.price_rub:.0f} ₽"

    price_rub_display.short_description = "Цена"

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
        "tier",
        "period_days",
        "amount_kopeks",
        "status",
        "created_at",
    )
    list_filter = ("status", "tier")
    readonly_fields = ("created_at",)
