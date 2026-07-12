import base64
import hashlib
import io
import json
import os
import re

from django.conf import settings
from django.core.cache import cache
from PIL import Image
import httpx

__all__ = [
    "normalize_inci",
    "content_hash",
    "get_cached_result",
    "save_to_cache",
    "analyze_inci",
    "extract_inci_from_image",
]


def normalize_inci(text):
    parts = [
        p.strip().lower()
        for p in text.replace("\n", ",").split(",")
        if p.strip()
    ]
    parts.sort()
    return ", ".join(parts)


def content_hash(text):
    normalized = normalize_inci(text)
    return hashlib.sha256(
        normalized.encode()
    ).hexdigest()


def get_cached_result(text):
    key = f"analysis:{content_hash(text)}"
    cached = cache.get(key)
    if cached:
        return cached

    from analysis.models import CachedAnalysis

    try:
        entry = (
            CachedAnalysis.objects.get(
                content_hash=content_hash(text)
            )
        )
        cache.set(
            key, entry.result, timeout=86400
        )
        return entry.result
    except CachedAnalysis.DoesNotExist:
        return None


def save_to_cache(text, result):
    key = f"analysis:{content_hash(text)}"
    cache.set(key, result, timeout=86400)

    from analysis.models import CachedAnalysis

    CachedAnalysis.objects.update_or_create(
        content_hash=content_hash(text),
        defaults={"result": result},
    )


ANALYSIS_PROMPT = (
    "Ты — эксперт по анализу косметических "
    "средств. Проанализируй состав (INCI) и "
    "верни ТОЛЬКО валидный JSON без markdown.\n\n"
    'Формат ответа:\n{\n  "safety_index": '
    "число от 1 до 10,\n"
    '  "comedogenicity": число от 0 до 10,\n'
    '  "verdict": "Можно использовать" или '
    '"Не рекомендуется",\n'
    '  "verdict_en": "safe" или "unsafe",\n'
    '  "summary": "Краткое описание на русском",\n'
    '  "components": [\n    {\n      "name": '
    '"Название ингредиента",\n'
    '      "status": "green" или "yellow" или '
    '"red",\n'
    '      "function": "Краткое описание '
    'функции",\n'
    '      "safety_note": "Примечание по '
    'безопасности"\n'
    "    }\n  ]\n}\n\n"
    "Состав для анализа:\n"
)


def call_groq_api(text):
    if not settings.GROQ_API_KEY:
        return None
    try:
        response = httpx.post(
            (
                "https://api.groq.com/openai/v1/"
                "chat/completions"
            ),
            headers={
                "Authorization": (
                    f"Bearer "
                    f"{settings.GROQ_API_KEY}"
                ),
                "Content-Type": (
                    "application/json"
                ),
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            ANALYSIS_PROMPT + text
                        ),
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = (
            response.json()["choices"][0][
                "message"
            ]["content"]
        )
        return _parse_json(content)
    except Exception:
        return None


def call_openrouter_api(text):
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    try:
        response = httpx.post(
            (
                "https://openrouter.ai/api/v1/"
                "chat/completions"
            ),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": (
                    "application/json"
                ),
                "HTTP-Referer": (
                    "https://cutanix.app"
                ),
                "X-Title": "Cutanix",
            },
            json={
                "model": os.getenv(
                    "OPENROUTER_ANALYSIS_MODEL",
                    "meta-llama/"
                    "llama-3.3-70b-instruct:free",
                ),
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            ANALYSIS_PROMPT + text
                        ),
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        response.raise_for_status()
        content = (
            response.json()["choices"][0][
                "message"
            ]["content"]
        )
        return _parse_json(content)
    except Exception:
        return None


def _parse_json(content):
    if not content:
        return None
    try:
        return json.loads(content)
    except Exception:
        pass
    fence = re.search(
        r"```(?:json)?\s*([\s\S]*?)```",
        content,
    )
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            return None
    return None


def call_together_api(text):
    if not settings.TOGETHER_API_KEY:
        return None
    try:
        response = httpx.post(
            (
                "https://api.together.xyz/v1/"
                "chat/completions"
            ),
            headers={
                "Authorization": (
                    f"Bearer "
                    f"{settings.TOGETHER_API_KEY}"
                ),
                "Content-Type": (
                    "application/json"
                ),
            },
            json={
                "model": (
                    "meta-llama/"
                    "Llama-3-70b-chat-hf"
                ),
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            ANALYSIS_PROMPT + text
                        ),
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        response.raise_for_status()
        content = (
            response.json()["choices"][0][
                "message"
            ]["content"]
        )
        return _parse_json(content)
    except Exception:
        return None


def analyze_inci(text):
    cached = get_cached_result(text)
    if cached:
        return cached

    result = call_openrouter_api(text)
    if result is None:
        result = call_groq_api(text)
    if result is None:
        result = call_together_api(text)
    if result is None:
        result = {
            "safety_index": 5,
            "comedogenicity": 5,
            "verdict": (
                "Не удалось проанализировать"
            ),
            "verdict_en": "unknown",
            "summary": (
                "Сервис временно недоступен"
            ),
            "components": [],
        }

    save_to_cache(text, result)
    return result


OCR_PROMPT = (
    "Это этикетка косметического средства. "
    "Извлеки полный список INCI (состав) — только "
    "названия ингредиентов на латинице, в том же "
    "порядке, через запятую. Игнорируй описания, "
    "предупреждения и текст на других языках. "
    "Верни ТОЛЬКО список ингредиентов, без пояснений."
)

OCR_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _prepare_image(image_bytes, max_size=1024):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(
            buf.getvalue()
        ).decode()
    except Exception:
        return None


def extract_inci_from_image(image_bytes):
    if not settings.GROQ_API_KEY:
        return None
    b64 = _prepare_image(image_bytes)
    if not b64:
        return None
    try:
        response = httpx.post(
            (
                "https://api.groq.com/openai/v1/"
                "chat/completions"
            ),
            headers={
                "Authorization": (
                    f"Bearer {settings.GROQ_API_KEY}"
                ),
                "Content-Type": (
                    "application/json"
                ),
            },
            json={
                "model": OCR_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": OCR_PROMPT,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": (
                                        "data:image/jpeg;"
                                        f"base64,{b64}"
                                    )
                                },
                            },
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 1500,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0][
            "message"
        ]["content"].strip()
    except Exception:
        return None
