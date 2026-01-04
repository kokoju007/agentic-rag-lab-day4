# Week 1 (Day 1–7) — State Snapshot

## One-line outcome
- (예) Built an operational agentic RAG system with HITL approve + persistent pending actions + crash-safe/idempotent execution.

## What we shipped (evidence)
- Day-1: (PR/commit/doc link)
- Day-2: (PR/commit/doc link)
- Day-3: (PR/commit/doc link)
- Day-4: (PR/commit/doc link)
- Day-5: (PR/commit/doc link)
- Day-6: (PR/commit/doc link)
- Day-7: PR #5 (Day-7), PR #6 (Day-7.1), PR #7 (Day-7.2)

## Architecture (stable picture)
- Ingress: FastAPI `/ask`, `/approve`
- Orchestration: Orchestrator routes to agents
- Retrieval: (keyword/TF-IDF, docs index)
- Workflow: Plan → Act → Verify
- Tools: registry-based tool-use (e.g., http_post)
- Store: PendingActionStore (SQLite)
- Ops: trace_id logging, eval/tests, CI

## Operational invariants (must never break)
- COMPLETED actions are never re-executed.
- FAILED actions are never re-executed unless `retry=true`.
- RUNNING indicates in-progress; stale RUNNING requires `force=true`.
- DB artifacts (e.g., *.db) are never committed.

## Known risks / next fixes
- (예) Approve authorization: approved_by is a string; needs auth/roles.
- (예) Upgrade persistence to Postgres/Redis for multi-instance deployment.

## Next week goal (Week 2)
- Pick 1: Approve auth/roles OR real Slack/Jira integration OR Postgres/Redis persistence.
