from __future__ import annotations

import re
from uuid import uuid4

from agents.base import AgentResult
from app.normalization import normalize_http_post_args
from app.policy import Actor, decision_entry, evaluate_tool_access, resolve_actor
from tools.registry import run_tool

ActionDict = dict[str, object]


class WorkflowAgent:
    name = "workflow"

    def run(
        self,
        question: str,
        actor: Actor | None = None,
        trace_id: str | None = None,
    ) -> AgentResult:
        plan, actions = self._build_plan_and_actions(question)
        resolved_actor = actor if isinstance(actor, Actor) else resolve_actor(None, None)
        pending_actions = []
        executed_actions = []
        policy_decisions = []
        denied_actions = 0

        for action in actions:
            tool = str(action["tool"])
            args = dict(action.get("args", {}))
            if tool == "http_post":
                args = normalize_http_post_args(question, args)
                action["args"] = args
            decision = evaluate_tool_access(resolved_actor, tool, args, trace_id=trace_id)
            action["policy"] = decision.to_dict()
            policy_decisions.append(decision_entry(action["action_id"], tool, decision))
            if not decision.allowed:
                denied_actions += 1
                continue

            if action["risk"] == "high":
                pending_actions.append(action)
                continue
            result = run_tool(tool, args)
            executed_actions.append(result)

        requires_approval = any(action["risk"] == "high" for action in pending_actions)

        if requires_approval:
            answer = "Approval required before executing high-risk actions."
        elif executed_actions:
            answer = "Requested actions executed."
        elif denied_actions:
            answer = "Requested actions were blocked by policy."
        else:
            answer = "No actionable steps detected."

        workflow = {
            "plan": plan,
            "requires_approval": requires_approval,
            "pending_actions": pending_actions,
            "executed_actions": executed_actions,
            "policy_decisions": policy_decisions,
        }
        return AgentResult(answer=answer, evidence=[], workflow=workflow)

    def _build_plan_and_actions(self, question: str) -> tuple[list[str], list[ActionDict]]:
        lowered = question.lower()
        actions: list[ActionDict] = []

        if "ticket" in lowered or "티켓" in question:
            actions.append(
                self._action(
                    tool="create_ticket",
                    args={"summary": question},
                    risk="low",
                    rationale="User requested ticket creation.",
                )
            )
        if "runbook" in lowered or "런북" in question:
            actions.append(
                self._action(
                    tool="generate_runbook",
                    args={"topic": question},
                    risk="low",
                    rationale="User asked for runbook.",
                )
            )
        if "notify" in lowered or "알림" in question:
            actions.append(
                self._action(
                    tool="notify",
                    args={"channel": "ops", "message": question},
                    risk="low",
                    rationale="User requested notification.",
                )
            )
        if "webhook" in lowered or "http post" in lowered or "http_post" in lowered:
            url = self._extract_url(question)
            args: dict[str, object] = {"payload": {"message": question}}
            if url:
                args["url"] = url
            actions.append(
                self._action(
                    tool="http_post",
                    args=args,
                    risk="high",
                    rationale="User requested webhook delivery.",
                )
            )
        if "restart" in lowered or "재시작" in question:
            risk = "high"
            is_production = "prod" in lowered or "production" in lowered or "프로덕션" in question
            environment = "production" if is_production else "unknown"
            actions.append(
                self._action(
                    tool="restart_service",
                    args={"service": "database", "environment": environment},
                    risk=risk,
                    rationale="Service restart requested.",
                )
            )
        if "kb" in lowered or "검색" in question:
            actions.append(
                self._action(
                    tool="kb_search",
                    args={"query": question},
                    risk="low",
                    rationale="User requested KB search.",
                )
            )

        plan = ["Interpret request"]
        plan.extend([f"Execute tool: {action['tool']}" for action in actions])
        return plan, actions

    def _action(
        self,
        tool: str,
        args: dict[str, object],
        risk: str,
        rationale: str,
    ) -> dict[str, object]:
        return {
            "action_id": str(uuid4()),
            "tool": tool,
            "args": args,
            "risk": risk,
            "rationale": rationale,
        }

    def _extract_url(self, question: str) -> str | None:
        match = re.search(r"https?://\\S+", question)
        if not match:
            return None
        return match.group(0).rstrip(").,]")
