from __future__ import annotations

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


class AskResponse(BaseModel):
    answer: str = Field(..., description="Final answer returned to the user.")
    chosen_agent: str = Field(..., description="Agent selected by the orchestrator.")
    evidence: list[str] = Field(..., description="Evidence snippets supporting the answer.")
    trace_id: str = Field(..., description="Trace identifier for observability.")
    citations: list[str] = Field(..., description="External citations, if any.")
    guardrail: dict[str, str | bool] = Field(..., description="Guardrail evaluation result.")
    usage: Usage | None = Field(default=None, description="Token usage when available.")
    model: str | None = Field(default=None, description="Model identifier when available.")
    human_review: HumanReview | None = Field(default=None, description="Human review hints.")
    build: str | None = Field(default=None, description="Build marker for debugging.")
    debug_guardrail_blocked: bool = Field(default=False, description="Debug guardrail blocked state.")
    debug_guardrail_raw: dict | None = Field(default=None, description="Raw guardrail payload for debugging.")
