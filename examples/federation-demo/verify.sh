#!/usr/bin/env bash
# End-to-end verification for the WCP v0.955.1 federation demo.
#
# Runs demo.py, which:
#   1. Spins up coord-alpha and coord-beta in-process.
#   2. Mutually exchanges signed bilateral trust anchors and verifies
#      both signatures.
#   3. Registers a logistics worker on coord-beta.
#   4. Posts a transport task on coord-alpha; the federation router
#      forwards it to coord-beta. coord-alpha records
#      federation_task_forwarded on its audit chain.
#   5. coord-beta records task_claimed and task_completed.
#   6. coord-alpha imports coord-beta's audit chain segment for the
#      claim; the segment is verified for link continuity, link
#      binding, and payload binding; coord-alpha records
#      federation_audit_chain_imported.
#   7. Both audit chains pass verify_chain.
#
# Passes when:
#   - both trust-anchor signatures verify
#   - the forward succeeds with eligible_workers_count >= 1
#   - import_peer_chain returns ok=True
#   - both audit chains pass verify_chain
#   - alpha records exactly 3 federation entry kinds
#
# Exit code 0 = PASS, non-zero = FAIL.

set -uo pipefail

cd "$(dirname "$0")/../.."

PYTHON="${WCP_PYTHON:-.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

"$PYTHON" examples/federation-demo/demo.py
RC=$?
exit $RC
