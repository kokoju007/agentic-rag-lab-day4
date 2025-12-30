import json
from pathlib import Path

from agents.orchestrator import Orchestrator


def test_eval_routing_smoke() -> None:
    dataset_path = Path("evals/golden_routing.json")
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))[:5]
    name_map = {
        "DocSearchAgent": "doc_search",
        "DirectAnswerAgent": "direct_answer",
    }
    orchestrator = Orchestrator()

    for case in cases:
        expected = name_map[case["expected_agent"]]
        chosen, _ = orchestrator.route_with_choice(case["query"])
        assert chosen == expected
