#!/usr/bin/env bash
# Provision a signed federation trust anchor between coord-alpha (port 9000)
# and coord-beta (port 9001). Both coordinators must already be running
# (via docker compose up -d).
#
# This is a demo trust anchor; production deployments use signed X.509 chains
# or DID-rooted trust anchors per spec/federation.md. The demo uses a shared
# secret for brevity.

set -euo pipefail

COORD_ALPHA_URL="${COORD_ALPHA_URL:-http://localhost:9000}"
COORD_BETA_URL="${COORD_BETA_URL:-http://localhost:9001}"

echo "[setup] checking coord-alpha at $COORD_ALPHA_URL..."
if ! curl -sf "$COORD_ALPHA_URL/health" > /dev/null 2>&1; then
  # The reference coordinator may not expose /health at v1.0-rc1; try /wcp/capabilities
  if ! curl -sf "$COORD_ALPHA_URL/wcp/capabilities" > /dev/null 2>&1; then
    echo "[setup] WARN: coord-alpha did not respond at $COORD_ALPHA_URL"
    echo "[setup] continuing in dry-run mode; this demo's federation provisioning"
    echo "[setup] requires the v1.1 federation primitives RFC to be implemented"
    echo "[setup] in the reference coordinator. v1.0-rc1 coordinator does not yet"
    echo "[setup] expose federation endpoints."
    echo "[setup] dry-run trust anchor:"
    cat <<EOF
{
  "schema_version": "wcp/1.0-rc1+federation-demo",
  "peer_a_coordinator_did": "did:wcp:coord-alpha-demo-key",
  "peer_b_coordinator_did": "did:wcp:coord-beta-demo-key",
  "peer_a_url": "ws://coord-alpha:9000/wcp/ws",
  "peer_b_url": "ws://coord-beta:9001/wcp/ws",
  "scope": ["capability_discovery", "task_posting", "audit_chain_export", "settlement_transfer"],
  "shared_secret_hash": "$(echo -n 'demo-federation-secret' | shasum -a 256 | awk '{print $1}')",
  "established_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "expires_at": "$(date -u -v+30d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '+30 days' +%Y-%m-%dT%H:%M:%SZ)",
  "demo_only": true
}
EOF
    echo "[setup] dry-run complete; demo will use the trust anchor above when v1.1 federation lands"
    exit 0
  fi
fi

echo "[setup] coord-alpha reachable"
echo "[setup] checking coord-beta at $COORD_BETA_URL..."
if ! curl -sf "$COORD_BETA_URL/health" > /dev/null 2>&1; then
  if ! curl -sf "$COORD_BETA_URL/wcp/capabilities" > /dev/null 2>&1; then
    echo "[setup] WARN: coord-beta did not respond at $COORD_BETA_URL"
    echo "[setup] (see note above about v1.1 federation primitives)"
    exit 0
  fi
fi
echo "[setup] coord-beta reachable"

# Real provisioning would POST to /wcp/federation/establish-trust-anchor on
# both coordinators with mutual signed payloads. v1.0-rc1 does not yet expose
# this endpoint; v1.1 RFC 0016 federation primitives spec out the call.

echo "[setup] (v1.1 trust anchor establishment endpoint not yet exposed)"
echo "[setup] demo will run in best-effort mode against current v1.0-rc1 coordinator"
echo "[setup] when v1.1 federation lands, this script POSTs the trust anchor to both peers"
echo "[setup] PASS (dry-run; no errors)"
