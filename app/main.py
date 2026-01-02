from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.ask_logic import build_ask_outcome
from app.pending_store import PendingActionStore
from app.schemas import ApproveRequest, ApproveResponse, AskRequest, AskResponse, ToolResult
from tools.registry import run_tool

logger = logging.getLogger("app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agentic RAG Lab")
pending_store = PendingActionStore()


@app.middleware("http")
async def trace_middleware(request: Request, call_next) -> Response:
    trace_id = request.headers.get("X-Trace-Id") or str(uuid4())
    request.state.trace_id = trace_id
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    latency_ms = (time.perf_counter() - start) * 1000
    log_payload = {
        "trace_id": trace_id,
        "chosen_agent": getattr(request.state, "chosen_agent", None),
        "latency_ms": round(latency_ms, 2),
        "evidence_count": getattr(request.state, "evidence_count", None),
        "status": response.status_code,
    }
    usage = getattr(request.state, "usage", None)
    if usage:
        log_payload["usage_prompt_tokens"] = usage.get("prompt_tokens")
        log_payload["usage_completion_tokens"] = usage.get("completion_tokens")
        log_payload["usage_total_tokens"] = usage.get("total_tokens")
    logger.info(json.dumps(log_payload, ensure_ascii=False))
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, request: Request) -> AskResponse:
    outcome = build_ask_outcome(payload.question, request.state.trace_id)
    request.state.chosen_agent = outcome.chosen_agent
    request.state.evidence_count = outcome.evidence_count
    request.state.usage = outcome.usage
    workflow = outcome.response.workflow
    if workflow.requires_approval and workflow.pending_actions:
        pending_store.save_pending(
            request.state.trace_id,
            [action.model_dump() for action in workflow.pending_actions],
        )
    return outcome.response


@app.post("/approve", response_model=ApproveResponse)
def approve(payload: ApproveRequest) -> ApproveResponse:
    entry = pending_store.get_entry(payload.trace_id)
    pending_actions = entry.pending_actions if entry else []

    if not payload.approve:
        pending_store.delete(payload.trace_id)
        return ApproveResponse(
            trace_id=payload.trace_id,
            approved=False,
            message="취소됨",
            executed_actions=[],
            pending_actions=pending_actions,
        )

    executed_actions: list[ToolResult] = []
    for action in pending_actions:
        action_id = str(action.get("action_id", ""))
        if entry and action_id in entry.executed_ids:
            continue
        result = run_tool(str(action.get("tool", "")), dict(action.get("args", {})))
        executed_actions.append(ToolResult(**result))
        if entry:
            pending_store.mark_executed(payload.trace_id, action_id)

    pending_store.delete(payload.trace_id)
    return ApproveResponse(
        trace_id=payload.trace_id,
        approved=True,
        message="approved",
        executed_actions=executed_actions,
        pending_actions=[],
    )
