from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache

from agents.guardrails import evaluate_question
from agents.orchestrator import Orchestrator
from agents.usage import normalize_usage
from app.config import RETRIEVAL_CONFIDENCE_THRESHOLD
from app.policy import Actor, resolve_actor
from app.schemas import AskResponse, HumanReview, Usage, Workflow

_LOW_CONFIDENCE_ACTIONS = [
    "Add more context (system name, timeframe, error message).",
    "Provide document name or section.",
    "Escalate to human operator if this impacts production.",
]
_POLICY_BLOCKED_ACTIONS = [
    "Provide a benign intent.",
    "Ask for defensive/security best practices.",
    "Escalate to the security team if needed.",
]
_MISSING_CONTEXT_ACTIONS = [
    "Provide the system name.",
    "Specify the environment (prod/staging/dev).",
    "Share the timeframe, ticket/alert ID, and error message.",
]
_INCIDENT_KEYWORDS = [
    "지난주",
    "어제",
    "오늘",
    "이번주",
    "장애",
    "원인",
    "incident",
    "알림",
]
_ENV_KEYWORDS = [
    "prod",
    "production",
    "staging",
    "stage",
    "dev",
    "qa",
    "환경",
]
_SYSTEM_KEYWORDS = [
    "system",
    "service",
    "server",
    "db",
    "database",
    "시스템",
    "서비스",
    "서버",
    "데이터베이스",
]


@dataclass(frozen=True)
class AskOutcome:
    response: AskResponse
    chosen_agent: str
    evidence_count: int
    usage: dict[str, int] | None


def _human_review_needed(reason: str, suggested_actions: list[str]) -> HumanReview:
    return HumanReview(needed=True, reason=reason, suggested_actions=list(suggested_actions))


def _human_review_not_needed() -> HumanReview:
    return HumanReview(needed=False, reason="", suggested_actions=[])


def _empty_workflow() -> Workflow:
    return Workflow(
        plan=[],
        requires_approval=False,
        pending_actions=[],
        executed_actions=[],
    )


def _has_ticket_id(question: str) -> bool:
    tokens = ["ticket", "incident", "alert", "case", "티켓", "알림", "인시던트"]
    if any(token in question for token in tokens) and any(char.isdigit() for char in question):
        return True
    return False


def _has_system_or_env(question: str) -> bool:
    return any(keyword in question for keyword in _ENV_KEYWORDS + _SYSTEM_KEYWORDS)


def _needs_missing_context(question: str) -> bool:
    lowered = question.lower()
    if not any(keyword in lowered for keyword in _INCIDENT_KEYWORDS):
        return False
    if _has_ticket_id(lowered):
        return False
    if _has_system_or_env(lowered):
        return False
    return True


@lru_cache(maxsize=1)
def _resolve_build_marker() -> str:
    env_marker = os.getenv("APP_BUILD") or os.getenv("BUILD_MARKER")
    if env_marker:
        return env_marker
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


BUILD_MARKER = _resolve_build_marker()


def build_ask_outcome(question: str, trace_id: str, actor: Actor | None = None) -> AskOutcome:
    build_marker = BUILD_MARKER
    guardrail = evaluate_question(question)
    if guardrail["blocked"]:
        response = AskResponse(
            answer="보안 정책상 해당 요청은 처리할 수 없습니다.",
            chosen_agent="guardrail",
            evidence=[],
            trace_id=trace_id,
            citations=[],
            guardrail=guardrail,
            workflow=_empty_workflow(),
            usage=None,
            model=None,
            human_review=_human_review_needed("policy_blocked", _POLICY_BLOCKED_ACTIONS),
            build=build_marker,
        )
        return AskOutcome(response=response, chosen_agent="guardrail", evidence_count=0, usage=None)

    orchestrator = Orchestrator()
    resolved_actor = actor or resolve_actor(None, None)
    chosen_agent, result = orchestrator.route_with_choice(
        question,
        actor=resolved_actor,
        trace_id=trace_id,
    )
    usage_dict = normalize_usage(result.usage)
    usage = Usage(**usage_dict) if usage_dict else None
    human_review = _human_review_not_needed()
    if _needs_missing_context(question):
        human_review = _human_review_needed("missing_context", _MISSING_CONTEXT_ACTIONS)
    elif result.confidence is not None and result.confidence < RETRIEVAL_CONFIDENCE_THRESHOLD:
        human_review = _human_review_needed("low_retrieval_confidence", _LOW_CONFIDENCE_ACTIONS)

    workflow = _empty_workflow()
    if result.workflow:
        workflow = Workflow(**result.workflow)

    response = AskResponse(
        answer=result.answer,
        chosen_agent=chosen_agent,
        evidence=result.evidence,
        trace_id=trace_id,
        citations=[],
        guardrail=guardrail,
        workflow=workflow,
        usage=usage,
        model=result.model,
        human_review=human_review,
        build=build_marker,
    )
    return AskOutcome(
        response=response,
        chosen_agent=chosen_agent,
        evidence_count=len(result.evidence),
        usage=usage_dict,
    )
