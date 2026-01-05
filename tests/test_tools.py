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

    def fake_getaddrinfo(host: str, port: int, type: int | None = None):
        return [(None, None, None, None, ("93.184.216.34", port))]

    monkeypatch.delenv("TOOL_HTTP_POST_ALLOWED_DOMAINS", raising=False)
    monkeypatch.setattr(registry.httpx, "Client", client_factory)
    monkeypatch.setattr(registry.socket, "getaddrinfo", fake_getaddrinfo)
    result = registry.http_post({"url": "https://example.com", "payload": {"ping": "pong"}})

    assert result["ok"] is True
    payload = json.loads(result["output"])
    assert payload["status_code"] == 200
    assert "truncated_body" in payload
    assert "elapsed_ms" in payload


def test_http_post_blocks_private_ips(monkeypatch) -> None:
    def fake_getaddrinfo(host: str, port: int, type: int | None = None):
        return [(None, None, None, None, ("127.0.0.1", port))]

    monkeypatch.delenv("TOOL_HTTP_POST_ALLOWED_DOMAINS", raising=False)
    monkeypatch.setattr(registry.socket, "getaddrinfo", fake_getaddrinfo)
    result = registry.http_post({"url": "https://example.com", "payload": {"ping": "pong"}})
    assert result["ok"] is False
    assert result["error"] == "blocked_ip"
