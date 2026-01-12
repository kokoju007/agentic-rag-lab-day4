# Day-9 Retro: Crypto Portfolio Copilot

## What we built
- `crypto_analysis` agent: Portfolio summary, concentration, scenarios, and risk checklist.
- `content_creator` agent: X thread + short post draft with title, disclaimer, hashtags.
- `portfolio_manager_workflow`: Approval-only actions for rebalance/publish requests.

## /ask examples
1) Analysis
- Input: see `docs/demo/day9/ask.crypto_analysis.json`
- Expected fields: `chosen_agent=crypto_analysis`, `answer`, `evidence`, `citations=[]`, `workflow.pending_actions=[]`

2) Content draft
- Input: see `docs/demo/day9/ask.content_draft.json`
- Expected fields: `chosen_agent=content_creator`, `answer` includes draft id, `workflow.pending_actions=[]`

3) Publish request (HITL)
- Input: see `docs/demo/day9/ask.publish_request.json`
- Expected fields: `chosen_agent=portfolio_manager`, `workflow.requires_approval=true`, `workflow.pending_actions` populated

## Limitation
- `http_post` can fail in some local DNS environments with `dns_resolution_failed`.
