from __future__ import annotations

from typing import Final

_SENSITIVE_KEYWORDS: Final[list[str]] = [
    "시스템 프롬프트",
    "비밀번호",
    "토큰",
    "내부 문서 전부",
    "dump",
    "malware",
    "prompt",
    "system prompt",
    "password",
    "token",
    "악성코드",
]


def evaluate_question(question: str) -> dict[str, str | bool]:
    lowered = question.lower()
    for keyword in _SENSITIVE_KEYWORDS:
        if keyword.lower() in lowered:
            return {
                "blocked": True,
                "reason": f"sensitive request detected: {keyword}",
                "category": "prompt_injection",
            }
    return {"blocked": False, "reason": "", "category": ""}
