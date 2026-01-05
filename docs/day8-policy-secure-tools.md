# Day 8: Policy + Secure Tools

## Threat model (SSRF)
- Untrusted URLs in tools can reach internal services if not constrained.
- Mitigations applied to `http_post`:
  - HTTPS-only by default (opt-in `ALLOW_INSECURE_HTTP=true`).
  - Optional domain allowlist via `TOOL_HTTP_POST_ALLOWED_DOMAINS`.
  - DNS resolution check blocks private/loopback/link-local/multicast/reserved IPs.
  - Redirects disabled.
  - Request limits: timeout + max payload size + host header override blocked.

## Policy design
- Actor model: `actor_id` + `actor_role` (`viewer`, `operator`, `admin`).
- Default tool rules:
  - `http_post` requires `operator` or `admin`.
  - Other tools default to `viewer`.
- Optional per-tool overrides via `TOOL_POLICY_RULES_JSON`:
  ```json
  {
    "notify": { "min_role": "admin" },
    "http_post": { "min_role": "operator", "allowed_domains": ["hooks.example.com"] }
  }
  ```
- PDP decisions include `{allowed, reason, policy_id, policy_version, evaluated_at}` and are logged with `trace_id`.

## Audit fields
- Pending actions persist `approved_by`, `approved_role`, `approved_at`.
- Policy decisions are embedded in pending action metadata and returned in `/ask` workflow payload.

## Env vars
- `ALLOW_INSECURE_HTTP=true` to allow http.
- `TOOL_HTTP_POST_ALLOWED_DOMAINS=hooks.example.com,api.example.com`
- `TOOL_HTTP_POST_TIMEOUT_SECONDS=10`
- `TOOL_HTTP_POST_MAX_PAYLOAD_BYTES=65536`
- `TOOL_HTTP_POST_MAX_RESPONSE_BYTES=4096`
- `TOOL_POLICY_RULES_JSON=...` (optional overrides)
