import json

import httpx

from tools import registry


def test_http_post_with_mock_transport(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def client_factory(*args, **kwargs) -> httpx.Client:
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(registry.httpx, "Client", client_factory)
    result = registry.http_post({"url": "http://test", "payload": {"ping": "pong"}})

    assert result["ok"] is True
    payload = json.loads(result["output"])
    assert payload["status_code"] == 200
