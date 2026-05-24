"""
Federation primitives for WCP v0.955.1.

Federation rides on the EXISTING eight lifecycle RPCs. What this
module adds:

  - Bilateral trust anchors with declared scope (which descriptor
    types and audit-chain entry kinds each side will accept from
    the other).
  - A router that forwards `tasks/post` to a peer coordinator when
    the task's worker_class_filter or capability_query matches a
    peer's advertised capability and the trust anchor scope allows it.
  - Four audit-chain entry kinds added at the federation layer:
      * `federation_capability_advertised` — a peer worker became
        visible in the local subscription stream
      * `federation_task_forwarded` — a task crossed the federation
        boundary outbound
      * `federation_audit_chain_imported` — a peer audit chain
        segment was fetched and verified locally
      * `federation_trust_anchor_revoked` — the operator revoked
        the trust relationship with a peer (added at v0.955.1)

There is no global directory. Federation is opt-in per coordinator
pair and policy-gated by the bilateral trust anchor. Per-peer
descriptor admission lives in the coordinator's routing layer (the
FederationRouter `allowed_descriptor_types_per_peer` argument), NOT
in the trust anchor: the anchor declares trust-class scope, the
coordinator declares its admission policy. Revocation is recorded as
`federation_trust_anchor_revoked` on the audit chain; mid-session
anchor invalidation is the operator's call.
"""
from __future__ import annotations

from .trust_anchor import TrustAnchor, TrustAnchorStore
from .router import FederationRouter, PeerTrustAnchorRevoked
from .capability_sync import CapabilitySync
from .audit_export import AuditExport
from .transport import WsForwarder, HttpChainFetcher

__all__ = [
    "TrustAnchor",
    "TrustAnchorStore",
    "FederationRouter",
    "PeerTrustAnchorRevoked",
    "CapabilitySync",
    "AuditExport",
    "WsForwarder",
    "HttpChainFetcher",
]
