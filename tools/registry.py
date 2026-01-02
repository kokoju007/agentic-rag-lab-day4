from __future__ import annotations

from typing import Any, Callable

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


TOOL_REGISTRY: dict[str, ToolFn] = {
    "kb_search": kb_search,
    "create_ticket": create_ticket,
    "generate_runbook": generate_runbook,
    "notify": notify,
    "restart_service": restart_service,
}


def run_tool(tool: str, args: dict[str, Any]) -> ToolResult:
    handler = TOOL_REGISTRY.get(tool)
    if not handler:
        return _result(tool, False, "", "unknown_tool")
    return handler(args)
