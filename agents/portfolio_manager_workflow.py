from __future__ import annotations

import re
from uuid import uuid4

from agents.base import AgentResult
from app.policy import Actor, decision_entry, evaluate_tool_access, resolve_actor

ActionDict = dict[str, object]


class PortfolioManagerWorkflow:
    name = "portfolio_manager"

    def run(
        self,
        question: str,
        actor: Actor | None = None,
        trace_id: str | None = None,
    ) -> AgentResult:
        plan, actions = self._build_plan_and_actions(question)
        resolved_actor = actor if isinstance(actor, Actor) else resolve_actor(None, None)
        pending_actions: list[ActionDict] = []
        policy_decisions: list[dict[str, object]] = []
        denied_actions = 0

        for action in actions:
            tool = str(action["tool"])
            args = dict(action.get("args", {}))
            decision = evaluate_tool_access(
                resolved_actor,
                tool,
                args,
                trace_id=trace_id,
            )
            action["policy"] = decision.to_dict()
            policy_decisions.append(decision_entry(action["action_id"], tool, decision))
            if not decision.allowed:
                denied_actions += 1
                continue
            pending_actions.append(action)

        requires_approval = bool(pending_actions)
        if requires_approval:
            answer = "Approval required before executing portfolio actions."
        elif denied_actions:
            answer = "Requested actions were blocked by policy."
        else:
            answer = "No actionable steps detected."

        workflow = {
            "plan": plan,
            "requires_approval": requires_approval,
            "pending_actions": pending_actions,
            "executed_actions": [],
            "policy_decisions": policy_decisions,
        }
        return AgentResult(answer=answer, evidence=[], workflow=workflow)

    def _build_plan_and_actions(self, question: str) -> tuple[list[str], list[ActionDict]]:
        lowered = question.lower()
        actions: list[ActionDict] = []

        if "rebalance" in lowered or "rebalancing" in lowered:
            actions.append(
                self._action(
                    tool="portfolio_rebalance_plan",
                    args={"request": question},
                    risk="high",
                    rationale="User requested portfolio rebalancing.",
                )
            )
        if "publish" in lowered or "post" in lowered:
            draft_id = self._extract_draft_id(question)
            args = {"request": question}
            if draft_id:
                args["draft_id"] = draft_id
            actions.append(
                self._action(
                    tool="publish_draft",
                    args=args,
                    risk="high",
                    rationale="User requested draft publication.",
                )
            )

        plan = ["Interpret request"]
        plan.extend(
            [f"Queue action for approval: {action['tool']}" for action in actions]
        )
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

    def _extract_draft_id(self, question: str) -> str | None:
        match = re.search(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            question,
        )
        if not match:
            return None
        return match.group(0)
