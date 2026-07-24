from django.db import models
from django.utils import timezone

__all__ = ["TelegramUser"]


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, blank=True, default="")
    first_name = models.CharField(max_length=255, blank=True, default="")
    last_name = models.CharField(max_length=255, blank=True, default="")
    photo_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Фото",
    )
    subscription_tier = models.ForeignKey(
        "payments.PricingPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Тариф",
    )
    subscription_expires = models.DateTimeField(null=True, blank=True)
    requests_used = models.PositiveIntegerField(default=0)
    requests_limit = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    class Meta:
        verbose_name = "Telegram пользователь"
        verbose_name_plural = "Telegram пользователи"

    def __str__(self):
        name = self.username or self.first_name
        tier = (
            self.subscription_tier.name if self.subscription_tier else "free"
        )
        return f"{name} ({self.telegram_id}) [{tier}]"

    @property
    def is_subscription_active(self):
        if not self.subscription_tier:
            return True
        if self.subscription_expires is None:
            return False
        return self.subscription_expires > timezone.now()

    def can_make_request(self):
        if not self.is_subscription_active:
            return False
        return self.requests_used < self.requests_limit

    def increment_usage(self):
        self.requests_used += 1
        self.save(
            update_fields=[
                "requests_used",
                "updated_at",
            ]
        )

    def reset_limits(self):
        self.requests_used = 0
        self.save(
            update_fields=[
                "requests_used",
                "updated_at",
            ]
        )

    def activate_subscription(self, plan, months=1):
        now = timezone.now()
        same_plan = self.subscription_tier_id == plan.id
        still_active = (
            self.subscription_expires and self.subscription_expires > now
        )
        if same_plan and still_active:
            self.subscription_expires += timezone.timedelta(
                days=plan.period_days * months
            )
            self.requests_limit += plan.requests_limit
        else:
            self.subscription_tier = plan
            self.requests_limit = plan.requests_limit
            self.requests_used = 0
            self.subscription_expires = now + timezone.timedelta(
                days=plan.period_days * months
            )
        self.save()
