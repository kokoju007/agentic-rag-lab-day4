import httpx
import pytest

from app.main import app
from app.pending_store import STATUS_COMPLETED, PendingActionStore
from app.portfolio_store import PortfolioStore

transport = httpx.ASGITransport(app=app)


@pytest.mark.anyio
async def test_crypto_analysis_routes_without_pending(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "app.db"))
    question = (
        "Analyze this crypto portfolio JSON: "
        "{\"positions\":[{\"symbol\":\"BTC\",\"qty\":1.25},{\"symbol\":\"ETH\",\"qty\":8.5}],"
        "\"constraints\":{\"risk_mode\":\"balanced\"}}"
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ask", json={"question": question})
    assert response.status_code == 200
    payload = response.json()
    assert payload["chosen_agent"] == "crypto_analysis"
    assert payload["workflow"]["requires_approval"] is False
    assert payload["workflow"]["pending_actions"] == []


@pytest.mark.anyio
async def test_content_creator_creates_draft(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    question = (
        "Create X thread draft. topic: Week 1 portfolio update. analysis: "
        "{\"summary\":\"Top positions count=2, concentration(top3)=90.0%.\","
        "\"risk_checklist\":[\"Confirm liquidity for top positions.\"],"
        "\"scenarios\":{\"base\":\"Sideways rotation.\"},"
        "\"top_positions\":[{\"symbol\":\"BTC\"},{\"symbol\":\"ETH\"}]}"
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ask", json={"question": question})
    assert response.status_code == 200
    payload = response.json()
    assert payload["chosen_agent"] == "content_creator"

    store = PortfolioStore(db_path=str(db_path))
    latest = store.fetch_latest_draft()
    assert latest is not None
    assert latest.topic == "Week 1 portfolio update"


@pytest.mark.anyio
async def test_publish_request_requires_approve(monkeypatch, tmp_path) -> None:
    pending_store = PendingActionStore(db_path=str(tmp_path / "pending_actions.db"))
    monkeypatch.setattr("app.main.pending_store", pending_store)
    question = "Publish this draft now: 11111111-2222-3333-4444-555555555555"
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ask",
            json={"question": question, "actor_id": "op-1", "actor_role": "operator"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["chosen_agent"] == "portfolio_manager"
        assert payload["workflow"]["requires_approval"] is True
        pending_actions = payload["workflow"]["pending_actions"]
        assert len(pending_actions) == 1
        action_id = pending_actions[0]["action_id"]

        approve_response = await client.post(
            "/approve",
            json={"action_id": action_id, "approved_by": "tester", "approved_role": "operator"},
        )
        assert approve_response.status_code == 200
        approve_payload = approve_response.json()
        assert approve_payload["status"] == STATUS_COMPLETED
        assert approve_payload["pending_actions"] == []
        assert any(
            action["tool"] == "publish_draft" and action["ok"] is True
            for action in approve_payload["executed_actions"]
        )
