import httpx
import pytest

from app.main import app

transport = httpx.ASGITransport(app=app)


@pytest.mark.anyio
async def test_health() -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload


@pytest.mark.anyio
async def test_ask_routes_to_doc_search() -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ask", json={"question": "Day-1 /ask 엔드포인트가 뭐야?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["chosen_agent"] == "doc_search"
    assert "answer" in payload
    assert isinstance(payload["evidence"], list)
    assert len(payload["evidence"]) >= 1
    assert isinstance(payload["citations"], list)


@pytest.mark.anyio
async def test_ask_routes_to_direct_answer() -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ask", json={"question": "FastAPI가 뭐야?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["chosen_agent"] == "direct_answer"
    assert "answer" in payload
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["citations"], list)
