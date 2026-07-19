from django.db import models

from users.models import TelegramUser

__all__ = ["Payment", "PricingPlan"]


class PricingPlan(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        default="",
        verbose_name="Название тарифа",
    )
    price_rub = models.PositiveIntegerField(
        default=0,
        verbose_name="Цена (₽)",
    )
    period_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Дней",
    )
    requests_limit = models.PositiveIntegerField(
        default=50,
        verbose_name="Лимит запросов",
    )
    features = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Возможности",
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
        ordering = ["price_rub"]

    def __str__(self):
        featured = " ⭐" if self.is_featured else ""
        return f"{self.name} — {self.price_rub} ₽ / {self.period_days} дн.{featured}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("succeeded", "Успешно"),
        ("failed", "Ошибка"),
        ("cancelled", "Отменён"),
    ]

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    plan = models.ForeignKey(
        PricingPlan,
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
    )
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
        return f"Payment {self.telegram_payment_id} [{self.status}]"

    @property
    def amount_rub(self):
        return self.amount_kopeks // 100
