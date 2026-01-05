import httpx
import pytest

from app.main import app
from app.pending_store import (
    STATUS_APPROVED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_REJECTED,
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
    assert any(action["tool"] == "create_ticket" for action in executed)


@pytest.mark.anyio
async def test_workflow_http_post_requires_approval_for_operator() -> None:
    question = "Send webhook to https://example.com for deployment"
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ask",
            json={"question": question, "actor_id": "op-1", "actor_role": "operator"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["chosen_agent"] == "workflow"
    assert payload["workflow"]["requires_approval"] is True
    pending = payload["workflow"]["pending_actions"]
    assert any(action["tool"] == "http_post" for action in pending)
    assert pending[0]["policy"]["allowed"] is True


@pytest.mark.anyio
async def test_workflow_http_post_normalizes_args() -> None:
    question = 'Send webhook url=https://example.com payload={"ping":"pong"}'
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ask",
            json={"question": question, "actor_id": "op-1", "actor_role": "operator"},
        )
    assert response.status_code == 200
    payload = response.json()
    pending = payload["workflow"]["pending_actions"]
    assert pending[0]["args"]["url"] == "https://example.com"
    assert pending[0]["args"]["payload"] == {"ping": "pong"}


@pytest.mark.anyio
async def test_workflow_http_post_blocked_for_viewer() -> None:
    question = "Send webhook to https://example.com for deployment"
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ask",
            json={"question": question, "actor_id": "viewer-1", "actor_role": "viewer"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["chosen_agent"] == "workflow"
    assert payload["workflow"]["requires_approval"] is False
    assert payload["workflow"]["pending_actions"] == []
    decisions = payload["workflow"]["policy_decisions"]
    assert any(
        entry["tool"] == "http_post" and entry["decision"]["allowed"] is False
        for entry in decisions
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
        assert any(action["tool"] == "restart_service" for action in pending)
        action_id = pending[0]["action_id"]

        approve_response = await client.post(
            "/approve",
            json={"action_id": action_id, "approved_by": "tester", "approved_role": "operator"},
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
        payload = {"action_id": action_id, "approved_by": "tester", "approved_role": "operator"}
        first = await client.post("/approve", json=payload)
        second = await client.post("/approve", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["count"] == 1
    assert first.json()["executed_actions"] == second.json()["executed_actions"]


@pytest.mark.anyio
async def test_approve_http_post_uses_normalized_args(monkeypatch, tmp_path) -> None:
    from app import main

    store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr(main, "pending_store", store)

    captured: dict[str, object] = {}

    def fake_run_tool(tool: str, args: dict[str, object]) -> dict[str, object]:
        captured["args"] = args
        return {"tool": tool, "ok": True, "output": "done"}

    monkeypatch.setattr(main, "run_tool", fake_run_tool)

    question = 'Send webhook url=https://example.com payload={"ping":"pong"}'
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        ask_response = await client.post(
            "/ask",
            json={"question": question, "actor_id": "op-1", "actor_role": "operator"},
        )
        pending = ask_response.json()["workflow"]["pending_actions"]
        action_id = pending[0]["action_id"]
        approve_response = await client.post(
            "/approve",
            json={"action_id": action_id, "approved_by": "tester", "approved_role": "operator"},
        )

    assert approve_response.status_code == 200
    payload = approve_response.json()
    assert payload["status"] == STATUS_COMPLETED
    assert captured["args"]["url"] == "https://example.com"
    assert captured["args"]["payload"] == {"ping": "pong"}


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
            json={"action_id": "action-2", "approved_by": "tester", "approved_role": "operator"},
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
    store.start_action("action-3", "tester", "operator", [STATUS_PENDING])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/approve",
            json={"action_id": "action-3", "approved_by": "tester", "approved_role": "operator"},
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
            json={"action_id": "action-4", "approved_by": "tester", "approved_role": "operator"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == STATUS_COMPLETED
    assert calls["count"] == 1


@pytest.mark.anyio
async def test_approve_failed_start_action_no_retry(monkeypatch, tmp_path) -> None:
    from app import main

    store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr(main, "pending_store", store)

    calls = {"count": 0}

    def fake_run_tool(tool: str, args: dict[str, str]) -> dict[str, object]:
        calls["count"] += 1
        return {"tool": tool, "ok": True, "output": "done"}

    monkeypatch.setattr(main, "run_tool", fake_run_tool)

    action = {
        "action_id": "action-5",
        "tool": "notify",
        "args": {"channel": "ops", "message": "ping"},
        "risk": "high",
        "rationale": "test",
    }
    store.save_pending("trace-5", [action])

    def start_action_stub(
        action_id: str,
        approved_by: str,
        approved_role: str | None,
        allowed: list[str],
    ) -> bool:
        store.fail_action(
            action_id,
            {"tool": "notify", "ok": False, "output": "", "error": "boom"},
            "boom",
        )
        return False

    monkeypatch.setattr(store, "start_action", start_action_stub)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/approve",
            json={"action_id": "action-5", "approved_by": "tester", "approved_role": "operator"},
        )

    payload = response.json()
    assert payload["status"] == STATUS_FAILED
    assert calls["count"] == 0


@pytest.mark.anyio
async def test_approve_failed_start_action_retry_executes(monkeypatch, tmp_path) -> None:
    from app import main

    store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr(main, "pending_store", store)

    calls = {"count": 0}

    def fake_run_tool(tool: str, args: dict[str, str]) -> dict[str, object]:
        calls["count"] += 1
        return {"tool": tool, "ok": True, "output": "done"}

    monkeypatch.setattr(main, "run_tool", fake_run_tool)

    action = {
        "action_id": "action-6",
        "tool": "notify",
        "args": {"channel": "ops", "message": "ping"},
        "risk": "high",
        "rationale": "test",
    }
    store.save_pending("trace-6", [action])
    original_start = store.start_action

    def start_action_stub(
        action_id: str,
        approved_by: str,
        approved_role: str | None,
        allowed: list[str],
    ) -> bool:
        if allowed == [STATUS_FAILED]:
            return original_start(action_id, approved_by, approved_role, allowed)
        store.fail_action(
            action_id,
            {"tool": "notify", "ok": False, "output": "", "error": "boom"},
            "boom",
        )
        return False

    monkeypatch.setattr(store, "start_action", start_action_stub)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/approve",
            json={
                "action_id": "action-6",
                "approved_by": "tester",
                "approved_role": "operator",
                "retry": True,
            },
        )

    payload = response.json()
    assert payload["status"] == STATUS_COMPLETED
    assert calls["count"] == 1


@pytest.mark.anyio
async def test_approve_reject_does_not_execute(monkeypatch, tmp_path) -> None:
    from app import main

    store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr(main, "pending_store", store)

    calls = {"count": 0}

    def fake_run_tool(tool: str, args: dict[str, str]) -> dict[str, object]:
        calls["count"] += 1
        return {"tool": tool, "ok": True, "output": "done"}

    monkeypatch.setattr(main, "run_tool", fake_run_tool)

    action = {
        "action_id": "action-7",
        "tool": "notify",
        "args": {"channel": "ops", "message": "ping"},
        "risk": "high",
        "rationale": "test",
    }
    store.save_pending("trace-7", [action])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/approve",
            json={
                "action_id": "action-7",
                "approved_by": "tester",
                "approved_role": "operator",
                "approve": False,
            },
        )

    payload = response.json()
    assert payload["status"] == STATUS_REJECTED
    assert payload["approved"] is False
    assert calls["count"] == 0
