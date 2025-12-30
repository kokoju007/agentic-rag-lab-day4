# Day 3 Observability

## Structured logs
Each request emits a JSON log with:
- `trace_id`
- `chosen_agent`
- `latency_ms`
- `evidence_count`
- `status`

Example:
```json
{"trace_id":"...","chosen_agent":"doc_search","latency_ms":12.4,"evidence_count":2,"status":200}
```

## Trace propagation
- Incoming `X-Trace-Id` is reused when provided.
- Otherwise a new UUID is generated.
- The response includes `X-Trace-Id` and `/ask` returns the same value in the JSON body.
