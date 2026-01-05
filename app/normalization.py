from __future__ import annotations

import json
import re
from typing import Any

_URL_WITH_LABEL = re.compile(r"url\s*[:=]\s*(https?://\S+)", re.IGNORECASE)
_URL_ANY = re.compile(r"https?://\S+", re.IGNORECASE)


def normalize_http_post_args(question: str | None, args: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(args or {})
    payload = normalized.get("payload")
    message = _extract_message(payload) or (question or "")

    if not normalized.get("url"):
        url = _extract_url(message) or _extract_url(question or "")
        if url:
            normalized["url"] = url

    payload_dict = payload if isinstance(payload, dict) else None
    if payload_dict is None or _payload_is_message_only(payload_dict):
        extracted = _extract_payload(message) or _extract_payload(question or "")
        if extracted is not None:
            payload_dict = extracted

    if payload_dict is None:
        payload_dict = _fallback_payload(payload, message)

    normalized["payload"] = payload_dict
    return normalized


def _extract_message(payload: object) -> str:
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str):
            return message
        return ""
    if isinstance(payload, str):
        return payload
    return ""


def _payload_is_message_only(payload: dict[str, Any]) -> bool:
    return set(payload.keys()) == {"message"}


def _extract_url(text: str) -> str | None:
    if not text:
        return None
    match = _URL_WITH_LABEL.search(text)
    if match:
        return match.group(1).rstrip(").,]")
    match = _URL_ANY.search(text)
    if not match:
        return None
    return match.group(0).rstrip(").,]")


def _extract_payload(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    lowered = text.lower()
    for marker in ("payload=", "payload:"):
        index = lowered.find(marker)
        if index == -1:
            continue
        brace_index = text.find("{", index)
        if brace_index == -1:
            continue
        try:
            parsed, _ = json.JSONDecoder().raw_decode(text[brace_index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _fallback_payload(payload: object, message: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return {"message": payload}
    if message:
        return {"message": message}
    return {}
