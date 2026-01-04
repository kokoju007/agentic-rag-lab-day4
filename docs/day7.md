# Day 7 Updates

- Pending actions now persist in SQLite using `PENDING_DB_PATH` (default: `pending_actions.db`).
- Added `http_post` tool to send JSON webhooks (uses `WEBHOOK_URL` when `url` is omitted).
- `/approve` requires `approved_by`, logs approval events, and is idempotent for prior approvals.
