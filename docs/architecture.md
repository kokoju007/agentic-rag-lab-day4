# Architecture

## Overview
- FastAPI service exposing two endpoints: `GET /health` and `POST /ask`.
- The `/ask` endpoint returns a dummy response payload with a fixed answer, two citations, and a generated `trace_id`.

## Components
- **API layer**: `app/main.py`
- **Dependencies**: `requirements.txt`
