import uuid

from django.db import models

from users.models import TelegramUser

__all__ = ["AnalysisTask", "CachedAnalysis"]


class AnalysisTask(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("processing", "Обработка"),
        ("ready", "Готово"),
        ("failed", "Ошибка"),
    ]

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    task_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
    )
    input_text = models.TextField(blank=True, default="")
    image = models.ImageField(
        upload_to="analysis/",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="pending",
    )
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Задача анализа"
        verbose_name_plural = "Задачи анализа"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Task {self.task_id} " f"[{self.status}]"


class CachedAnalysis(models.Model):
    content_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Кэшированный анализ"
        verbose_name_plural = "Кэшированные анализы"

    def __str__(self):
        return f"Cache {self.content_hash[:16]}..."
