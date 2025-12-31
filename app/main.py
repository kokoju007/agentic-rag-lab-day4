from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.ask_logic import build_ask_outcome
from app.schemas import AskRequest, AskResponse

logger = logging.getLogger("app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agentic RAG Lab")


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
    return outcome.response
