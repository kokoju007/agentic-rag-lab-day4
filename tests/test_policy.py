import json

from app.policy import ActorRole, evaluate_tool_access, resolve_actor


def test_policy_denies_viewer_for_http_post(monkeypatch) -> None:
    monkeypatch.delenv("TOOL_POLICY_RULES_JSON", raising=False)
    actor = resolve_actor("user-1", "viewer")
    decision = evaluate_tool_access(actor, "http_post", {"url": "https://example.com"})
    assert decision.allowed is False
    assert decision.reason.startswith("role_required")


def test_policy_allows_operator_for_http_post(monkeypatch) -> None:
    monkeypatch.delenv("TOOL_POLICY_RULES_JSON", raising=False)
    actor = resolve_actor("user-2", "operator")
    decision = evaluate_tool_access(actor, "http_post", {"url": "https://example.com"})
    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_policy_domain_allowlist_blocks(monkeypatch) -> None:
    monkeypatch.setenv("TOOL_HTTP_POST_ALLOWED_DOMAINS", "allowed.example.com")
    actor = resolve_actor("user-3", "operator")
    decision = evaluate_tool_access(actor, "http_post", {"url": "https://blocked.example.com"})
    assert decision.allowed is False
    assert decision.reason == "domain_not_allowed"


def test_policy_override_rules(monkeypatch) -> None:
    overrides = {"notify": {"min_role": "admin"}}
    monkeypatch.setenv("TOOL_POLICY_RULES_JSON", json.dumps(overrides))
    actor = resolve_actor("user-4", "operator")
    decision = evaluate_tool_access(actor, "notify", {})
    assert decision.allowed is False
    assert decision.reason == "role_required:admin"
    assert ActorRole.from_value("admin") == ActorRole.admin
