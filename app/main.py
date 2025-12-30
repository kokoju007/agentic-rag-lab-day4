from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, Field

from agents.orchestrator import Orchestrator

logger = logging.getLogger("app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agentic RAG Lab")


class AskRequest(BaseModel):
    question: str = Field(..., description="User question to route and answer.")


class AskResponse(BaseModel):
    answer: str = Field(..., description="Final answer returned to the user.")
    chosen_agent: str = Field(..., description="Agent selected by the orchestrator.")
    evidence: list[str] = Field(..., description="Evidence snippets supporting the answer.")
    trace_id: str = Field(..., description="Trace identifier for observability.")
    citations: list[str] = Field(..., description="External citations, if any.")


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
    logger.info(json.dumps(log_payload, ensure_ascii=False))
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, request: Request) -> AskResponse:
    orchestrator = Orchestrator()
    chosen_agent, result = orchestrator.route_with_choice(payload.question)
    request.state.chosen_agent = chosen_agent
    request.state.evidence_count = len(result.evidence)
    return AskResponse(
        answer=result.answer,
        chosen_agent=chosen_agent,
        evidence=result.evidence,
        trace_id=request.state.trace_id,
        citations=[],
    )
