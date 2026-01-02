from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class PendingEntry:
    pending_actions: list[dict[str, Any]]
    created_at: float
    executed_ids: set[str] = field(default_factory=set)


class PendingActionStore:
    def __init__(self, ttl_seconds: int = 1800, time_fn: Callable[[], float] = time.time) -> None:
        self._ttl_seconds = ttl_seconds
        self._time_fn = time_fn
        self._entries: dict[str, PendingEntry] = {}

    def save_pending(self, trace_id: str, pending_actions: list[dict[str, Any]]) -> None:
        self._purge_expired()
        if not pending_actions:
            return
        entry = self._entries.get(trace_id)
        if entry:
            entry.pending_actions = list(pending_actions)
            entry.created_at = self._time_fn()
        else:
            self._entries[trace_id] = PendingEntry(
                pending_actions=list(pending_actions),
                created_at=self._time_fn(),
            )

    def get_entry(self, trace_id: str) -> PendingEntry | None:
        self._purge_expired()
        return self._entries.get(trace_id)

    def mark_executed(self, trace_id: str, action_id: str) -> None:
        entry = self._entries.get(trace_id)
        if entry:
            entry.executed_ids.add(action_id)

    def delete(self, trace_id: str) -> None:
        self._entries.pop(trace_id, None)

    def _purge_expired(self) -> None:
        now = self._time_fn()
        expired = [
            trace_id
            for trace_id, entry in self._entries.items()
            if now - entry.created_at > self._ttl_seconds
        ]
        for trace_id in expired:
            self._entries.pop(trace_id, None)
