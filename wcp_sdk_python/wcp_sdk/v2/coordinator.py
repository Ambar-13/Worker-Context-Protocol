"""
v2 Coordinator extension-point API.

The Coordinator role is for operators running their own WCP marketplace. The
reference coordinator (`wcp_coordinator/`) implements the full contract; this
v2 wrapper provides a cleaner extension surface for the common cases.

For most operators, this class is a registration index rather than a
process-runner; the actual ASGI app lives in `wcp_coordinator.router`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


VerifierFn = Callable[[str, str, dict[str, Any]], dict[str, Any]]


@dataclass
class Coordinator:
    """Extension registry for a WCP coordinator deployment."""

    attestation_verifiers: dict[str, VerifierFn] = field(default_factory=dict)
    settlement_adapters: dict[str, Any] = field(default_factory=dict)
    federation_trust_anchors: list[dict[str, Any]] = field(default_factory=list)

    def register_attestation_verifier(
        self, mode_or_kind: str, fn: VerifierFn
    ) -> None:
        """Register a custom verifier for a non-standard (mode, kind) pair.

        Conformant verifiers must still discriminate by (mode, kind) only,
        never by worker class. See `spec/conformance.md` Level 2.
        """
        self.attestation_verifiers[mode_or_kind] = fn

    def register_settlement_adapter(self, escrow_provider: str, adapter: Any) -> None:
        """Register an additional settlement provider.

        WCP's settlement_adapter protocol requires .hold, .capture, .refund,
        .cancel methods returning SettlementOutcome. See
        `wcp_coordinator.settlement_adapter.SettlementAdapter`.
        """
        self.settlement_adapters[escrow_provider] = adapter

    def add_federation_trust_anchor(self, anchor: dict[str, Any]) -> None:
        """Add a signed federation trust anchor.

        See `spec/federation.md` Section 1 for the trust anchor schema.
        """
        self.federation_trust_anchors.append(anchor)
