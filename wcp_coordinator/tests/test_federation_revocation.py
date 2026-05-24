"""Trust-anchor revocation integration test.

Scenario:
  1. Two-coord setup with mutual trust anchors in capability_discovery scope.
  2. alpha forwards a tasks/post to beta. Forward succeeds; alpha records
     federation_task_forwarded.
  3. Operator invokes alpha.anchors.remove(beta_did, reason="..."). The
     store emits federation_trust_anchor_revoked on alpha's audit chain.
  4. alpha.router.pick_peer(...) returns None for the same descriptor type
     (no peer satisfies capability_discovery scope after removal).
  5. alpha.router.forward_task(peer=<stale_anchor_handle>) raises
     PeerTrustAnchorRevoked (the router refuses to forward under an
     anchor the operator just revoked).
  6. federation_trust_anchor_revoked appears on alpha's audit chain.

Also covers:
  - remove() returns None on an unknown peer (idempotent).
  - remove() returns the anchor on a known peer.
  - remove() without an attached audit chain does not raise.
"""
from __future__ import annotations

import asyncio
import base64
import json
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from wcp_coordinator.audit_chain import AuditChain
from wcp_coordinator.federation import (
    FederationRouter,
    PeerTrustAnchorRevoked,
    TrustAnchor,
    TrustAnchorStore,
)


def _make_signed_anchor(peer_did: str, peer_url: str, scope, lifetime_s=3600):
    sk = Ed25519PrivateKey.generate()
    pub = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    now = time.time()
    body = {
        "peer_coordinator_did": peer_did,
        "peer_endpoint_url": peer_url,
        "scope": sorted(scope),
        "established_at": now,
        "expires_at": now + lifetime_s,
    }
    body_bytes = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    sig_b = sk.sign(body_bytes)
    sig = "ed25519:" + base64.urlsafe_b64encode(sig_b).rstrip(b"=").decode("ascii")
    return TrustAnchor(
        peer_coordinator_did=peer_did,
        peer_public_key=pub,
        peer_endpoint_url=peer_url,
        scope=frozenset(scope),
        established_at=now,
        expires_at=now + lifetime_s,
        signature=sig,
    )


def test_revoke_returns_none_on_unknown_peer(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore(audit=audit)
    result = store.remove("did:wcp:does-not-exist", reason="cleanup")
    assert result is None
    # No revocation entry emitted for a peer that did not exist.
    from wcp_coordinator.models import WcpAudit
    rows = list(db.query(WcpAudit).filter(
        WcpAudit.event_type == "federation_trust_anchor_revoked"
    ))
    assert len(rows) == 0


def test_revoke_returns_anchor_and_emits_audit_on_known_peer(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore(audit=audit)
    anchor = _make_signed_anchor(
        "did:wcp:peer-known", "wss://peer/wcp/ws", {"capability_discovery"},
    )
    store.add(anchor)

    removed = store.remove(
        "did:wcp:peer-known", reason="key rotation",
    )
    assert removed is anchor
    assert store.get("did:wcp:peer-known") is None

    from wcp_coordinator.models import WcpAudit
    rows = list(db.query(WcpAudit).filter(
        WcpAudit.event_type == "federation_trust_anchor_revoked"
    ))
    assert len(rows) == 1
    payload = rows[0].payload_json
    assert payload["peer_coordinator_did"] == "did:wcp:peer-known"
    assert payload["reason"] == "key rotation"
    assert isinstance(payload["revoked_at"], (int, float))


def test_revoke_without_audit_does_not_raise(db, signer):
    # Some operators run TrustAnchorStore standalone without wiring an
    # audit chain. remove() must work silently in that mode.
    store = TrustAnchorStore()  # no audit
    anchor = _make_signed_anchor(
        "did:wcp:no-audit", "wss://peer/wcp/ws", {"capability_discovery"},
    )
    store.add(anchor)
    removed = store.remove("did:wcp:no-audit", reason="any")
    assert removed is anchor


def test_revoke_then_pick_peer_returns_none(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore(audit=audit)
    anchor = _make_signed_anchor(
        "did:wcp:peer-A", "wss://A/wcp/ws", {"capability_discovery"},
    )
    store.add(anchor)

    router = FederationRouter(audit, store)
    assert router.pick_peer(
        descriptor_type="transport", worker_class_filter=[],
    ) is anchor

    store.remove("did:wcp:peer-A", reason="revoked for test")
    assert router.pick_peer(
        descriptor_type="transport", worker_class_filter=[],
    ) is None


def test_revoke_then_forward_raises_peer_trust_anchor_revoked(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore(audit=audit)
    anchor = _make_signed_anchor(
        "did:wcp:peer-B", "wss://B/wcp/ws", {"capability_discovery"},
    )
    store.add(anchor)

    async def stub_forwarder(url, method, params):
        return {"task_id": params["task"]["task_id"], "eligible_workers_count": 1}

    router = FederationRouter(audit, store, forwarder=stub_forwarder)

    # First forward: peer is present, succeeds.
    task = {"task_id": "t-revoke-1", "descriptor_type": "transport"}
    result = asyncio.get_event_loop().run_until_complete(
        router.forward_task(peer=anchor, task=task, expiry="2099-12-31T00:00:00Z")
    )
    assert result["task_id"] == "t-revoke-1"

    # Operator revokes the anchor.
    store.remove("did:wcp:peer-B", reason="anchor invalidated")

    # Second forward against the now-stale handle MUST raise the defined
    # error rather than silently issuing a cross-coordinator call under
    # a torn-down trust relationship.
    task2 = {"task_id": "t-revoke-2", "descriptor_type": "transport"}
    with pytest.raises(PeerTrustAnchorRevoked):
        asyncio.get_event_loop().run_until_complete(
            router.forward_task(
                peer=anchor, task=task2, expiry="2099-12-31T00:00:00Z",
            )
        )


def test_revoke_audit_entry_payload_carries_all_required_fields(db, signer):
    """Pin the payload shape: peer_coordinator_did, revoked_at, reason."""
    audit = AuditChain(db, signer)
    store = TrustAnchorStore(audit=audit)
    anchor = _make_signed_anchor(
        "did:wcp:peer-shape", "wss://C/wcp/ws", {"capability_discovery"},
    )
    store.add(anchor)
    store.remove("did:wcp:peer-shape", reason="operator runbook step 4.b")

    from wcp_coordinator.models import WcpAudit
    rows = list(db.query(WcpAudit).filter(
        WcpAudit.event_type == "federation_trust_anchor_revoked"
    ))
    assert len(rows) == 1
    p = rows[0].payload_json
    assert set(p.keys()) >= {"peer_coordinator_did", "revoked_at", "reason"}
    assert p["peer_coordinator_did"] == "did:wcp:peer-shape"
    assert p["reason"] == "operator runbook step 4.b"
