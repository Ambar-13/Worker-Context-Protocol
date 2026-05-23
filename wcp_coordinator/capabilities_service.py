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

        if capabilities.get("schema_version") != "wcp/0.1":
            raise ValueError(
                "INVALID_PARAMS: capabilities.schema_version must be wcp/0.1"
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
        self, *, capability_query: dict[str, Any], worker_class_filter: list[str]
    ) -> list[WcpWorker]:
        """Simple in-process matcher for v0.1. Production replaces with index."""
        stmt = select(WcpWorker)
        if worker_class_filter:
            stmt = stmt.where(WcpWorker.worker_class.in_(worker_class_filter))
        return list(self._db.execute(stmt).scalars())
