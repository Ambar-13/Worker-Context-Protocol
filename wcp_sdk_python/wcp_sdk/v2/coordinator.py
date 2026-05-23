"""
v2 Coordinator extension-point API.

The Coordinator role is for operators running their own WCP coordinator. The
reference coordinator (`wcp_coordinator/`) implements the full contract; this
v2 wrapper provides a cleaner extension surface for the common cases.

For most operators, this class is a registration index rather than a
process-runner; the actual ASGI app lives in `wcp_coordinator.router`.

v0.955: the settlement_adapter registry is removed; settlement is no longer
a protocol concern. External settlement layers subscribe to the coordinator's
audit chain (task_completed, task_voided, task_aborted) instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


VerifierFn = Callable[[str, str, dict[str, Any]], dict[str, Any]]


@dataclass
class Coordinator:
    """Extension registry for a WCP coordinator deployment."""

    attestation_verifiers: dict[str, VerifierFn] = field(default_factory=dict)
    federation_trust_anchors: list[dict[str, Any]] = field(default_factory=list)

    def register_attestation_verifier(
        self, mode_or_kind: str, fn: VerifierFn
    ) -> None:
        """Register a custom verifier for a non-standard (mode, kind) pair.

        Conformant verifiers must still discriminate by (mode, kind) only,
        never by worker class or attempt number. See `spec/conformance.md`
        Level 2.
        """
        self.attestation_verifiers[mode_or_kind] = fn

    def add_federation_trust_anchor(self, anchor: dict[str, Any]) -> None:
        """Add a signed federation trust anchor.

        See `spec/federation.md` Section 1 for the trust anchor schema.
        """
        self.federation_trust_anchors.append(anchor)
