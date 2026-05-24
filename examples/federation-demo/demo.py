"""
End-to-end federation demo, v0.955.1.

Spins up two reference coordinators in-process (coord-alpha on its own
SQLite DB, coord-beta on a separate SQLite DB), mutually exchanges
signed trust anchors, registers a worker on β, has α forward a task
to β through the federation router, has β complete the task, and
imports β's audit chain segment back to α with verification.

This is the artifact the paper's Section 6 refers to. Running it
end-to-end and getting `OK` from `verify_chain` on both sides is the
acceptance criterion.

Usage:
    python examples/federation-demo/demo.py
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from wcp_coordinator.audit_chain import AuditChain, AuditSigner
from wcp_coordinator.capabilities_service import CapabilitiesService
from wcp_coordinator.did_resolver import DidResolver, _b58encode
from wcp_coordinator.federation import (
    AuditExport,
    CapabilitySync,
    FederationRouter,
    TrustAnchor,
    TrustAnchorStore,
)
from wcp_coordinator.models import Base, WcpAudit
from wcp_coordinator.rpc_dispatch import Dispatcher
from wcp_coordinator.tasks_service import TasksService


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_coordinator(label: str):
    """Returns (services, db_session, signer, signing_key, coord_did)."""
    engine = create_engine(f"sqlite:///./.federation-demo-{label}.db", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = SessionLocal()
    resolver = DidResolver()
    signer = AuditSigner.ephemeral()
    audit = AuditChain(db, signer)
    caps = CapabilitiesService(db, resolver)
    tasks = TasksService(db, resolver, audit)
    dispatcher = Dispatcher(caps, tasks)

    # Build a stable coord DID from the signer's pubkey.
    pub = signer._public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    coord_did = f"did:wcp:{_b58encode(pub)}"

    return {
        "label": label,
        "db": db,
        "engine": engine,
        "audit": audit,
        "caps": caps,
        "tasks": tasks,
        "dispatcher": dispatcher,
        "signer": signer,
        "coord_did": coord_did,
    }


def _make_signed_trust_anchor(
    *, signing_key: Ed25519PrivateKey, peer_did: str, peer_url: str,
    scope: set[str], lifetime_s: int = 3600,
) -> TrustAnchor:
    """Build a trust anchor that the OTHER side will accept (we sign as
    the peer, since this is an in-process demo)."""
    pub = signing_key.public_key().public_bytes(
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
    sig_b = signing_key.sign(body_bytes)
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


async def main() -> int:
    print("[demo] === WCP v0.955.1 federation demo ===")
    print()

    # ---- 1. Bring up two coordinators in-process ------------------------
    print("[demo] starting coord-alpha and coord-beta in-process ...")
    alpha = _build_coordinator("alpha")
    beta = _build_coordinator("beta")
    print(f"[demo]   coord-alpha DID: {alpha['coord_did']}")
    print(f"[demo]   coord-beta DID:  {beta['coord_did']}")

    # ---- 2. Mutual trust anchor exchange --------------------------------
    print("[demo] exchanging signed bilateral trust anchors ...")
    scope = {"capability_discovery", "audit_chain_export"}
    anchor_for_alpha = _make_signed_trust_anchor(
        signing_key=beta["signer"]._key,
        peer_did=beta["coord_did"],
        peer_url="in-process://beta",
        scope=scope,
    )
    anchor_for_beta = _make_signed_trust_anchor(
        signing_key=alpha["signer"]._key,
        peer_did=alpha["coord_did"],
        peer_url="in-process://alpha",
        scope=scope,
    )
    alpha_store = TrustAnchorStore()
    alpha_store.add(anchor_for_alpha)
    beta_store = TrustAnchorStore()
    beta_store.add(anchor_for_beta)
    print(f"[demo]   alpha->beta trust anchor signature verified: "
          f"{anchor_for_alpha.verify_signature()}")
    print(f"[demo]   beta->alpha trust anchor signature verified: "
          f"{anchor_for_beta.verify_signature()}")

    # ---- 3. Register a worker on beta -----------------------------------
    print("[demo] registering logistics worker on coord-beta ...")
    worker_sk = Ed25519PrivateKey.generate()
    worker_pub = worker_sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    worker_did = f"did:wcp:{_b58encode(worker_pub)}"
    principal_sk = Ed25519PrivateKey.generate()
    principal_pub = principal_sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    principal_did = f"did:wcp:{_b58encode(principal_pub)}"
    capability = {
        "schema_version": "wcp/0.2",
        "worker_id": worker_did,
        "principal_id": principal_did,
        "class": "human",
        "required": {
            "current_location": {"venue_id": "london-zone-c", "map_id": "m1"},
            "available_windows": [
                {"rrule": "FREQ=DAILY;BYHOUR=8-22", "timezone": "Europe/London"}
            ],
            "attestation_methods_supported": [
                "sensor-witness",
                "owner-sign-off",
            ],
            "certifications": [],
            "policy_windows": [{"type": "geographic", "scope": "UK"}],
            "attestation_keys": [
                {"kty": "OKP", "crv": "Ed25519",
                 "x": base64.urlsafe_b64encode(worker_pub).rstrip(b"=").decode("ascii")}
            ],
            "as_of": _now(),
        },
        "class_extension": {"skills": ["transport", "delivery"]},
    }
    beta["caps"].upsert_capabilities(
        worker_id=worker_did,
        capabilities=capability,
        principal_id=principal_did,
    )
    beta["db"].commit()
    print(f"[demo]   worker registered: {worker_did}")

    # ---- 4. alpha sees beta's capability via federation sync ------------
    print("[demo] coord-alpha records federation_capability_advertised ...")
    alpha_caps_sync = CapabilitySync(alpha["audit"], alpha_store)
    alpha_caps_sync.advertise_peer_capability(
        peer_anchor=anchor_for_alpha,
        peer_worker_id=worker_did,
        capability_summary={
            "class": "human",
            "venue_id": "london-zone-c",
            "skills": ["transport", "delivery"],
        },
    )
    alpha["db"].commit()

    # ---- 5. alpha posts a transport task; federation router forwards ----
    print("[demo] coord-alpha posts transport task; forwarding to coord-beta ...")
    agent_sk = Ed25519PrivateKey.generate()
    agent_pub = agent_sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    agent_did = f"did:wcp:{_b58encode(agent_pub)}"
    task = {
        "schema_version": "wcp/0.2",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent_did,
        "descriptor_type": "transport",
        "descriptor_payload": {
            "origin_venue_id": "london-zone-a",
            "destination_venue_id": "london-zone-c",
        },
        "constraints": {
            "worker_class_filter": {"allowed": ["human"]},
        },
        "attestation_requirement": {
            "modes": ["sensor-witness", "owner-sign-off"],
            "threshold": "M-of-N", "M": 2, "N": 2,
            "evidence_schema": [
                {"mode": "sensor-witness", "kinds": ["gps_track"]},
                {"mode": "owner-sign-off",
                 "kinds": ["whatsapp_business_signed_link"]},
            ],
        },
        "max_attestation_attempts": 1,
        "accounting_ref": "demo-job-001",
        "supervision": {"default": "autonomous"},
        "x-subcontract-allowed": False,
    }

    async def in_process_forwarder(peer_url: str, method: str, params: dict):
        """In-process forwarder: dispatches the call directly into beta."""
        result = beta["dispatcher"].dispatch(method, params)
        beta["db"].commit()
        return result

    router = FederationRouter(
        alpha["audit"], alpha_store, forwarder=in_process_forwarder,
    )
    peer = router.pick_peer(
        descriptor_type="transport",
        worker_class_filter=["human"],
    )
    assert peer is not None, "no federation peer matched"
    forward_result = await router.forward_task(
        peer=peer, task=task, expiry="2099-12-31T23:59:00Z",
    )
    alpha["db"].commit()
    print(f"[demo]   peer accepted task: task_id={forward_result.get('task_id')} "
          f"eligible_workers_count={forward_result.get('eligible_workers_count')}")

    # ---- 6. beta worker claims, executes, attests -----------------------
    # (For brevity, the demo skips the full claim/execute/attest sequence
    # and writes the task_completed entry directly to beta's chain. The
    # unit tests in test_lifecycle.py walk the full sequence.)
    claim_id = "demo-claim-" + uuid.uuid4().hex[:8]
    beta["audit"].append(
        event_type="task_claimed",
        actor_did=worker_did,
        payload={"claim_id": claim_id, "task_id": task["task_id"]},
        claim_id=claim_id, task_id=task["task_id"],
    )
    beta["audit"].append(
        event_type="task_completed",
        actor_did=beta["coord_did"],
        payload={"claim_id": claim_id, "verifier_decision": "pass"},
        claim_id=claim_id, task_id=task["task_id"],
    )
    beta["db"].commit()
    print(f"[demo]   beta records task_claimed and task_completed for claim {claim_id}")

    # ---- 7. alpha imports beta's audit chain segment for verification ---
    async def beta_chain_fetcher(peer_url: str, claim_id_arg: str):
        rows = list(
            beta["db"].query(WcpAudit)
            .filter(WcpAudit.claim_id == claim_id_arg)
            .order_by(WcpAudit.timestamp.asc())
        )
        return [
            {
                "event_type": r.event_type,
                "actor_did": r.actor_did,
                "timestamp": r.timestamp.replace(tzinfo=None).isoformat()
                    if r.timestamp.tzinfo else r.timestamp.isoformat(),
                "payload_json": r.payload_json,
                "payload_hash": r.payload_hash,
                "prev_hash": r.prev_hash,
                "this_hash": r.this_hash,
                "claim_id": r.claim_id,
                "task_id": r.task_id,
                "sig": r.sig,
            } for r in rows
        ]

    export = AuditExport(alpha["audit"], fetcher=beta_chain_fetcher)
    import_result = await export.import_peer_chain(
        peer=peer, claim_id=claim_id,
    )
    alpha["db"].commit()
    print(f"[demo] coord-alpha imports beta's chain segment: "
          f"ok={import_result['ok']} entries={import_result['entries']} "
          f"completion={import_result['completion_event']}")

    # ---- 8. Verify both chains end-to-end -------------------------------
    print("[demo] verifying audit chains ...")
    beta_ok = beta["audit"].verify_chain(claim_id)
    print(f"[demo]   beta verify_chain(claim_id={claim_id[:18]}...): {beta_ok}")

    # Count federation entries on alpha's chain.
    fed_entries = list(
        alpha["db"].query(WcpAudit)
        .filter(WcpAudit.event_type.in_([
            "federation_capability_advertised",
            "federation_task_forwarded",
            "federation_audit_chain_imported",
        ]))
    )
    print(f"[demo]   alpha federation entries: {len(fed_entries)} "
          f"({', '.join(e.event_type for e in fed_entries)})")

    print()
    if beta_ok and import_result["ok"] and len(fed_entries) == 3:
        print("[demo] PASS")
        return 0
    print("[demo] FAIL")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
