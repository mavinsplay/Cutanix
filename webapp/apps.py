from django.apps import AppConfig

__all__ = []


class WebappConfig(AppConfig):
    default_auto_field = (
        "django.db.models.BigAutoField"
    )
    name = "webapp"
    verbose_name = "Web App"
