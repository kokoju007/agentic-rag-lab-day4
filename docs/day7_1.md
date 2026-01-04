# Day 7.1 Hotfix: /approve RUNNING state

- Added explicit execution state with `RUNNING` to avoid crash windows where approval is recorded but results are empty.
- Status flow: `PENDING` -> `RUNNING` -> `COMPLETED` or `FAILED`. Legacy `APPROVED` is treated as `PENDING` when no result exists.
- `/approve` is now action-scoped (`action_id`, `approved_by`) and idempotent:
  - `COMPLETED` returns stored result without re-execution.
  - `FAILED` returns stored error; retry only when `retry=true`.
  - `RUNNING` returns current status; no re-execution unless `force=true` and the run is stale.
- Added `started_at` to track execution start and enable stale-run recovery.
