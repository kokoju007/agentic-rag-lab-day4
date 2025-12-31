from __future__ import annotations

from typing import Final

_SENSITIVE_KEYWORDS: Final[list[str]] = [
    "system prompt",
    "prompt",
    "dump",
    "password",
    "token",
    "악성코드",
    "malware",
]


def evaluate_question(question: str) -> dict[str, str | bool]:
    lowered = question.lower()
    for keyword in _SENSITIVE_KEYWORDS:
        if keyword.lower() in lowered:
            if keyword in {"악성코드", "malware"}:
                return {
                    "blocked": True,
                    "reason": "sensitive request detected: 악성코드",
                    "category": "cyber_abuse",
                }
            return {
                "blocked": True,
                "reason": f"sensitive request detected: {keyword}",
                "category": "prompt_injection",
            }
    return {"blocked": False, "reason": "", "category": ""}
