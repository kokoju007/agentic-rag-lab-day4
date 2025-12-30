# Evaluation Plan

- **Health check**: call `GET /health` and confirm `{"status": "ok"}`.
- **Ask flow**: call `POST /ask` with a sample question and verify the response contains:
  - `answer` set to `"더미 답변"`
  - `citations` array with two items
  - `trace_id` as a non-empty string
