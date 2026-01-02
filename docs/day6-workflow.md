# Day 6 Workflow + HITL Examples

## Low-risk (auto-executed)

Request:
```json
{
  "question": "VPN 장애 티켓 만들어줘"
}
```

Response:
```json
{
  "answer": "Requested actions executed.",
  "chosen_agent": "workflow",
  "evidence": [],
  "trace_id": "trace-123",
  "citations": [],
  "guardrail": {"blocked": false, "reason": "", "category": ""},
  "workflow": {
    "plan": ["Interpret request", "Execute tool: create_ticket"],
    "requires_approval": false,
    "pending_actions": [],
    "executed_actions": [
      {"tool": "create_ticket", "ok": true, "output": "Created ticket: VPN 장애 티켓 만들어줘"}
    ]
  }
}
```

## High-risk (approval required)

Request:
```json
{
  "question": "프로덕션 DB 재시작해"
}
```

Response:
```json
{
  "answer": "Approval required before executing high-risk actions.",
  "chosen_agent": "workflow",
  "evidence": [],
  "trace_id": "trace-456",
  "citations": [],
  "guardrail": {"blocked": false, "reason": "", "category": ""},
  "workflow": {
    "plan": ["Interpret request", "Execute tool: restart_service"],
    "requires_approval": true,
    "pending_actions": [
      {
        "action_id": "action-1",
        "tool": "restart_service",
        "args": {"service": "database", "environment": "production"},
        "risk": "high",
        "rationale": "Service restart requested."
      }
    ],
    "executed_actions": []
  }
}
```

Approval:
```json
{
  "trace_id": "trace-456",
  "approve": true
}
```

Approval response:
```json
{
  "trace_id": "trace-456",
  "approved": true,
  "message": "approved",
  "executed_actions": [
    {"tool": "restart_service", "ok": true, "output": "Restarted database in production."}
  ],
  "pending_actions": []
}
```
