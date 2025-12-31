from __future__ import annotations

from dataclasses import dataclass

from agents.guardrails import evaluate_question
from agents.orchestrator import Orchestrator
from agents.usage import normalize_usage
from app.config import RETRIEVAL_CONFIDENCE_THRESHOLD
from app.schemas import AskResponse, HumanReview, Usage

_HUMAN_REVIEW_ACTIONS = [
    "Add more context (system name, timeframe, error message).",
    "Provide document name or section.",
    "Escalate to human operator if this impacts production.",
]


@dataclass(frozen=True)
class AskOutcome:
    response: AskResponse
    chosen_agent: str
    evidence_count: int
    usage: dict[str, int] | None


def _human_review_needed(reason: str) -> HumanReview:
    return HumanReview(needed=True, reason=reason, suggested_actions=list(_HUMAN_REVIEW_ACTIONS))


def _human_review_not_needed() -> HumanReview:
    return HumanReview(needed=False, reason="", suggested_actions=[])


def build_ask_outcome(question: str, trace_id: str) -> AskOutcome:
    guardrail = evaluate_question(question)
    if guardrail["blocked"]:
        response = AskResponse(
            answer="?旍箔?橃嫚 ?挫毄?€ 觳橂Μ?????嗢姷?堧嫟.",
            chosen_agent="guardrail",
            evidence=[],
            trace_id=trace_id,
            citations=[],
            guardrail=guardrail,
            usage=None,
            model=None,
            human_review=_human_review_needed("policy_blocked"),
        )
        return AskOutcome(response=response, chosen_agent="guardrail", evidence_count=0, usage=None)

    orchestrator = Orchestrator()
    chosen_agent, result = orchestrator.route_with_choice(question)
    usage_dict = normalize_usage(result.usage)
    usage = Usage(**usage_dict) if usage_dict else None
    human_review = _human_review_not_needed()
    if result.confidence is not None and result.confidence < RETRIEVAL_CONFIDENCE_THRESHOLD:
        human_review = _human_review_needed("low_retrieval_confidence")

    response = AskResponse(
        answer=result.answer,
        chosen_agent=chosen_agent,
        evidence=result.evidence,
        trace_id=trace_id,
        citations=[],
        guardrail=guardrail,
        usage=usage,
        model=result.model,
        human_review=human_review,
    )
    return AskOutcome(
        response=response,
        chosen_agent=chosen_agent,
        evidence_count=len(result.evidence),
        usage=usage_dict,
    )
