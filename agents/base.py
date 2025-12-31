from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AgentResult:
    answer: str
    evidence: list[str]
    confidence: float | None = None
    usage: dict[str, int] | None = None
    model: str | None = None


class Agent(Protocol):
    name: str

    def run(self, question: str) -> AgentResult: ...
