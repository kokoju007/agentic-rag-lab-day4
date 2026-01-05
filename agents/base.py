from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AgentResult:
    answer: str
    evidence: list[str]
    confidence: float | None = None
    usage: dict[str, int] | None = None
    model: str | None = None
    workflow: dict[str, Any] | None = None


class Agent(Protocol):
    name: str

    def run(
        self,
        question: str,
        actor: object | None = None,
        trace_id: str | None = None,
    ) -> AgentResult: ...
