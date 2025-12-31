from __future__ import annotations

from agents.base import Agent, AgentResult
from agents.direct_answer_agent import DirectAnswerAgent
from agents.doc_search_agent import DocSearchAgent


class Orchestrator:
    def __init__(self, doc_search: Agent | None = None, direct_answer: Agent | None = None) -> None:
        self._doc_search = doc_search or DocSearchAgent()
        self._direct_answer = direct_answer or DirectAnswerAgent()

    def route(self, question: str) -> AgentResult:
        return self.route_with_choice(question)[1]

    def route_with_choice(self, question: str) -> tuple[str, AgentResult]:
        if self._is_doc_question(question):
            return self._doc_search.name, self._doc_search.run(question)
        return self._direct_answer.name, self._direct_answer.run(question)

    def chosen_agent(self, question: str) -> str:
        return self.route_with_choice(question)[0]

    def _is_doc_question(self, question: str) -> bool:
        lowered = question.lower()
        doc_keywords = [
            "docs",
            "readme",
            "runbook",
            "architecture",
            "decisions",
            "eval",
            "day-1",
            "day1",
            "ask",
            "/ask",
            "endpoint",
            "엔드포인트",
            "백업",
            "복구",
            "검증",
            "절차",
            "런북",
            "운영",
            "체크리스트",
            "장애",
            "원인",
            "모니터링",
            "티켓",
            "알림",
            "incident",
        ]
        return any(keyword in lowered for keyword in doc_keywords)
