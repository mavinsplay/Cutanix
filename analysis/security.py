import re

__all__ = [
    "PromptInjectionError",
    "MAX_INCI_LENGTH",
    "sanitize_inci_input",
    "wrap_user_data",
    "INCI_DATA_START",
    "INCI_DATA_END",
]


MAX_INCI_LENGTH = 4000

INCI_DATA_START = "<<<INCI_DATA>>>"
INCI_DATA_END = "<<<END_INCI_DATA>>>"

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_CODE_FENCE = re.compile(r"```+")

_DELIMITER_LEAK = re.compile(
    r"<<<\s*/?\s*(?:end_?)?inci_?data\s*>>>",
    re.IGNORECASE,
)

_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore\s+(?:all\s+)?(?:previous|above|prior)"
        r"\s+(?:instructions?|prompts?|rules?)",
        r"disregard\s+(?:all\s+)?(?:previous|above|prior)",
        r"forget\s+(?:all\s+)?(?:previous|above|"
        r"your)\s+(?:instructions?|rules?)",
        r"\b(?:игнорируй|забудь|проигнорируй)\b.*"
        r"(?:инструкц|правил|указан|предыдущ)",
        r"\bты\s+(?:теперь|больше не)\b",
        r"new\s+instructions?\s*:",
        r"system\s+prompt",
        r"(?:системн\w*)\s+(?:промпт|подсказк|инструкц)",
        r"\b(?:act|behave|pretend)\s+as\b",
        r"\bвед[ий]\s+себя\s+как\b",
        r"\brole\s*[:=]\s*(?:system|assistant|developer)",
        r"^\s*(?:system|assistant|developer|user)\s*:",
        r"reveal\s+(?:your|the)\s+(?:prompt|" r"instructions?|system)",
        r"(?:покажи|раскрой|выведи)\s+(?:свой|"
        r"системн\w*)\s+(?:промпт|инструкц)",
        r"\boverride\b.*\b(?:instructions?|rules?|" r"safety)\b",
        r"jailbreak",
        r"\bDAN\b\s+mode",
    )
]


class PromptInjectionError(ValueError):
    """Raised when user input contains a prompt-injection attempt."""


def _strip_dangerous(text):
    text = _CONTROL_CHARS.sub("", text)
    text = _CODE_FENCE.sub("", text)
    text = _DELIMITER_LEAK.sub("", text)
    return text


def _detect_injection(text):
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _neutralize_injection(text):
    cleaned_lines = []
    for line in text.splitlines():
        if _detect_injection(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def sanitize_inci_input(text, strict=True):
    """Clean untrusted INCI text before sending it to an LLM.

    strict=True raises PromptInjectionError on injection patterns
    (used for direct user input). strict=False silently drops the
    offending lines (used for OCR output from images).
    """
    if not text:
        return ""

    text = str(text)
    text = _strip_dangerous(text)

    if len(text) > MAX_INCI_LENGTH:
        text = text[:MAX_INCI_LENGTH]

    if _detect_injection(text):
        if strict:
            raise PromptInjectionError(
                "Обнаружена попытка внедрения инструкций"
            )
        text = _neutralize_injection(text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def wrap_user_data(text):
    """Wrap sanitized text in explicit data delimiters."""
    return f"{INCI_DATA_START}\n{text}\n{INCI_DATA_END}"
