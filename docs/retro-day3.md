# Day 3 Retro

## What changed
- Added an evaluation harness with a golden routing dataset and smoke tests.
- Added structured JSON logging with trace propagation.
- Defined explicit API schemas for `/ask`.
- Added CI (lint + tests + eval smoke) and a Dockerfile.

## Why it matters
These changes show that the service is testable, observable, and deployable—key traits for an ops-ready portfolio project.

## Next steps
- Expand evaluation cases and track accuracy over time.
- Add persistence for logs/metrics and alerting hooks.
