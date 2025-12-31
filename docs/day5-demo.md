# Day-5 Demo: SMB IT Ops Assistant

## Problem
Small IT teams need fast, reliable guidance during incidents without exposing secrets or making risky changes.

## Users
- On-call engineers
- IT managers reviewing incidents
- Support analysts triaging tickets

## Request Types
- Normal: runbook steps, backup verification, ticket summaries.
- Borderline: unclear or under-specified requests that need more context.
- Blocked: requests for system prompts, secrets, or destructive changes.

## Success Criteria
- Correct routing to doc search with clear evidence.
- Guardrails block sensitive requests.
- Human review hints appear when confidence is low.

## Failure Modes
- Answers without evidence.
- Missing guardrail enforcement.
- No human review trigger on low-confidence retrieval.
