#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Activate the project venv if available; otherwise assume the user has installed wcp-sdk.
if [ -f "../../../.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ../../../.venv/bin/activate
fi

# Start the reference coordinator on port 8000 (dev mode, in-memory SQLite).
python -m uvicorn wcp_dev_runtime.coordinator_dev_app:app --port 8000 &
COORD=$!
trap "kill $COORD 2>/dev/null || true" EXIT

# Wait briefly for the coordinator to bind.
sleep 2

# Start the worker.
python worker.py &
WORKER=$!
trap "kill $COORD $WORKER 2>/dev/null || true" EXIT

# Run the agent (single-shot post).
python agent.py

wait $WORKER || true
