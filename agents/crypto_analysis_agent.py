from __future__ import annotations

import json
from uuid import uuid4

from agents.base import AgentResult
from app.portfolio_store import PortfolioStore


class CryptoAnalysisAgent:
    name = "crypto_analysis"

    def run(
        self,
        question: str,
        actor: object | None = None,
        trace_id: str | None = None,
    ) -> AgentResult:
        _ = actor
        portfolio = _extract_portfolio_json(question)
        if not portfolio:
            return AgentResult(
                answer=(
                    "No portfolio JSON detected. Provide positions and optional " "constraints."
                ),
                evidence=[],
            )

        positions = portfolio.get("positions") or []
        constraints = portfolio.get("constraints") or {}
        normalized_positions = _normalize_positions(positions)
        summary, risk_checklist, scenarios, next_actions, top_positions = _analyze_portfolio(
            normalized_positions, constraints
        )

        snapshot_id = str(uuid4())
        store = PortfolioStore()
        store.save_positions(snapshot_id, normalized_positions)
        analysis_payload = {
            "summary": summary,
            "risk_checklist": risk_checklist,
            "scenarios": scenarios,
            "next_actions": next_actions,
            "constraints": constraints,
            "top_positions": top_positions,
        }
        store.save_analysis_snapshot(snapshot_id, trace_id, analysis_payload)

        answer = _format_analysis_answer(
            summary,
            top_positions,
            scenarios,
            risk_checklist,
            next_actions,
        )
        top_symbols = ",".join([item["symbol"] for item in top_positions])
        evidence = [
            f"positions={len(normalized_positions)}",
            f"top_positions={top_symbols}",
            f"snapshot_id={snapshot_id}",
        ]
        return AgentResult(answer=answer, evidence=evidence)


def _extract_portfolio_json(question: str) -> dict[str, object] | None:
    payload = _extract_json_payload(question)
    if not isinstance(payload, dict):
        return None
    if "positions" not in payload:
        return None
    return payload


def _extract_json_payload(text: str) -> object | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _normalize_positions(positions: list[object]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for entry in positions:
        if not isinstance(entry, dict):
            continue
        symbol = str(entry.get("symbol") or "").strip()
        if not symbol:
            continue
        qty = _to_float(entry.get("qty")) or 0.0
        avg_cost = _to_float(entry.get("avg_cost"))
        notes = entry.get("notes")
        normalized.append(
            {
                "symbol": symbol,
                "qty": qty,
                "avg_cost": avg_cost,
                "notes": notes,
            }
        )
    return normalized


def _analyze_portfolio(
    positions: list[dict[str, object]],
    constraints: dict[str, object],
) -> tuple[str, list[str], dict[str, str], list[str], list[dict[str, object]]]:
    total_qty = sum(float(position.get("qty") or 0.0) for position in positions)
    sorted_positions = sorted(
        positions,
        key=lambda item: float(item.get("qty") or 0.0),
        reverse=True,
    )
    top_positions: list[dict[str, object]] = []
    for item in sorted_positions[:3]:
        qty = float(item.get("qty") or 0.0)
        pct = (qty / total_qty) * 100 if total_qty else 0.0
        top_positions.append(
            {
                "symbol": item.get("symbol"),
                "qty": qty,
                "pct": round(pct, 2),
            }
        )

    concentration = round(sum(item["pct"] for item in top_positions), 2)
    risk_mode = str(constraints.get("risk_mode") or "balanced")
    summary = (
        f"Top positions count={len(top_positions)}, "
        f"concentration(top3)={concentration}%, "
        f"risk_mode={risk_mode}."
    )

    scenarios = {
        "bull": ("Risk-on continuation lifts leaders; keep alerts on outlier rallies."),
        "base": "Sideways rotation; focus on position sizing discipline.",
        "bear": "Risk-off shock; prepare downside trims and cash buffer.",
    }
    if risk_mode.lower() == "conservative":
        scenarios["bear"] = "Risk-off shock; prioritize capital preservation and reduce exposure."

    risk_checklist = ["Confirm liquidity for top positions."]
    max_position_pct = _to_float(constraints.get("max_position_pct"))
    if max_position_pct is not None:
        over_max = [
            item["symbol"] for item in top_positions if float(item["pct"]) > float(max_position_pct)
        ]
        if over_max:
            risk_checklist.append(
                "Positions above max_position_pct " f"({max_position_pct}%): {', '.join(over_max)}."
            )
    if len(positions) < 2:
        risk_checklist.append("Portfolio is highly concentrated with fewer than 2 positions.")
    if concentration >= 80:
        risk_checklist.append("Top-3 concentration exceeds 80%; consider trimming.")

    next_actions = [
        "Review position sizing against constraints.",
        "Set rebalance triggers for over-allocated assets.",
        "Draft communication plan for market volatility.",
    ]
    return summary, risk_checklist, scenarios, next_actions, top_positions


def _format_analysis_answer(
    summary: str,
    top_positions: list[dict[str, object]],
    scenarios: dict[str, str],
    risk_checklist: list[str],
    next_actions: list[str],
) -> str:
    top_lines = ", ".join(f"{item['symbol']} {item['pct']}%" for item in top_positions) or "none"
    scenario_lines = "; ".join(f"{key}={value}" for key, value in scenarios.items())
    risk_lines = " | ".join(risk_checklist) if risk_checklist else "none"
    action_lines = " | ".join(next_actions) if next_actions else "none"
    return (
        "Crypto portfolio analysis\n"
        f"Summary: {summary}\n"
        f"Top positions: {top_lines}\n"
        f"Scenarios: {scenario_lines}\n"
        f"Risk checklist: {risk_lines}\n"
        f"Next actions: {action_lines}"
    )


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
