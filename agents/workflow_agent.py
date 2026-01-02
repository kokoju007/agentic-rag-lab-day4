from __future__ import annotations

from uuid import uuid4

from agents.base import AgentResult
from tools.registry import run_tool

ActionDict = dict[str, str | dict[str, str]]


class WorkflowAgent:
    name = "workflow"

    def run(self, question: str) -> AgentResult:
        plan, actions = self._build_plan_and_actions(question)
        requires_approval = any(action["risk"] == "high" for action in actions)
        pending_actions = []
        executed_actions = []

        for action in actions:
            if action["risk"] == "high":
                pending_actions.append(action)
                continue
            result = run_tool(action["tool"], action["args"])
            executed_actions.append(result)

        if requires_approval:
            answer = "Approval required before executing high-risk actions."
        elif actions:
            answer = "Requested actions executed."
        else:
            answer = "No actionable steps detected."

        workflow = {
            "plan": plan,
            "requires_approval": requires_approval,
            "pending_actions": pending_actions,
            "executed_actions": executed_actions,
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
        args: dict[str, str],
        risk: str,
        rationale: str,
    ) -> dict[str, str | dict[str, str]]:
        return {
            "action_id": str(uuid4()),
            "tool": tool,
            "args": args,
            "risk": risk,
            "rationale": rationale,
        }
