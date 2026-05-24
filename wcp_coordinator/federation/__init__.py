"""
Federation primitives for WCP v0.955.1.

Federation rides on the EXISTING eight RPCs. What this module adds:

  - Bilateral trust anchors with declared scope (which descriptor
    types and audit-chain entry kinds each side will accept from
    the other).
  - A router that forwards `tasks/post` to a peer coordinator when
    the task's worker_class_filter or capability_query matches a
    peer's advertised capability and the trust anchor scope allows it.
  - Three new audit-chain entry kinds:
      * `federation_capability_advertised` — a peer worker became
        visible in the local subscription stream
      * `federation_task_forwarded` — a task crossed the federation
        boundary outbound
      * `federation_audit_chain_imported` — a peer audit chain
        segment was fetched and verified locally

There is no global directory. Federation is opt-in per coordinator
pair and policy-gated by the bilateral trust anchor.
"""
from __future__ import annotations

from .trust_anchor import TrustAnchor, TrustAnchorStore
from .router import FederationRouter
from .capability_sync import CapabilitySync
from .audit_export import AuditExport

__all__ = [
    "TrustAnchor",
    "TrustAnchorStore",
    "FederationRouter",
    "CapabilitySync",
    "AuditExport",
]
