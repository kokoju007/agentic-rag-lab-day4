from __future__ import annotations

from agents.base import AgentResult


class DirectAnswerAgent:
    name = "direct_answer"

    def run(self, question: str) -> AgentResult:
        _ = question
        return AgentResult(answer="아직은 임시 답변만 제공할 수 있습니다.", evidence=[])
