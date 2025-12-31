from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ask_logic import build_ask_outcome  # noqa: E402

DATASET_PATH = Path("evals/golden_routing.json")
REPORT_PATH = Path("evals/report.json")
AGENT_NAME_MAP = {
    "DocSearchAgent": "doc_search",
    "DirectAnswerAgent": "direct_answer",
}


def load_dataset(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(cases: list[dict[str, object]]) -> dict[str, object]:
    results: list[dict[str, object]] = []
    correct = 0
    for case in cases:
        expected = AGENT_NAME_MAP.get(case["expected_agent"], case["expected_agent"])
        outcome = build_ask_outcome(case["query"], trace_id="eval")
        response = outcome.response
        checks: list[bool] = [outcome.chosen_agent == expected]
        if "expected_guardrail_blocked" in case:
            checks.append(response.guardrail["blocked"] == case["expected_guardrail_blocked"])
        if "expected_human_review_needed" in case:
            human_review = response.human_review
            checks.append((human_review is not None) and human_review.needed == case["expected_human_review_needed"])
        if "expected_evidence_nonempty" in case:
            checks.append((len(response.evidence) > 0) == case["expected_evidence_nonempty"])
        is_correct = all(checks)
        if is_correct:
            correct += 1
        results.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected_agent": expected,
                "chosen_agent": outcome.chosen_agent,
                "guardrail_blocked": response.guardrail["blocked"],
                "human_review_needed": response.human_review.needed if response.human_review else None,
                "evidence_count": len(response.evidence),
                "passed": is_correct,
            }
        )

    total = len(cases)
    accuracy = round(correct / total, 3) if total else 0.0
    return {
        "summary": {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
        },
        "results": results,
    }


def write_report(report: dict[str, object], path: Path) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **report,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run routing evaluation.")
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    parser.add_argument("--smoke", action="store_true", help="Run a small subset.")
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    if args.smoke:
        dataset = dataset[:5]

    report = evaluate(dataset)
    write_report(report, REPORT_PATH)

    summary = report["summary"]
    failures = summary["total"] - summary["correct"]
    print("Routing evaluation summary")
    print(f"Total: {summary['total']}")
    print(f"Correct: {summary['correct']}")
    print(f"Accuracy: {summary['accuracy']}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
