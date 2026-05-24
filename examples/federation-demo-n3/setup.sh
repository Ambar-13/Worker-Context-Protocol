#!/usr/bin/env bash
# Bring up the WCP v0.955.1 three-coordinator partial-graph federation
# demo. The actual demo logic is in demo.py.
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "[setup] cleaning any stale demo databases ..."
rm -f .federation-n3-alpha.db .federation-n3-beta.db .federation-n3-gamma.db
echo "[setup] OK"
echo "[setup] run ./examples/federation-demo-n3/verify.sh to execute the demo"
