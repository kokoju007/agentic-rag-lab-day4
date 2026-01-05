from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ActorRole = Literal["viewer", "operator", "admin"]


class AskRequest(BaseModel):
    question: str = Field(..., description="User question to route and answer.")
    actor_id: str | None = Field(default=None, description="Actor identifier.")
    actor_role: ActorRole | None = Field(default=None, description="Actor role.")


class Usage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class HumanReview(BaseModel):
    needed: bool
    reason: str
    suggested_actions: list[str]


class Action(BaseModel):
    action_id: str
    tool: str
    args: dict[str, object]
    risk: Literal["low", "medium", "high"]
    rationale: str
    policy: dict[str, object] | None = None


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    policy_id: str
    policy_version: str
    evaluated_at: str


class PolicyDecisionEntry(BaseModel):
    action_id: str
    tool: str
    decision: PolicyDecision


class ToolResult(BaseModel):
    tool: str
    ok: bool
    output: str
    error: str | None = None


class Workflow(BaseModel):
    plan: list[str]
    requires_approval: bool
    pending_actions: list[Action]
    executed_actions: list[ToolResult]
    policy_decisions: list[PolicyDecisionEntry] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: str = Field(..., description="Final answer returned to the user.")
    chosen_agent: str = Field(..., description="Agent selected by the orchestrator.")
    evidence: list[str] = Field(..., description="Evidence snippets supporting the answer.")
    trace_id: str = Field(..., description="Trace identifier for observability.")
    citations: list[str] = Field(..., description="External citations, if any.")
    guardrail: dict[str, str | bool] = Field(..., description="Guardrail evaluation result.")
    workflow: Workflow = Field(..., description="Workflow execution details.")
    usage: Usage | None = Field(default=None, description="Token usage when available.")
    model: str | None = Field(default=None, description="Model identifier when available.")
    human_review: HumanReview | None = Field(default=None, description="Human review hints.")
    build: str | None = Field(default=None, description="Build marker for debugging.")


class ApproveRequest(BaseModel):
    action_id: str
    approved_by: str
    approved_role: ActorRole | None = Field(default=None, description="Approver role.")
    approve: bool = True
    retry: bool = False
    force: bool = False


class ApproveResponse(BaseModel):
    trace_id: str
    action_id: str
    approved: bool
    status: str
    message: str
    executed_actions: list[ToolResult]
    pending_actions: list[Action]
