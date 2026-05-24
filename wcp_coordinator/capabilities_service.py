"""
Capabilities service: handles capabilities/list and capabilities/subscribe.

The service mutates state only after signature verification by DidResolver.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .did_resolver import (
    DIDResolutionError,
    DidResolver,
    SignatureVerificationError,
)
from .models import WcpSubscription, WcpWorker, WorkerClass


class CapabilitiesService:
    def __init__(self, db: Session, resolver: DidResolver) -> None:
        self._db = db
        self._resolver = resolver

    def upsert_capabilities(
        self,
        *,
        worker_id: str,
        capabilities: dict[str, Any],
        principal_id: str,
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        try:
            self._resolver.resolve(worker_id)
        except DIDResolutionError as exc:
            raise ValueError(f"DID_NOT_RESOLVED: {exc}") from exc

        # Accept both wcp/0.1 and wcp/0.2 capability envelopes. The v0.2
        # envelope is the v0.955 default; v0.1 is grandfathered for
        # back-compat. The capability structure itself is identical.
        if capabilities.get("schema_version") not in ("wcp/0.1", "wcp/0.2"):
            raise ValueError(
                "INVALID_PARAMS: capabilities.schema_version must be "
                "wcp/0.1 or wcp/0.2"
            )
        worker_class_str = capabilities.get("class")
        try:
            worker_class = WorkerClass(worker_class_str)
        except ValueError as exc:
            raise ValueError(
                f"INVALID_PARAMS: invalid worker class {worker_class_str!r}"
            ) from exc

        existing = self._db.get(WcpWorker, worker_id)
        if existing is None:
            row = WcpWorker(
                worker_id=worker_id,
                principal_id=principal_id,
                worker_class=worker_class,
                capabilities_json=capabilities,
                revision=1,
                ttl_seconds=ttl_seconds,
                as_of=datetime.now(timezone.utc),
            )
            self._db.add(row)
            self._db.flush()
            revision = 1
        else:
            existing.capabilities_json = capabilities
            existing.principal_id = principal_id
            existing.worker_class = worker_class
            existing.ttl_seconds = ttl_seconds
            existing.revision = (existing.revision or 0) + 1
            existing.as_of = datetime.now(timezone.utc)
            revision = existing.revision

        return {
            "worker_id": worker_id,
            "capabilities": capabilities,
            "ttl_seconds": ttl_seconds,
            "revision": revision,
        }

    def list_capabilities(self, *, worker_id: str) -> dict[str, Any]:
        row = self._db.get(WcpWorker, worker_id)
        if row is None:
            raise ValueError(f"DID_NOT_RESOLVED: worker {worker_id!r} unknown")
        return {
            "worker_id": row.worker_id,
            "capabilities": row.capabilities_json,
            "ttl_seconds": row.ttl_seconds,
            "revision": row.revision,
        }

    def create_subscription(
        self,
        *,
        agent_did: str,
        filter_dict: Optional[dict[str, Any]] = None,
        since_revision: Optional[int] = None,
        stream_endpoint_base: str = "wss://localhost/wcp/sub",
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        try:
            self._resolver.resolve(agent_did)
        except DIDResolutionError as exc:
            raise ValueError(f"DID_NOT_RESOLVED: {exc}") from exc
        sub_id = str(uuid.uuid4())
        endpoint = f"{stream_endpoint_base}/{sub_id}"
        sub = WcpSubscription(
            subscription_id=sub_id,
            agent_did=agent_did,
            filter_json=filter_dict,
            since_revision=since_revision,
            stream_endpoint=endpoint,
            ttl_seconds=ttl_seconds,
        )
        self._db.add(sub)
        self._db.flush()
        return {
            "subscription_id": sub_id,
            "stream_endpoint": endpoint,
            "ttl_seconds": ttl_seconds,
        }

    def matching_workers(
        self,
        *,
        capability_query: dict[str, Any],
        worker_class_filter: list[str],
    ) -> list[WcpWorker]:
        """In-process matcher.

        The matcher discriminates by STRUCTURAL properties only:

        - `worker_class_filter` (a list of `WorkerClass` values from the
          task's `constraints.worker_class_filter.allowed`)
        - `capability_query` against the worker's REQUIRED block:
          * `attestation_methods` — every requested method must be
            in the worker's `required.attestation_methods_supported`
          * `descriptor_types` — every requested descriptor type
            must be in the worker's `required.descriptor_types_supported`
            (absent means the worker accepts all types; the matcher
            does not enforce when the worker has not declared)
          * `certifications` — every requested certification id must
            be present in the worker's `required.certifications`
          * `location_venue_id` — must equal the worker's
            `required.current_location.venue_id`

        The matcher MUST NOT read the worker's `class_extension` block;
        that block is opaque to the matching engine by design. This
        invariant is enforced by `test_matching_ignores_class_extension`
        and is the load-bearing claim of Section 4 (the D4 forcing
        function).

        Production deployments swap this in-process scan for an indexed
        store (Postgres GIN, ElasticSearch, etc.); the discrimination
        invariants stay the same.
        """
        stmt = select(WcpWorker)
        if worker_class_filter:
            stmt = stmt.where(WcpWorker.worker_class.in_(worker_class_filter))
        candidates = list(self._db.execute(stmt).scalars())

        if not capability_query:
            return candidates

        wanted_methods = set(capability_query.get("attestation_methods", []) or [])
        wanted_descs = set(capability_query.get("descriptor_types", []) or [])
        wanted_certs = set(capability_query.get("certifications", []) or [])
        wanted_venue = capability_query.get("location_venue_id")

        matched: list[WcpWorker] = []
        for w in candidates:
            required = (w.capabilities_json or {}).get("required") or {}

            # attestation_methods: every requested method MUST be supported.
            if wanted_methods:
                supported = set(
                    required.get("attestation_methods_supported", []) or []
                )
                if not wanted_methods.issubset(supported):
                    continue

            # descriptor_types: only enforced when the worker DECLARES the
            # field. Absence means "accepts all"; declaring an empty list
            # means "accepts none".
            if wanted_descs and "descriptor_types_supported" in required:
                supported_descs = set(
                    required.get("descriptor_types_supported", []) or []
                )
                if not wanted_descs.issubset(supported_descs):
                    continue

            # certifications: every requested cert id MUST be present.
            if wanted_certs:
                worker_cert_ids = {
                    (c or {}).get("id")
                    for c in (required.get("certifications", []) or [])
                }
                if not wanted_certs.issubset(worker_cert_ids):
                    continue

            # venue: must match if requested.
            if wanted_venue is not None:
                worker_venue = (
                    (required.get("current_location") or {}).get("venue_id")
                )
                if worker_venue != wanted_venue:
                    continue

            matched.append(w)
        return matched
