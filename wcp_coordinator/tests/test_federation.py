"""Tests for the federation primitives.

The federation module rides on the existing eight RPCs. These tests
verify:

  - Trust anchors verify peer signatures and reject expired or
    out-of-scope anchors.
  - Capability advertisements outside the trust scope are silently
    dropped (no chain emission).
  - Task forwarding within scope succeeds and emits
    federation_task_forwarded.
  - Task forwarding to a peer that refuses still emits the entry
    (with status='rejected') for forensic purposes.
  - Audit chain interop fetches and verifies a peer chain segment.
  - A tampered peer chain segment is detected by verify_chain_segment.
"""
from __future__ import annotations

import asyncio
import base64
import time
from datetime import timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from wcp_coordinator.audit_chain import AuditChain
from wcp_coordinator.federation import (
    AuditExport,
    CapabilitySync,
    FederationRouter,
    TrustAnchor,
    TrustAnchorStore,
)
from wcp_coordinator.federation.audit_export import verify_chain_segment


def _make_anchor(scope, lifetime_s=3600):
    """Make a peer signing key, build a signed TrustAnchor for it."""
    sk = Ed25519PrivateKey.generate()
    pubkey_bytes = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    now = time.time()
    body = {
        "peer_coordinator_did": "did:wcp:peer-beta",
        "peer_endpoint_url": "wss://beta.example/wcp/ws",
        "scope": sorted(scope),
        "established_at": now,
        "expires_at": now + lifetime_s,
    }
    import json as _json
    body_bytes = _json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    sig = sk.sign(body_bytes)
    sig_str = "ed25519:" + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return TrustAnchor(
        peer_coordinator_did="did:wcp:peer-beta",
        peer_public_key=pubkey_bytes,
        peer_endpoint_url="wss://beta.example/wcp/ws",
        scope=frozenset(scope),
        established_at=now,
        expires_at=now + lifetime_s,
        signature=sig_str,
    )


def test_trust_anchor_signature_verified():
    a = _make_anchor({"capability_discovery"})
    assert a.verify_signature() is True


def test_trust_anchor_rejects_forged_signature():
    a = _make_anchor({"capability_discovery"})
    bad = TrustAnchor(
        peer_coordinator_did=a.peer_coordinator_did,
        peer_public_key=a.peer_public_key,
        peer_endpoint_url="wss://malicious/wcp/ws",  # tampered URL
        scope=a.scope,
        established_at=a.established_at,
        expires_at=a.expires_at,
        signature=a.signature,  # signature still over the old URL
    )
    assert bad.verify_signature() is False


def test_trust_anchor_rejects_expired():
    a = _make_anchor({"capability_discovery"}, lifetime_s=-1)
    assert a.is_expired() is True
    store = TrustAnchorStore()
    with pytest.raises(ValueError, match="expired"):
        store.add(a)


def test_trust_anchor_rejects_unknown_scope_class():
    with pytest.raises(ValueError, match="unknown trust classes"):
        TrustAnchor.from_dict(
            {
                "peer_coordinator_did": "did:wcp:peer",
                "peer_public_key_b64": "AAAA",
                "peer_endpoint_url": "wss://x",
                "scope": ["this_class_does_not_exist"],
                "established_at": 0,
                "expires_at": 9999999999,
                "signature": "ed25519:fake",
            }
        )


