from __future__ import annotations

from agents.base import Agent, AgentResult
from agents.content_creator_agent import ContentCreatorAgent
from agents.crypto_analysis_agent import CryptoAnalysisAgent
from agents.direct_answer_agent import DirectAnswerAgent
from agents.doc_search_agent import DocSearchAgent
from agents.portfolio_manager_workflow import PortfolioManagerWorkflow
from agents.workflow_agent import WorkflowAgent


class Orchestrator:
    def __init__(
        self,
        doc_search: Agent | None = None,
        direct_answer: Agent | None = None,
        workflow: Agent | None = None,
        crypto_analysis: Agent | None = None,
        content_creator: Agent | None = None,
        portfolio_workflow: Agent | None = None,
    ) -> None:
        self._doc_search = doc_search or DocSearchAgent()
        self._direct_answer = direct_answer or DirectAnswerAgent()
        self._workflow = workflow or WorkflowAgent()
        self._crypto_analysis = crypto_analysis or CryptoAnalysisAgent()
        self._content_creator = content_creator or ContentCreatorAgent()
        self._portfolio_workflow = portfolio_workflow or PortfolioManagerWorkflow()

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
        if self._is_portfolio_action_request(question):
            return (
                self._portfolio_workflow.name,
                self._portfolio_workflow.run(question, actor=actor, trace_id=trace_id),
            )
        if self._is_content_request(question):
            return (
                self._content_creator.name,
                self._content_creator.run(question, actor=actor, trace_id=trace_id),
            )
        if self._is_crypto_analysis_request(question):
            return (
                self._crypto_analysis.name,
                self._crypto_analysis.run(question, actor=actor, trace_id=trace_id),
            )
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

    def _is_crypto_analysis_request(self, question: str) -> bool:
        lowered = question.lower()
        primary = ["portfolio", "positions", "crypto"]
        secondary = ["analysis", "analyze", "summary", "risk", "concentration"]
        if any(keyword in lowered for keyword in primary):
            return True
        if any(keyword in lowered for keyword in secondary) and "positions" in lowered:
            return True
        return False

    def _is_content_request(self, question: str) -> bool:
        lowered = question.lower()
        keywords = [
            "draft",
            "thread",
            "tweet",
            "write",
            "create post",
            "x post",
            "content",
        ]
        return any(keyword in lowered for keyword in keywords)

    def _is_portfolio_action_request(self, question: str) -> bool:
        lowered = question.lower()
        keywords = [
            "rebalance",
            "rebalancing",
            "execute",
            "publish",
            "post now",
            "trade",
        ]
        return any(keyword in lowered for keyword in keywords)

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
