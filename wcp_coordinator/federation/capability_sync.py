"""
Federation capability sync.

When a peer coordinator's worker becomes visible in our local
subscription stream, we record a `federation_capability_advertised`
entry on our audit chain. The trust-anchor scope must include
`capability_discovery`; otherwise we silently ignore the peer's
advertisement.

The capability descriptors themselves are NOT mutated. Our matching
engine treats peer capabilities as a separate result set that the
agent may opt into via `filter.federation = True` on
capabilities/subscribe.
"""
from __future__ import annotations

from typing import Any

from .trust_anchor import TrustAnchor, TrustAnchorStore


class CapabilitySync:
    def __init__(self, audit, anchors: TrustAnchorStore) -> None:
        self._audit = audit
        self._anchors = anchors

    def advertise_peer_capability(
        self,
        *,
        peer_anchor: TrustAnchor,
        peer_worker_id: str,
        capability_summary: dict[str, Any],
    ) -> None:
        """Record that a peer worker became visible to us."""
        if not peer_anchor.allows("capability_discovery"):
            return  # silently ignore: outside scope
        self._audit.append(
            event_type="federation_capability_advertised",
            actor_did=peer_anchor.peer_coordinator_did,
            payload={
                "peer_coordinator_did": peer_anchor.peer_coordinator_did,
                "peer_worker_id": peer_worker_id,
                "capability_summary": capability_summary,
            },
        )
