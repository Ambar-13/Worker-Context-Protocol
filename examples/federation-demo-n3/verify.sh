#!/usr/bin/env bash
# End-to-end verification for the three-coordinator partial-graph
# federation demo. Runs demo.py.
#
# Topology: coord-alpha holds trust anchors to coord-beta and
# coord-gamma; coord-beta and coord-gamma are NOT peered (partial
# graph, not a clique). Two descriptor types route to distinct peers
# via per-peer admission policy on alpha's router.
#
# Pass criteria (asserted by demo.py before printing PASS):
#   len(federation_capability_advertised on alpha) == 2
#   len(federation_task_forwarded       on alpha) == 2
#   distinct peer DIDs in forwarded entries        == 2
#   verify_chain integrity scaffold                 OK
#
# Exit 0 = PASS, non-zero = FAIL.

set -uo pipefail
cd "$(dirname "$0")/../.."

PYTHON="${WCP_PYTHON:-.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

"$PYTHON" examples/federation-demo-n3/demo.py
RC=$?
exit $RC
