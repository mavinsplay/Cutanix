from django.apps import AppConfig

__all__ = []


class AnalysisConfig(AppConfig):
    default_auto_field = (
        "django.db.models.BigAutoField"
    )
    name = "analysis"
    verbose_name = "Анализ"
