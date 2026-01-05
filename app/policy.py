from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("policy")


class ActorRole(str, Enum):
    viewer = "viewer"
    operator = "operator"
    admin = "admin"

    @classmethod
    def from_value(cls, value: str | None) -> "ActorRole":
        if not value:
            return cls.viewer
        normalized = value.strip().lower()
        for role in cls:
            if role.value == normalized:
                return role
        return cls.viewer


ROLE_ORDER: dict[ActorRole, int] = {
    ActorRole.viewer: 0,
    ActorRole.operator: 1,
    ActorRole.admin: 2,
}


@dataclass(frozen=True)
class Actor:
    actor_id: str
    role: ActorRole


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    policy_id: str
    policy_version: str
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "evaluated_at": self.evaluated_at,
        }


@dataclass(frozen=True)
class PolicyRule:
    min_role: ActorRole
    allowed_domains: set[str] | None = None


POLICY_ID = "tool-exec"
POLICY_VERSION = "v1"


def resolve_actor(actor_id: str | None, role: str | None) -> Actor:
    resolved_id = actor_id or "anonymous"
    return Actor(actor_id=resolved_id, role=ActorRole.from_value(role))


def evaluate_tool_access(
    actor: Actor,
    tool: str,
    args: dict[str, Any],
    trace_id: str | None = None,
) -> PolicyDecision:
    rule = _resolve_rule(tool)
    if rule is None:
        decision = _decision(allowed=False, reason="no_policy")
        _log_decision(actor, tool, decision, trace_id)
        return decision
    if ROLE_ORDER.get(actor.role, 0) < ROLE_ORDER.get(rule.min_role, 0):
        decision = _decision(
            allowed=False,
            reason=f"role_required:{rule.min_role.value}",
        )
        _log_decision(actor, tool, decision, trace_id)
        return decision

    if rule.allowed_domains is not None:
        url = str(args.get("url") or "")
        hostname = _extract_hostname(url)
        if not hostname:
            decision = _decision(allowed=False, reason="missing_hostname")
            _log_decision(actor, tool, decision, trace_id)
            return decision
        if not _domain_allowed(hostname, rule.allowed_domains):
            decision = _decision(allowed=False, reason="domain_not_allowed")
            _log_decision(actor, tool, decision, trace_id)
            return decision

    decision = _decision(allowed=True, reason="allowed")
    _log_decision(actor, tool, decision, trace_id)
    return decision


def decision_entry(action_id: str, tool: str, decision: PolicyDecision) -> dict[str, Any]:
    return {"action_id": action_id, "tool": tool, "decision": decision.to_dict()}


def _resolve_rule(tool: str) -> PolicyRule | None:
    policies = _load_tool_policy_overrides()
    if tool in policies:
        return policies[tool]

    if tool == "http_post":
        return PolicyRule(
            min_role=ActorRole.operator,
            allowed_domains=_load_allowed_domains(),
        )
    if tool in {
        "kb_search",
        "create_ticket",
        "generate_runbook",
        "notify",
        "restart_service",
    }:
        return PolicyRule(min_role=ActorRole.viewer)
    return None


def _load_allowed_domains() -> set[str] | None:
    raw = os.getenv("TOOL_HTTP_POST_ALLOWED_DOMAINS", "").strip()
    if not raw:
        return None
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _load_tool_policy_overrides() -> dict[str, PolicyRule]:
    raw = os.getenv("TOOL_POLICY_RULES_JSON", "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    policies: dict[str, PolicyRule] = {}
    for tool, rule in payload.items():
        if not isinstance(rule, dict):
            continue
        min_role = ActorRole.from_value(str(rule.get("min_role") or "viewer"))
        allowed_domains = rule.get("allowed_domains")
        domains: set[str] | None = None
        if isinstance(allowed_domains, list):
            domains = {str(item).strip().lower() for item in allowed_domains if str(item).strip()}
        policies[str(tool)] = PolicyRule(min_role=min_role, allowed_domains=domains)
    return policies


def _extract_hostname(url: str) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    return parsed.hostname


def _domain_allowed(hostname: str, allowed_domains: set[str]) -> bool:
    normalized = hostname.lower().strip(".")
    for domain in allowed_domains:
        domain = domain.strip(".")
        if normalized == domain or normalized.endswith(f".{domain}"):
            return True
    return False


def _decision(allowed: bool, reason: str) -> PolicyDecision:
    evaluated_at = datetime.now(timezone.utc).isoformat()
    return PolicyDecision(
        allowed=allowed,
        reason=reason,
        policy_id=POLICY_ID,
        policy_version=POLICY_VERSION,
        evaluated_at=evaluated_at,
    )


def _log_decision(
    actor: Actor,
    tool: str,
    decision: PolicyDecision,
    trace_id: str | None,
) -> None:
    logger.info(
        json.dumps(
            {
                "event": "policy_decision",
                "trace_id": trace_id,
                "actor_id": actor.actor_id,
                "actor_role": actor.role.value,
                "tool": tool,
                "allowed": decision.allowed,
                "reason": decision.reason,
                "policy_id": decision.policy_id,
                "policy_version": decision.policy_version,
                "evaluated_at": decision.evaluated_at,
            },
            ensure_ascii=False,
        )
    )
