#!/usr/bin/env bash
# Bring up the WCP v0.955.1 federation demo.
#
# The actual demo logic is in demo.py (the in-process two-coordinator
# script). setup.sh prepares the SQLite DB files; verify.sh runs the
# script and checks the exit code.

set -euo pipefail

cd "$(dirname "$0")/../.."

echo "[setup] cleaning any stale demo databases ..."
rm -f .federation-demo-alpha.db .federation-demo-beta.db
echo "[setup] OK"
echo "[setup] run ./examples/federation-demo/verify.sh to execute the demo"