def test_capability_advertised_emitted_within_scope(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore()
    a = _make_anchor({"capability_discovery"})
    store.add(a)
    cs = CapabilitySync(audit, store)
    cs.advertise_peer_capability(
        peer_anchor=a,
        peer_worker_id="did:wcp:peer-worker-1",
        capability_summary={"class": "human", "skills": ["delivery"]},
    )
    from wcp_coordinator.models import WcpAudit
    rows = list(db.query(WcpAudit).filter(
        WcpAudit.event_type == "federation_capability_advertised"
    ))
    assert len(rows) == 1
    assert rows[0].payload_json["peer_worker_id"] == "did:wcp:peer-worker-1"


def test_capability_advertised_silently_dropped_outside_scope(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore()
    # Anchor declares only audit_chain_export, not capability_discovery.
    a = _make_anchor({"audit_chain_export"})
    store.add(a)
    cs = CapabilitySync(audit, store)
    cs.advertise_peer_capability(
        peer_anchor=a,
        peer_worker_id="did:wcp:peer-worker-1",
        capability_summary={},
    )
    from wcp_coordinator.models import WcpAudit
    rows = list(db.query(WcpAudit).filter(
        WcpAudit.event_type == "federation_capability_advertised"
    ))
    assert len(rows) == 0


def test_task_forwarded_under_scope_emits_audit_entry(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore()
    a = _make_anchor({"capability_discovery"})
    store.add(a)

    forwarded_calls: list[tuple[str, str, dict]] = []

    async def stub_forwarder(url, method, params):
        forwarded_calls.append((url, method, params))
        return {"task_id": params["task"]["task_id"], "eligible_workers_count": 1}

    router = FederationRouter(audit, store, forwarder=stub_forwarder)
    task = {"task_id": "t-fwd-1", "descriptor_type": "transport"}
    result = asyncio.get_event_loop().run_until_complete(
        router.forward_task(peer=a, task=task, expiry="2099-12-31T00:00:00Z")
    )
    assert result["task_id"] == "t-fwd-1"
    assert forwarded_calls == [
        (a.peer_endpoint_url, "tasks/post",
         {"task": task, "expiry": "2099-12-31T00:00:00Z"}),
    ]

    from wcp_coordinator.models import WcpAudit
    rows = list(db.query(WcpAudit).filter(
        WcpAudit.event_type == "federation_task_forwarded"
    ))
    assert len(rows) == 1
    assert rows[0].payload_json["status"] == "accepted"
    assert rows[0].payload_json["task_id"] == "t-fwd-1"


def test_task_forwarding_records_peer_rejection(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore()
    a = _make_anchor({"capability_discovery"})
    store.add(a)

    async def failing_forwarder(url, method, params):
        raise RuntimeError("peer is on fire")

    router = FederationRouter(audit, store, forwarder=failing_forwarder)
    task = {"task_id": "t-fwd-fail", "descriptor_type": "transport"}
    result = asyncio.get_event_loop().run_until_complete(
        router.forward_task(peer=a, task=task, expiry="2099-12-31T00:00:00Z")
    )
    assert "error" in result

    from wcp_coordinator.models import WcpAudit
    rows = list(db.query(WcpAudit).filter(
        WcpAudit.event_type == "federation_task_forwarded"
    ))
    assert len(rows) == 1
    assert rows[0].payload_json["status"] == "rejected"


def test_audit_chain_import_verifies_segment(db, signer):
    """Build a valid peer chain segment manually; AuditExport's
    verify_chain_segment should accept it."""
    audit = AuditChain(db, signer)
    store = TrustAnchorStore()
    a = _make_anchor({"audit_chain_export"})
    store.add(a)

    # Build a tiny valid peer chain manually using the same canonical
    # form the local AuditChain uses.
    import hashlib, json as _json
    def cj(d): return _json.dumps(d, sort_keys=True, separators=(",", ":")).encode()
    def sha(b): return hashlib.sha256(b).hexdigest()

    e1_payload = {"task_id": "peer-t1"}
    e1_payload_hash = sha(cj(e1_payload))
    e1_link = {
        "event_type": "task_posted",
        "actor_did": "did:wcp:peer-agent",
        "timestamp": "2026-05-23T10:00:00",
        "payload_hash": e1_payload_hash,
        "prev_hash": "",
        "claim_id": "peer-c1",
        "task_id": "peer-t1",
    }
    e1_this = sha(cj(e1_link))

    e2_payload = {"claim_id": "peer-c1", "verifier_decision": "pass"}
    e2_payload_hash = sha(cj(e2_payload))
    e2_link = {
        "event_type": "task_completed",
        "actor_did": "did:wcp:peer-coordinator",
        "timestamp": "2026-05-23T10:05:00",
        "payload_hash": e2_payload_hash,
        "prev_hash": e1_this,
        "claim_id": "peer-c1",
        "task_id": "peer-t1",
    }
    e2_this = sha(cj(e2_link))

    peer_chain = [
        {**e1_link, "payload_json": e1_payload, "this_hash": e1_this, "sig": "ed25519:peer"},
        {**e2_link, "payload_json": e2_payload, "this_hash": e2_this, "sig": "ed25519:peer"},
    ]

    assert verify_chain_segment(peer_chain) is True

    async def stub_fetcher(url, claim_id):
        return peer_chain

    export = AuditExport(audit, fetcher=stub_fetcher)
    result = asyncio.get_event_loop().run_until_complete(
        export.import_peer_chain(peer=a, claim_id="peer-c1")
    )
    assert result["ok"] is True
    assert result["entries"] == 2
    assert result["completion_event"] == "task_completed"

    from wcp_coordinator.models import WcpAudit
    rows = list(db.query(WcpAudit).filter(
        WcpAudit.event_type == "federation_audit_chain_imported"
    ))
    assert len(rows) == 1
    assert rows[0].payload_json["ok"] is True


def test_audit_chain_import_detects_tampered_segment(db, signer):
    """A peer chain with a payload tampered post-hoc fails verification."""
    audit = AuditChain(db, signer)
    store = TrustAnchorStore()
    a = _make_anchor({"audit_chain_export"})
    store.add(a)

    import hashlib, json as _json
    def cj(d): return _json.dumps(d, sort_keys=True, separators=(",", ":")).encode()
    def sha(b): return hashlib.sha256(b).hexdigest()

    e1_payload = {"task_id": "peer-t1"}
    e1_link = {
        "event_type": "task_posted",
        "actor_did": "did:wcp:peer-agent",
        "timestamp": "2026-05-23T10:00:00",
        "payload_hash": sha(cj(e1_payload)),
        "prev_hash": "",
        "claim_id": "peer-c1",
        "task_id": "peer-t1",
    }
    e1_this = sha(cj(e1_link))

    # Tamper: ship a different payload_json than the one payload_hash binds.
    tampered = [
        {**e1_link, "payload_json": {"task_id": "DIFFERENT"},
         "this_hash": e1_this, "sig": "ed25519:peer"},
    ]
    assert verify_chain_segment(tampered) is False

    async def stub_fetcher(url, claim_id):
        return tampered

    export = AuditExport(audit, fetcher=stub_fetcher)
    result = asyncio.get_event_loop().run_until_complete(
        export.import_peer_chain(peer=a, claim_id="peer-c1")
    )
    assert result["ok"] is False


def test_router_picks_peer_only_when_descriptor_in_scope(db, signer):
    audit = AuditChain(db, signer)
    store = TrustAnchorStore()
    a = _make_anchor({"capability_discovery"})
    store.add(a)

    router = FederationRouter(audit, store)

    # With per-peer descriptor admission set, only matching descriptors
    # surface the peer.
    matched = router.pick_peer(
        descriptor_type="transport",
        worker_class_filter=[],
        allowed_descriptor_types_per_peer={
            a.peer_coordinator_did: {"transport"},
        },
    )
    assert matched is a

    not_matched = router.pick_peer(
        descriptor_type="place_on_shelf",
        worker_class_filter=[],
        allowed_descriptor_types_per_peer={
            a.peer_coordinator_did: {"transport"},
        },
    )
    assert not_matched is None
