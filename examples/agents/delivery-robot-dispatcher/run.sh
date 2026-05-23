#!/usr/bin/env bash
# Robot-as-agent reference deployment: start coordinator (if not already),
# bring up the AMR worker, the stationary manipulator, then post the
# transport task. Watch the chain settle.
set -euo pipefail
cd "$(dirname "$0")"

# Optional: start a fresh local coordinator. Comment out if one is already
# running on ws://localhost:8000/wcp/ws.
# python -m uvicorn wcp_dev_runtime.coordinator_dev_app:app --port 8000 &
# COORD_PID=$!
# sleep 1

python worker.py &
AMR_PID=$!

python manipulator_worker.py &
MANIP_PID=$!

# Give the workers a moment to register their capabilities.
sleep 1

python agent.py

# Allow the chain to settle, then tear down.
sleep 3
kill "$AMR_PID" "$MANIP_PID" 2>/dev/null || true
# kill "$COORD_PID" 2>/dev/null || true
