# agentic-rag-lab

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker
```bash
docker build -t agentic-rag-lab .
docker run -p 8000:8000 agentic-rag-lab
```

## Eval
```bash
python scripts/run_eval.py
```

## Tests
```bash
pytest -q
```

## Lint
```bash
ruff check .
```

Ruff is pinned in `requirements.txt` to keep linting consistent in CI.
