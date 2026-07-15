from django.db import models

from users.models import TelegramUser

__all__ = ["Payment", "PricingPlan"]


class PricingPlan(models.Model):
    TIER_CHOICES = [
        ("pro", "Pro"),
        ("ultra", "Ultra"),
    ]

    tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        unique=True,
        verbose_name="Тариф",
    )
    base_price_kopeks = models.PositiveIntegerField(
        verbose_name="Базовая цена за 30 дней (копейки)",
    )
    features = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Возможности (список строк)",
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name='Плашка "Лучший выбор"',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
    )

    class Meta:
        verbose_name = "Тарифный план"
        verbose_name_plural = "Тарифные планы"
        ordering = ["base_price_kopeks"]

    def __str__(self):
        featured = " ⭐" if self.is_featured else ""
        return (
            f"{self.get_tier_display()} — "
            f"{self.base_price_kopeks / 100:.0f} ₽ / 30 дн."
            f"{featured}"
        )

    @property
    def price_rub(self):
        return self.base_price_kopeks / 100


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("succeeded", "Успешно"),
        ("failed", "Ошибка"),
        ("cancelled", "Отменён"),
    ]
    TIER_CHOICES = [
        ("pro", "Pro"),
        ("ultra", "Ultra"),
    ]

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    tier = models.CharField(max_length=10, choices=TIER_CHOICES)
    period_days = models.PositiveIntegerField()
    amount_kopeks = models.PositiveIntegerField()
    telegram_payment_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        default="",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.telegram_payment_id} " f"[{self.status}]"

    @property
    def amount_rub(self):
        return self.amount_kopeks / 100
