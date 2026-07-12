import logging

from celery import shared_task

from analysis.models import AnalysisTask
from analysis.services import (
    analyze_inci,
    extract_inci_from_image,
)

logger = logging.getLogger("analysis")


@shared_task(bind=True, max_retries=1)
def run_analysis_task(self, task_id):
    try:
        task = AnalysisTask.objects.get(id=task_id)
    except AnalysisTask.DoesNotExist:
        return

    try:
        text = (task.input_text or "").strip()
        if not text and task.image:
            with task.image.open("rb") as f:
                raw = f.read()
            extracted = extract_inci_from_image(raw)
            if extracted:
                text = extracted.strip()
                task.input_text = text
                task.save(update_fields=["input_text"])

        if not text:
            task.status = "failed"
            task.result = {
                "error": "Не удалось извлечь состав"
            }
            task.save(
                update_fields=[
                    "status",
                    "result",
                    "updated_at",
                ]
            )
            return

        task.result = analyze_inci(text)
        task.status = "ready"
        task.save(
            update_fields=[
                "result",
                "status",
                "updated_at",
            ]
        )
    except Exception as exc:
        logger.exception(
            "Analysis task %s failed: %s", task_id, exc
        )
        try:
            task.status = "failed"
            task.result = {"error": "Ошибка анализа"}
            task.save(
                update_fields=[
                    "status",
                    "result",
                    "updated_at",
                ]
            )
        except Exception:
            pass
