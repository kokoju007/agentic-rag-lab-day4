from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., description="User question to route and answer.")


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
    trace_id: str
    approve: bool
    approved_by: str


class ApproveResponse(BaseModel):
    trace_id: str
    approved: bool
    message: str
    executed_actions: list[ToolResult]
    pending_actions: list[Action]
