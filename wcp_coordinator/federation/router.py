"""
Federation router: forwards tasks/post calls to peer coordinators when
the trust anchor scope and descriptor type allow.

The router does NOT add wire-level RPCs. It calls the peer's existing
`tasks/post` over JSON-RPC and records `federation_task_forwarded` on
the local audit chain.

For the reference coordinator and the federation demo, peer transport
is HTTPS+WebSocket. The router accepts a pluggable `forwarder` callable
so tests can supply an in-memory peer.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from .trust_anchor import TrustAnchor, TrustAnchorStore


# A forwarder is async (peer_url, method, params) -> result_dict.
# It raises if the peer refuses or is unreachable.
Forwarder = Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]]


class FederationRouter:
    def __init__(
        self,
        audit,
        anchors: TrustAnchorStore,
        forwarder: Optional[Forwarder] = None,
    ) -> None:
        self._audit = audit
        self._anchors = anchors
        self._forwarder = forwarder

    def pick_peer(
        self,
        *,
        descriptor_type: str,
        worker_class_filter: list[str],
        allowed_descriptor_types_per_peer: dict[str, set[str]] | None = None,
    ) -> Optional[TrustAnchor]:
        """Pick the first peer whose trust anchor scope allows
        capability_discovery AND whose declared accepted descriptor
        types include this task's descriptor_type.

        `allowed_descriptor_types_per_peer` lets the caller scope
        per-peer descriptor admission; absent, capability_discovery
        scope alone is the gate.
        """
        for anchor in self._anchors.anchors_for_class("capability_discovery"):
            if allowed_descriptor_types_per_peer is not None:
                accepted = allowed_descriptor_types_per_peer.get(
                    anchor.peer_coordinator_did, set()
                )
                if descriptor_type and descriptor_type not in accepted:
                    continue
            return anchor
        return None

    async def forward_task(
        self,
        *,
        peer: TrustAnchor,
        task: dict[str, Any],
        expiry: str,
        informational: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Forward a tasks/post call to the peer.

        Records federation_task_forwarded on the local audit chain
        regardless of whether the peer accepts (the audit chain is
        the forensic record either way; the peer's response or
        rejection is included on the same entry).
        """
        if self._forwarder is None:
            raise RuntimeError(
                "FederationRouter has no forwarder configured; "
                "set one at construction or via .with_forwarder()"
            )
        params: dict[str, Any] = {"task": task, "expiry": expiry}
        if informational:
            params.update(informational)

        try:
            result = await self._forwarder(
                peer.peer_endpoint_url, "tasks/post", params
            )
            status = "accepted"
        except Exception as exc:
            result = {"error": str(exc)}
            status = "rejected"

        self._audit.append(
            event_type="federation_task_forwarded",
            actor_did=peer.peer_coordinator_did,
            payload={
                "peer_coordinator_did": peer.peer_coordinator_did,
                "peer_endpoint_url": peer.peer_endpoint_url,
                "task_id": task.get("task_id"),
                "status": status,
                "peer_response": result,
            },
            task_id=task.get("task_id"),
        )
        return result

    def with_forwarder(self, forwarder: Forwarder) -> "FederationRouter":
        self._forwarder = forwarder
        return self
