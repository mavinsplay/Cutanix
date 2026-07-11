from django.contrib import admin

from analysis.models import (
    AnalysisTask,
    CachedAnalysis,
)

__all__ = []


@admin.register(AnalysisTask)
class AnalysisTaskAdmin(admin.ModelAdmin):
    list_display = (
        "task_id",
        "user",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    readonly_fields = (
        "task_id",
        "created_at",
        "updated_at",
    )


@admin.register(CachedAnalysis)
class CachedAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "content_hash",
        "created_at",
    )
    readonly_fields = ("created_at",)
