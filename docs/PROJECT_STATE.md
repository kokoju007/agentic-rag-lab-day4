# PROJECT STATE (Single Source of Truth)

## Current milestone
- Day-7.2 merged (PR #7): approve idempotency race fix + retry guard

## Latest merged PRs
- PR #5: Day-7 (SQLite persistence + http_post + approve audit/idempotency)
- PR #6: Day-7.1 (RUNNING + started_at + crash-safety)
- PR #7: Day-7.2 (FAILED retry=false no re-exec + race fix)

## Current architecture (1-paragraph)
- Orchestrator routes requests to agents; WorkflowAgent uses Plan→Act→Verify with tool registry; PendingActionStore persists actions (SQLite); /approve gates execution; tools include http_post; trace_id enables observability.

## Operational invariants (must hold)
- Never re-execute tools on COMPLETED.
- Never re-execute FAILED unless retry=true.
- RUNNING means “in progress”; stale RUNNING requires force=true.
- pending DB artifacts must never be committed.

## Next target (Day-8)
- (Pick one) Auth/roles for approve OR real Slack/Jira integration OR Postgres/Redis persistence
