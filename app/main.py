from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response

from app.ask_logic import build_ask_outcome
from app.pending_store import (
    STATUS_APPROVED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    PendingActionStore,
)
from app.schemas import ApproveRequest, ApproveResponse, AskRequest, AskResponse, ToolResult
from tools.registry import run_tool

logger = logging.getLogger("app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agentic RAG Lab")
pending_store = PendingActionStore()
RUNNING_STALE_SECONDS = 15 * 60


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
    record = pending_store.get_action(payload.action_id)
    if not record:
        raise HTTPException(status_code=404, detail="action_not_found")

    trace_id = record.trace_id
    logger.info(
        json.dumps(
            {
                "event": "approval_check",
                "trace_id": trace_id,
                "action_id": payload.action_id,
                "status": record.status,
                "approved_by": payload.approved_by,
            },
            ensure_ascii=False,
        )
    )

    completed_result = _tool_result_from_record(record)
    if record.status in {STATUS_COMPLETED, STATUS_APPROVED} and completed_result:
        return ApproveResponse(
            trace_id=trace_id or "",
            action_id=payload.action_id,
            approved=True,
            status=STATUS_COMPLETED,
            message="completed",
            executed_actions=[completed_result],
            pending_actions=[],
        )

    if record.status == STATUS_FAILED and not payload.retry:
        failed_result = completed_result or _fallback_tool_result(record)
        return ApproveResponse(
            trace_id=trace_id or "",
            action_id=payload.action_id,
            approved=True,
            status=STATUS_FAILED,
            message="failed",
            executed_actions=[failed_result],
            pending_actions=[],
        )

    if record.status == STATUS_RUNNING:
        if not payload.force or not _is_stale(record.started_at):
            return ApproveResponse(
                trace_id=trace_id or "",
                action_id=payload.action_id,
                approved=True,
                status=STATUS_RUNNING,
                message="running",
                executed_actions=[],
                pending_actions=[],
            )
        pending_store.refresh_running(payload.action_id, payload.approved_by)

    if record.status in {STATUS_PENDING, STATUS_APPROVED, STATUS_FAILED}:
        allowed = [STATUS_PENDING, STATUS_APPROVED]
        if record.status == STATUS_FAILED and payload.retry:
            allowed = [STATUS_FAILED]
        started = pending_store.start_action(payload.action_id, payload.approved_by, allowed)
        if not started:
            latest = pending_store.get_action(payload.action_id)
            if latest and latest.status == STATUS_RUNNING:
                return ApproveResponse(
                    trace_id=latest.trace_id or "",
                    action_id=payload.action_id,
                    approved=True,
                    status=STATUS_RUNNING,
                    message="running",
                    executed_actions=[],
                    pending_actions=[],
                )
            if latest and latest.status == STATUS_COMPLETED:
                latest_result = _tool_result_from_record(latest)
                return ApproveResponse(
                    trace_id=latest.trace_id or "",
                    action_id=payload.action_id,
                    approved=True,
                    status=STATUS_COMPLETED,
                    message="completed",
                    executed_actions=[latest_result] if latest_result else [],
                    pending_actions=[],
                )

    action = record.action
    tool = str(action.get("tool", ""))
    args = dict(action.get("args", {}))
    try:
        result = run_tool(tool, args)
    except Exception as exc:
        error = str(exc)
        result = {"tool": tool, "ok": False, "output": "", "error": error}
        pending_store.fail_action(payload.action_id, result, error)
        return ApproveResponse(
            trace_id=trace_id or "",
            action_id=payload.action_id,
            approved=True,
            status=STATUS_FAILED,
            message="failed",
            executed_actions=[ToolResult(**result)],
            pending_actions=[],
        )
    if result.get("ok", False):
        pending_store.complete_action(payload.action_id, result)
        status = STATUS_COMPLETED
        message = "completed"
    else:
        error = str(result.get("error") or "tool_failed")
        pending_store.fail_action(payload.action_id, result, error)
        status = STATUS_FAILED
        message = "failed"

    return ApproveResponse(
        trace_id=trace_id or "",
        action_id=payload.action_id,
        approved=True,
        status=status,
        message=message,
        executed_actions=[ToolResult(**result)],
        pending_actions=[],
    )


def _tool_result_from_record(record) -> ToolResult | None:
    if record.result:
        return ToolResult(**record.result)
    return None


def _fallback_tool_result(record) -> ToolResult:
    tool = str(record.action.get("tool", ""))
    error = record.error or "failed"
    return ToolResult(tool=tool, ok=False, output="", error=error)


def _is_stale(started_at: str | None) -> bool:
    if not started_at:
        return True
    try:
        parsed = datetime.fromisoformat(started_at)
    except ValueError:
        return True
    now = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (now - parsed).total_seconds() > RUNNING_STALE_SECONDS
