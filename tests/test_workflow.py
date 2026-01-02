import httpx
import pytest

from app.main import app

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
        trace_id = ask_payload["trace_id"]

        approve_response = await client.post(
            "/approve",
            json={"trace_id": trace_id, "approve": True},
        )
        assert approve_response.status_code == 200
        approve_payload = approve_response.json()
        assert approve_payload["approved"] is True
        assert approve_payload["pending_actions"] == []
        assert any(
            action["tool"] == "restart_service" and action["ok"] is True
            for action in approve_payload["executed_actions"]
        )
