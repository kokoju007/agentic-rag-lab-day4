from __future__ import annotations

from typing import Any


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_usage(llm_response: Any) -> dict[str, int] | None:
    if llm_response is None:
        return None

    usage = None
    if isinstance(llm_response, dict):
        usage = llm_response.get("usage") or llm_response.get("token_usage") or llm_response
    else:
        usage = getattr(llm_response, "usage", None) or getattr(llm_response, "token_usage", None)

    if not isinstance(usage, dict):
        return None

    prompt_tokens = _coerce_int(usage.get("prompt_tokens") or usage.get("input_tokens"))
    completion_tokens = _coerce_int(usage.get("completion_tokens") or usage.get("output_tokens"))
    total_tokens = _coerce_int(usage.get("total_tokens"))
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        return None

    normalized: dict[str, int] = {}
    if prompt_tokens is not None:
        normalized["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        normalized["completion_tokens"] = completion_tokens
    if total_tokens is not None:
        normalized["total_tokens"] = total_tokens
    return normalized
