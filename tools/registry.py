from __future__ import annotations

import ipaddress
import json
import os
import socket
import time
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

ToolResult = dict[str, Any]
ToolFn = Callable[[dict[str, Any]], ToolResult]


def _result(tool: str, ok: bool, output: str, error: str | None = None) -> ToolResult:
    payload: ToolResult = {"tool": tool, "ok": ok, "output": output}
    if error:
        payload["error"] = error
    return payload


def kb_search(args: dict[str, Any]) -> ToolResult:
    query = args.get("query", "")
    return _result("kb_search", True, f"Found KB snippets for '{query}'.")


def create_ticket(args: dict[str, Any]) -> ToolResult:
    summary = args.get("summary", "No summary provided.")
    return _result("create_ticket", True, f"Created ticket: {summary}")


def generate_runbook(args: dict[str, Any]) -> ToolResult:
    topic = args.get("topic", "general")
    return _result("generate_runbook", True, f"Generated runbook for {topic}.")


def notify(args: dict[str, Any]) -> ToolResult:
    channel = args.get("channel", "ops")
    message = args.get("message", "")
    return _result("notify", True, f"Notified {channel}: {message}")


def restart_service(args: dict[str, Any]) -> ToolResult:
    service = args.get("service", "unknown-service")
    environment = args.get("environment", "unknown")
    return _result(
        "restart_service",
        True,
        f"Restarted {service} in {environment}.",
    )


def http_post(args: dict[str, Any]) -> ToolResult:
    url = str(args.get("url") or os.getenv("WEBHOOK_URL") or "")
    if not url:
        return _result("http_post", False, "", "missing_url")

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    allow_insecure = os.getenv("ALLOW_INSECURE_HTTP", "").lower() == "true"
    if scheme not in {"https", "http"}:
        return _result("http_post", False, "", "invalid_scheme")
    if scheme == "http" and not allow_insecure:
        return _result("http_post", False, "", "insecure_http_disallowed")

    hostname = parsed.hostname
    if not hostname:
        return _result("http_post", False, "", "missing_hostname")

    allowed_domains = _parse_allowed_domains()
    if allowed_domains and not _domain_allowed(hostname, allowed_domains):
        return _result("http_post", False, "", "domain_not_allowed")

    ip_blocked = _is_blocked_hostname(hostname, parsed.port or (443 if scheme == "https" else 80))
    if ip_blocked:
        return _result("http_post", False, "", ip_blocked)

    payload = args.get("payload", {})
    try:
        payload_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return _result("http_post", False, "", "invalid_payload")
    max_payload = int(os.getenv("TOOL_HTTP_POST_MAX_PAYLOAD_BYTES", "65536"))
    if len(payload_bytes) > max_payload:
        return _result("http_post", False, "", "payload_too_large")

    headers = args.get("headers")
    if headers is not None:
        if not isinstance(headers, dict):
            return _result("http_post", False, "", "invalid_headers")
        if any(str(key).lower() == "host" for key in headers.keys()):
            return _result("http_post", False, "", "host_header_disallowed")
        headers = {str(k): str(v) for k, v in headers.items()}

    timeout_seconds = float(os.getenv("TOOL_HTTP_POST_TIMEOUT_SECONDS", "10"))
    max_response_bytes = int(os.getenv("TOOL_HTTP_POST_MAX_RESPONSE_BYTES", "4096"))
    start = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        return _result("http_post", False, "", str(exc))
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    body_bytes = response.content[:max_response_bytes]
    truncated_body = body_bytes.decode(response.encoding or "utf-8", errors="replace")
    output = json.dumps(
        {
            "status_code": response.status_code,
            "truncated_body": truncated_body,
            "elapsed_ms": elapsed_ms,
        },
        ensure_ascii=False,
    )
    ok = 200 <= response.status_code < 300
    error = None if ok else f"status_{response.status_code}"
    return _result("http_post", ok, output, error)


def portfolio_rebalance_plan(args: dict[str, Any]) -> ToolResult:
    request = str(args.get("request") or "")
    output = json.dumps(
        {
            "simulated": True,
            "plan": "Generated rebalance plan (simulation only).",
            "request": request,
        },
        ensure_ascii=False,
    )
    return _result("portfolio_rebalance_plan", True, output)


def publish_draft(args: dict[str, Any]) -> ToolResult:
    draft_id = str(args.get("draft_id") or "")
    output = json.dumps(
        {
            "simulated": True,
            "published": True,
            "draft_id": draft_id,
        },
        ensure_ascii=False,
    )
    return _result("publish_draft", True, output)


def _parse_allowed_domains() -> set[str]:
    raw = os.getenv("TOOL_HTTP_POST_ALLOWED_DOMAINS", "").strip()
    if not raw:
        return set()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _domain_allowed(hostname: str, allowed_domains: set[str]) -> bool:
    normalized = hostname.lower().strip(".")
    for domain in allowed_domains:
        domain = domain.strip(".")
        if normalized == domain or normalized.endswith(f".{domain}"):
            return True
    return False


def _is_blocked_hostname(hostname: str, port: int) -> str | None:
    try:
        results = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError:
        return "dns_resolution_failed"
    for _, _, _, _, sockaddr in results:
        ip = sockaddr[0]
        try:
            ip_addr = ipaddress.ip_address(ip)
        except ValueError:
            return "invalid_ip"
        if _is_blocked_ip(ip_addr):
            return "blocked_ip"
    return None


def _is_blocked_ip(ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(
        [
            ip_addr.is_private,
            ip_addr.is_loopback,
            ip_addr.is_link_local,
            ip_addr.is_multicast,
            ip_addr.is_reserved,
            ip_addr.is_unspecified,
        ]
    )


TOOL_REGISTRY: dict[str, ToolFn] = {
    "kb_search": kb_search,
    "create_ticket": create_ticket,
    "generate_runbook": generate_runbook,
    "notify": notify,
    "restart_service": restart_service,
    "http_post": http_post,
    "portfolio_rebalance_plan": portfolio_rebalance_plan,
    "publish_draft": publish_draft,
}


def run_tool(tool: str, args: dict[str, Any]) -> ToolResult:
    handler = TOOL_REGISTRY.get(tool)
    if not handler:
        return _result(tool, False, "", "unknown_tool")
    return handler(args)
