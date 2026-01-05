from __future__ import annotations

from agents.base import Agent, AgentResult
from agents.direct_answer_agent import DirectAnswerAgent
from agents.doc_search_agent import DocSearchAgent
from agents.workflow_agent import WorkflowAgent


class Orchestrator:
    def __init__(
        self,
        doc_search: Agent | None = None,
        direct_answer: Agent | None = None,
        workflow: Agent | None = None,
    ) -> None:
        self._doc_search = doc_search or DocSearchAgent()
        self._direct_answer = direct_answer or DirectAnswerAgent()
        self._workflow = workflow or WorkflowAgent()

    def route(
        self,
        question: str,
        actor: object | None = None,
        trace_id: str | None = None,
    ) -> AgentResult:
        return self.route_with_choice(question, actor=actor, trace_id=trace_id)[1]

    def route_with_choice(
        self,
        question: str,
        actor: object | None = None,
        trace_id: str | None = None,
    ) -> tuple[str, AgentResult]:
        if self._is_action_request(question):
            return self._workflow.name, self._workflow.run(question, actor=actor, trace_id=trace_id)
        if self._is_doc_question(question):
            return self._doc_search.name, self._doc_search.run(
                question,
                actor=actor,
                trace_id=trace_id,
            )
        return self._direct_answer.name, self._direct_answer.run(
            question,
            actor=actor,
            trace_id=trace_id,
        )

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

    def _is_action_request(self, question: str) -> bool:
        lowered = question.lower()
        if "webhook" in lowered or "http post" in lowered or "http_post" in lowered:
            return True
        if "restart" in lowered or "재시작" in question:
            return True
        if "notify" in lowered or "알림" in question:
            return True
        ticket_requested = "ticket" in lowered and any(
            verb in lowered for verb in ("create", "make", "open", "raise")
        )
        ticket_requested = ticket_requested or (
            "티켓" in question and any(verb in question for verb in ("만들", "생성"))
        )
        if ticket_requested:
            return True
        runbook_requested = "runbook" in lowered and any(
            verb in lowered for verb in ("generate", "create", "make", "write")
        )
        runbook_requested = runbook_requested or (
            "런북" in question and any(verb in question for verb in ("작성", "만들"))
        )
        return runbook_requested
