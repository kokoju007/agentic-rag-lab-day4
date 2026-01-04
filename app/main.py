from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.ask_logic import build_ask_outcome
from app.pending_store import (
    STATUS_APPROVED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    PendingActionStore,
)
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
    records = pending_store.list_actions(payload.trace_id)
    pending_actions = [record.action for record in records if record.status == STATUS_PENDING]

    if not payload.approve:
        pending_store.reject_pending(payload.trace_id, payload.approved_by)
        logger.info(
            json.dumps(
                {
                    "event": "approval",
                    "trace_id": payload.trace_id,
                    "approved": False,
                    "approved_by": payload.approved_by,
                    "pending_count": len(pending_actions),
                },
                ensure_ascii=False,
            )
        )
        return ApproveResponse(
            trace_id=payload.trace_id,
            approved=False,
            message="rejected",
            executed_actions=[],
            pending_actions=pending_actions,
        )

    executed_actions: list[ToolResult] = []
    for record in records:
        if record.status in {STATUS_COMPLETED, STATUS_FAILED, STATUS_APPROVED} and record.result:
            executed_actions.append(ToolResult(**record.result))

    pending_records = [record for record in records if record.status == STATUS_PENDING]
    if pending_records:
        pending_store.approve_pending(payload.trace_id, payload.approved_by)
        logger.info(
            json.dumps(
                {
                    "event": "approval",
                    "trace_id": payload.trace_id,
                    "approved": True,
                    "approved_by": payload.approved_by,
                    "pending_count": len(pending_records),
                },
                ensure_ascii=False,
            )
        )
        for record in pending_records:
            action = record.action
            tool = str(action.get("tool", ""))
            args = dict(action.get("args", {}))
            try:
                result = run_tool(tool, args)
            except Exception as exc:
                error = str(exc)
                result = {"tool": tool, "ok": False, "output": "", "error": error}
                pending_store.fail_action(record.action_id, result, error)
                executed_actions.append(ToolResult(**result))
                continue
            if result.get("ok", False):
                pending_store.complete_action(record.action_id, result)
            else:
                error = str(result.get("error") or "tool_failed")
                pending_store.fail_action(record.action_id, result, error)
            executed_actions.append(ToolResult(**result))

    return ApproveResponse(
        trace_id=payload.trace_id,
        approved=True,
        message="approved",
        executed_actions=executed_actions,
        pending_actions=[],
    )
