"""
Pytest fixtures for wcp_coordinator tests.

In-memory SQLite database; ephemeral Ed25519 signer; helper to construct a
signed worker DID and produce signed payloads.
"""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from wcp_coordinator.audit_chain import AuditChain, AuditSigner
from wcp_coordinator.capabilities_service import CapabilitiesService
from wcp_coordinator.did_resolver import DidResolver, _b58encode
from wcp_coordinator.models import Base
from wcp_coordinator.rpc_dispatch import Dispatcher
from wcp_coordinator.tasks_service import TasksService


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sig_str(key: Ed25519PrivateKey, payload: bytes) -> str:
    sig = key.sign(payload)
    return "ed25519:" + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine) -> Session:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def resolver() -> DidResolver:
    return DidResolver()


@pytest.fixture()
def signer() -> AuditSigner:
    return AuditSigner.ephemeral()


@pytest.fixture()
def services(db, resolver, signer):
    audit = AuditChain(db, signer)
    caps = CapabilitiesService(db, resolver)
    tasks = TasksService(db, resolver, audit)
    return caps, tasks, audit


@pytest.fixture()
def dispatcher(services):
    caps, tasks, _ = services
    return Dispatcher(caps, tasks)


class Identity:
    """Helper: a DID with its Ed25519 keypair, for tests."""

    def __init__(self, label: str = "test") -> None:
        self._key = Ed25519PrivateKey.generate()
        pub = self._key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.did = f"did:wcp:{_b58encode(pub)}"
        self.label = label

    def sign(self, payload: dict[str, Any]) -> str:
        return _sig_str(self._key, _canonical_json(payload))

    def sign_bytes(self, data: bytes) -> str:
        return _sig_str(self._key, data)


@pytest.fixture()
def worker_identity() -> Identity:
    return Identity("worker")


@pytest.fixture()
def agent_identity() -> Identity:
    return Identity("agent")


@pytest.fixture()
def principal_identity() -> Identity:
    return Identity("principal")


@pytest.fixture()
def customer_identity() -> Identity:
    return Identity("customer")


def make_capability(
    *,
    worker_id: str,
    principal_id: str,
    worker_class: str = "human",
    pubkey_b64url: str = "AAAA",
    skills: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "wcp/0.1",
        "worker_id": worker_id,
        "principal_id": principal_id,
        "class": worker_class,
        "required": {
            "current_location": {"venue_id": "v1", "map_id": "m1"},
            "available_windows": [
                {"rrule": "FREQ=DAILY;BYHOUR=8-22", "timezone": "Asia/Singapore"}
            ],
            "attestation_methods_supported": [
                "sensor-witness",
                "third-party-witness",
                "cryptographic-presence",
                "owner-sign-off",
            ],
            "certifications": [],
            "policy_windows": [{"type": "geographic", "scope": "Singapore"}],
            "attestation_keys": [
                {"kty": "OKP", "crv": "Ed25519", "x": pubkey_b64url}
            ],
            "as_of": "2026-05-23T00:00:00Z",
        },
        "class_extension": {"skills": skills or ["test_skill"]},
    }


def make_task(
    *,
    agent_did: str,
    descriptor_type: str = "scheduled_presence",
    descriptor_payload: dict | None = None,
    attestation_modes: list[str] | None = None,
    attestation_kinds: dict[str, list[str]] | None = None,
    M: int = 2,
    N: int = 2,
    worker_class_filter: list[str] | None = None,
    max_attestation_attempts: int = 1,
    accounting_ref: str | None = None,
) -> dict[str, Any]:
    modes = attestation_modes or ["cryptographic-presence", "owner-sign-off"]
    kinds_map = attestation_kinds or {
        "cryptographic-presence": ["geofence_check_in_out"],
        "owner-sign-off": ["whatsapp_business_signed_link"],
    }
    task: dict[str, Any] = {
        "schema_version": "wcp/0.2",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent_did,
        "descriptor_type": descriptor_type,
        "descriptor_payload": descriptor_payload or {"duration_minutes": 45},
        "constraints": {
            "time_window": {
                "earliest": "2026-06-01T00:00:00Z",
                "latest": "2026-06-01T23:59:00Z",
            },
            "worker_class_filter": {"allowed": worker_class_filter or ["human"]},
        },
        "attestation_requirement": {
            "modes": modes,
            "threshold": "M-of-N",
            "M": M,
            "N": N,
            "evidence_schema": [
                {"mode": m, "kinds": kinds_map.get(m, [])} for m in modes
            ],
        },
        "max_attestation_attempts": max_attestation_attempts,
        "x-subcontract-allowed": False,
    }
    if accounting_ref is not None:
        task["accounting_ref"] = accounting_ref
    return task


def make_acceptance(
    worker_identity: Identity, task_id: str, eta: str, bid: str | None = None
) -> dict[str, Any]:
    payload_hash = "0" * 64
    signed_at = datetime.now(timezone.utc).isoformat()
    canonical_payload = {
        "task_id": task_id,
        "worker_id": worker_identity.did,
        "eta": eta,
        "bid": bid,
        "payload_hash": payload_hash,
        "signed_at": signed_at,
    }
    sig = worker_identity.sign(canonical_payload)
    return {
        "sig": sig,
        "alg": "Ed25519",
        "payload_hash": payload_hash,
        "signed_at": signed_at,
    }


def make_evidence(
    worker_identity: Identity,
    claim_id: str,
    mode: str,
    kind: str,
    payload: dict[str, Any],
    collected_at: str | None = None,
) -> dict[str, Any]:
    collected_at = collected_at or datetime.now(timezone.utc).isoformat()
    payload_hash = "0" * 64
    canonical = {
        "mode": mode,
        "kind": kind,
        "payload_hash": payload_hash,
        "worker_id": worker_identity.did,
        "claim_id": claim_id,
        "collected_at": collected_at,
    }
    sig = worker_identity.sign(canonical)
    return {
        "schema_version": "wcp/0.1",
        "mode": mode,
        "kind": kind,
        "payload": payload,
        "payload_hash": payload_hash,
        "sig": sig,
        "worker_id": worker_identity.did,
        "claim_id": claim_id,
        "collected_at": collected_at,
    }
