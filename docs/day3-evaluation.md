# Day 3 Evaluation

## Overview
The routing evaluation checks whether the orchestrator selects the expected agent for a query.

## Dataset
- File: `evals/golden_routing.json`
- Fields: `id`, `query`, `expected_agent`, optional `notes`
- Expected agent values use class names: `DocSearchAgent` or `DirectAnswerAgent`.

## Running
```bash
python scripts/run_eval.py
```
Smoke run for CI:
```bash
python scripts/run_eval.py --smoke
```

## Report
The runner writes `evals/report.json` with summary metrics and per-case results.

## Adding cases
Append a new JSON object to `evals/golden_routing.json` with a unique `id` and a query that exercises a routing rule.
