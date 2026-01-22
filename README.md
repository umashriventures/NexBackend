# NEX Backend Service (Python MVP)

## Overview
A minimal viable product for the NEX Backend Service built with **FastAPI**, **WebSockets**, and **JWT** authentication. The service streams partial transcripts, final transcripts, and simulated LLM tokens.

## Features
- WebSocket endpoint `/ws` with JWT authentication.
- Streaming ASR stub (audio chunks as text).
- Conversation orchestrator that echoes the transcript as tokens.
- Short‑term in‑memory memory engine.
- Load‑testing harness (`app/load_test.py`).
- Swagger UI available at `http://localhost:8000/docs` (OpenAPI spec).

## Prerequisites
- Python 3.12 (or compatible).
- Poetry (install via `curl -sSL https://install.python-poetry.org | python3 -`).

## Setup
```bash
# Clone the repo (if not already)
git clone <repo-url>
cd nex-backend

# Install dependencies via Poetry
poetry install

# Set a secret for JWT (optional, defaults to "supersecretkey")
export JWT_SECRET="your‑very‑secret-key"
```

## Running the Server
```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will start and Swagger UI will be reachable at:
```
http://localhost:8000/docs
```
> **Note:** WebSocket routes are not shown in Swagger, but the UI confirms the OpenAPI spec is active.

## Generating a JWT for Testing
```python
# quick one‑liner (run with `poetry run python -c "..."`)
import os, jwt, datetime
secret = os.getenv('JWT_SECRET', 'supersecretkey')
payload = {"user_id": "test_user", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
print(jwt.encode(payload, secret, algorithm='HS256'))
```
Copy the printed token for the next steps.

## Manual Test with `wscat`
```bash
# Install wscat globally if you don't have it
npm install -g wscat

# Connect to the WebSocket
wscat -c ws://localhost:8000/ws
```
In the `wscat` prompt, send the auth message (replace `<TOKEN>`):
```
{"type":"auth","token":"<TOKEN>"}
```
You should receive:
```json
{"type":"status_update","status":"authenticated"}
```
Now send audio chunks:
```
{"type":"audio","chunk":"hello "}
{"type":"audio","chunk":"world"}
{"type":"end"}
```
You will see `partial_transcript`, `final_transcript`, a series of `llm_token` events, and finally a `status_update` with `completed`.

## Load‑Testing
The repository includes a simple load‑testing script that spawns many concurrent WebSocket clients.
```bash
poetry run python -m app.load_test 50   # 50 concurrent sessions (default)
```
The script prints the average round‑trip latency. Increase the number (e.g., `200`) to stress‑test the service.

## Extending the Service
- Replace the ASR stub in `app/asr.py` with a real speech‑to‑text engine.
- Implement a real LLM streaming backend in `app/llm_runtime.py`.
- Add more sophisticated belief handling and tool execution as described in the PRD.

---
*Feel free to open an issue or PR for any enhancements.*
