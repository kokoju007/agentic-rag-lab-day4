from __future__ import annotations

import json
import re
from uuid import uuid4

from agents.base import AgentResult
from app.portfolio_store import PortfolioStore


class ContentCreatorAgent:
    name = "content_creator"

    def run(
        self,
        question: str,
        actor: object | None = None,
        trace_id: str | None = None,
    ) -> AgentResult:
        _ = actor
        _ = trace_id
        analysis_payload = _extract_json_payload(question)
        topic = _extract_topic(question) or "Crypto portfolio update"

        title = f"{topic}: Portfolio pulse"
        thread = _build_thread(analysis_payload, topic)
        short_post = _build_short_post(analysis_payload, topic)
        body = f"{thread}\n\nShort post:\n{short_post}"
        disclaimer = "Not financial advice. For informational purposes only."
        hashtags = _build_hashtags(analysis_payload)

        draft_id = str(uuid4())
        store = PortfolioStore()
        store.save_content_draft(
            draft_id=draft_id,
            snapshot_id=None,
            topic=topic,
            title=title,
            body=body,
            disclaimer=disclaimer,
            hashtags=hashtags,
        )

        answer = (
            f"Draft ID: {draft_id}\n"
            f"Title: {title}\n"
            f"Body:\n{body}\n"
            f"Disclaimer: {disclaimer}\n"
            f"Hashtags: {' '.join(hashtags)}"
        )
        evidence = [f"draft_id:{draft_id}", f"topic:{topic}"]
        return AgentResult(answer=answer, evidence=evidence)


def _extract_topic(question: str) -> str | None:
    match = re.search(
        r"topic:\s*(.+?)(?:\.\s*analysis:|\s*analysis:|$)",
        question,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        topic = match.group(1).strip()
        if topic:
            return topic
    for line in question.splitlines():
        lowered = line.lower()
        if "subject:" in lowered:
            return line.split(":", 1)[1].strip()
    return None


def _extract_json_payload(text: str) -> dict[str, object] | None:
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return None
    return None


def _build_thread(analysis_payload: dict[str, object] | None, topic: str) -> str:
    summary = "Portfolio highlights and risk notes."
    if analysis_payload and isinstance(analysis_payload.get("summary"), str):
        summary = analysis_payload["summary"]
    risks = analysis_payload.get("risk_checklist") if analysis_payload else None
    risk_line = ""
    if isinstance(risks, list) and risks:
        risk_line = f"Risk check: {risks[0]}"
    lines = [
        f"1/ {topic} quick take: {summary}",
        "2/ Position sizing discipline remains the focus.",
        "3/ Keep alerts on volatility and liquidity shifts.",
    ]
    if risk_line:
        lines.append(f"4/ {risk_line}")
    return "\n".join(lines)


def _build_short_post(analysis_payload: dict[str, object] | None, topic: str) -> str:
    scenario = "Balanced outlook with tight risk controls."
    if analysis_payload:
        scenarios = analysis_payload.get("scenarios")
        if isinstance(scenarios, dict) and scenarios.get("base"):
            scenario = str(scenarios["base"])
    return f"{topic}: {scenario}"


def _build_hashtags(analysis_payload: dict[str, object] | None) -> list[str]:
    tags = ["#crypto", "#portfolio", "#risk"]
    if analysis_payload and isinstance(analysis_payload.get("top_positions"), list):
        symbols = [
            item.get("symbol")
            for item in analysis_payload["top_positions"]
            if isinstance(item, dict) and item.get("symbol")
        ]
        tags.extend([f"#{symbol}" for symbol in symbols[:2]])
    return tags
