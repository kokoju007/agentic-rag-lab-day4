import httpx
import pytest

from app.main import app
from app.pending_store import (
    STATUS_APPROVED,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_RUNNING,
    PendingActionStore,
)

transport = httpx.ASGITransport(app=app)


@pytest.mark.anyio
async def test_workflow_low_risk_executes_ticket() -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ask",
            json={"question": "VPN 장애 티켓 만들어줘"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["chosen_agent"] == "workflow"
    assert payload["workflow"]["requires_approval"] is False
    assert payload["workflow"]["pending_actions"] == []
    executed = payload["workflow"]["executed_actions"]
    assert any(
        action["tool"] == "create_ticket"
        for action in executed
    )


@pytest.mark.anyio
async def test_workflow_high_risk_requires_approval_and_executes_on_approve() -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        ask_response = await client.post(
            "/ask",
            json={"question": "프로덕션 DB 재시작해"},
        )
        assert ask_response.status_code == 200
        ask_payload = ask_response.json()
        assert ask_payload["chosen_agent"] == "workflow"
        assert ask_payload["workflow"]["requires_approval"] is True
        assert ask_payload["workflow"]["executed_actions"] == []
        pending = ask_payload["workflow"]["pending_actions"]
        assert any(
            action["tool"] == "restart_service"
            for action in pending
        )
        action_id = pending[0]["action_id"]

        approve_response = await client.post(
            "/approve",
            json={"action_id": action_id, "approved_by": "tester"},
        )
        assert approve_response.status_code == 200
        approve_payload = approve_response.json()
        assert approve_payload["approved"] is True
        assert approve_payload["status"] == STATUS_COMPLETED
        assert approve_payload["pending_actions"] == []
        assert any(
            action["tool"] == "restart_service" and action["ok"] is True
            for action in approve_payload["executed_actions"]
        )


@pytest.mark.anyio
async def test_approve_is_idempotent(monkeypatch, tmp_path) -> None:
    from app import main

    store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr(main, "pending_store", store)

    calls = {"count": 0}

    def fake_run_tool(tool: str, args: dict[str, str]) -> dict[str, object]:
        calls["count"] += 1
        return {"tool": tool, "ok": True, "output": "done"}

    monkeypatch.setattr(main, "run_tool", fake_run_tool)

    action = {
        "action_id": "action-1",
        "tool": "notify",
        "args": {"channel": "ops", "message": "ping"},
        "risk": "high",
        "rationale": "test",
    }
    store.save_pending("trace-1", [action])
    action_id = action["action_id"]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        payload = {"action_id": action_id, "approved_by": "tester"}
        first = await client.post("/approve", json=payload)
        second = await client.post("/approve", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["count"] == 1
    assert first.json()["executed_actions"] == second.json()["executed_actions"]


@pytest.mark.anyio
async def test_approve_marks_running_then_completed(monkeypatch, tmp_path) -> None:
    from app import main

    store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr(main, "pending_store", store)

    def fake_run_tool(tool: str, args: dict[str, str]) -> dict[str, object]:
        return {"tool": tool, "ok": True, "output": "done"}

    monkeypatch.setattr(main, "run_tool", fake_run_tool)

    action = {
        "action_id": "action-2",
        "tool": "notify",
        "args": {"channel": "ops", "message": "ping"},
        "risk": "high",
        "rationale": "test",
    }
    store.save_pending("trace-2", [action])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/approve",
            json={"action_id": "action-2", "approved_by": "tester"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == STATUS_COMPLETED
    stored = store.get_action("action-2")
    assert stored is not None
    assert stored.status == STATUS_COMPLETED


@pytest.mark.anyio
async def test_approve_running_does_not_reexecute(monkeypatch, tmp_path) -> None:
    from app import main

    store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr(main, "pending_store", store)

    calls = {"count": 0}

    def fake_run_tool(tool: str, args: dict[str, str]) -> dict[str, object]:
        calls["count"] += 1
        return {"tool": tool, "ok": True, "output": "done"}

    monkeypatch.setattr(main, "run_tool", fake_run_tool)

    action = {
        "action_id": "action-3",
        "tool": "notify",
        "args": {"channel": "ops", "message": "ping"},
        "risk": "high",
        "rationale": "test",
    }
    store.save_pending("trace-3", [action])
    store.start_action("action-3", "tester", [STATUS_PENDING])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/approve",
            json={"action_id": "action-3", "approved_by": "tester"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == STATUS_RUNNING
    assert calls["count"] == 0


@pytest.mark.anyio
async def test_approve_legacy_approved_recovery(monkeypatch, tmp_path) -> None:
    from app import main

    store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr(main, "pending_store", store)

    calls = {"count": 0}

    def fake_run_tool(tool: str, args: dict[str, str]) -> dict[str, object]:
        calls["count"] += 1
        return {"tool": tool, "ok": True, "output": "done"}

    monkeypatch.setattr(main, "run_tool", fake_run_tool)

    action = {
        "action_id": "action-4",
        "tool": "notify",
        "args": {"channel": "ops", "message": "ping"},
        "risk": "high",
        "rationale": "test",
    }
    store.save_pending("trace-4", [action])
    with store._connect() as conn:
        conn.execute(
            "UPDATE pending_actions SET status = ? WHERE id = ?",
            (STATUS_APPROVED, "action-4"),
        )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/approve",
            json={"action_id": "action-4", "approved_by": "tester"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == STATUS_COMPLETED
    assert calls["count"] == 1
