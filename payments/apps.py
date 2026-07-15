from django.apps import AppConfig

__all__ = []


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payments"
    verbose_name = "Платежи"
