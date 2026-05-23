"""
RFC 0034 preview: External Trust-Root Signed Evidence.

Provides the `ExternalTrustRoot` abstract base and three concrete subclasses
for the most common trust anchor types:
    JWKSTrustRoot          - JWKS URL hosting the trust anchor's keys
    X509ChainTrustRoot     - X.509 PKI chain
    DIDResolutionTrustRoot - non-did:wcp DID resolving to verifiable keys

Registry semantics: external trust roots register against well-known
identifiers under the `external-trust-root.<root-identifier>` evidence kind
family. The registry here is process-local; production deployments would
back it with an operator-side configuration store.

This preview does NOT fetch real trust anchors on import. Verification calls
are stubbed; production deployments implement the network and cryptographic
verification per the trust anchor type. The preview API surface matches the
v1.1-candidate interface so integrators can build against it now.
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import emit_preview_warning


# Registry of external-trust-root.<root-identifier> -> ExternalTrustRoot instance
_REGISTRY: dict[str, "ExternalTrustRoot"] = {}


@dataclass
class VerificationResult:
    """Outcome of an external trust root verification call."""

    accepted: bool
    reason: str = ""
    signer_identifier: Optional[str] = None
    signer_trust_anchor_ref: Optional[str] = None
    payload_age_seconds: Optional[float] = None


class ExternalTrustRoot(abc.ABC):
    """Abstract base for a trust root that verifies evidence signed against an
    external (non-did:wcp) authority.

    Subclasses implement `verify(evidence_payload)` per the trust anchor type.
    Each instance is registered under a `<root-identifier>` string; evidence
    referring to `external-trust-root.<root-identifier>` is dispatched here.
    """

    root_identifier: str
    """The identifier registered under external-trust-root.<root-identifier>."""

    signature_algorithm: str = "RS256"
    """Default signature algorithm; subclasses may override."""

    max_payload_age_seconds: int = 3600
    """Maximum age of evidence payload at verification time, per RFC 0034."""

    max_trust_anchor_age_seconds: int = 86400
    """Maximum age of cached trust anchor data before refresh, per RFC 0034."""

    def __init__(self, root_identifier: str, **kwargs: Any) -> None:
        emit_preview_warning(34, "external_trust_root")
        self.root_identifier = root_identifier
        for k, v in kwargs.items():
            setattr(self, k, v)

    @abc.abstractmethod
    def verify(self, evidence_payload: dict[str, Any]) -> VerificationResult:
        """Verify the evidence against this trust root.

        Concrete subclasses fetch the trust anchor (with caching), verify
        the signature, validate freshness, and return a VerificationResult.
        """
        ...


class JWKSTrustRoot(ExternalTrustRoot):
    """Trust root backed by a JWKS endpoint (RFC 7517).

    `jwks_url`: HTTPS URL serving the trust anchor's public keys as JWKS
    `freshness_field`: payload field with the issued_at timestamp
    """

    def __init__(
        self,
        root_identifier: str,
        *,
        jwks_url: str,
        signature_algorithm: str = "RS256",
        freshness_field: str = "issued_at",
        max_payload_age_seconds: int = 3600,
        max_trust_anchor_age_seconds: int = 86400,
    ) -> None:
        super().__init__(
            root_identifier,
            signature_algorithm=signature_algorithm,
            max_payload_age_seconds=max_payload_age_seconds,
            max_trust_anchor_age_seconds=max_trust_anchor_age_seconds,
        )
        self.jwks_url = jwks_url
        self.freshness_field = freshness_field
        # In production: cache the fetched JWKS with TTL = max_trust_anchor_age_seconds.
        # In this preview: keep cached_jwks=None and treat verification as stubbed.
        self.cached_jwks: Optional[dict[str, Any]] = None

    def verify(self, evidence_payload: dict[str, Any]) -> VerificationResult:
        if self.cached_jwks is None:
            return VerificationResult(
                accepted=False,
                reason=(
                    "preview: JWKS not cached. Production deployments fetch "
                    f"from {self.jwks_url} and verify the signature."
                ),
            )
        kid = evidence_payload.get("kid")
        ts_str = evidence_payload.get(self.freshness_field)
        if not ts_str:
            return VerificationResult(
                accepted=False,
                reason=f"missing freshness field: {self.freshness_field}",
            )
        # Freshness check
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if age > self.max_payload_age_seconds:
                return VerificationResult(
                    accepted=False,
                    reason=f"payload too old: {age:.0f}s > {self.max_payload_age_seconds}s",
                    payload_age_seconds=age,
                )
        except (ValueError, AttributeError) as exc:
            return VerificationResult(
                accepted=False, reason=f"freshness parse error: {exc}"
            )
        # Production: verify signature using JWKS key by kid
        return VerificationResult(
            accepted=True,
            reason="preview: structural validation passed; signature verification stubbed",
            signer_identifier=kid,
            signer_trust_anchor_ref=self.jwks_url,
            payload_age_seconds=age,
        )


class X509ChainTrustRoot(ExternalTrustRoot):
    """Trust root backed by an X.509 PKI chain.

    `trust_store_pem`: path or PEM content of the root CA / intermediate chain
    """

    def __init__(
        self,
        root_identifier: str,
        *,
        trust_store_pem: str,
        signature_algorithm: str = "RS256",
        max_payload_age_seconds: int = 3600,
    ) -> None:
        super().__init__(
            root_identifier,
            signature_algorithm=signature_algorithm,
            max_payload_age_seconds=max_payload_age_seconds,
        )
        self.trust_store_pem = trust_store_pem

    def verify(self, evidence_payload: dict[str, Any]) -> VerificationResult:
        # Production: parse the leaf certificate from evidence_payload,
        # walk the chain to trust_store_pem, verify signature.
        cert_serial = evidence_payload.get("certificate_serial")
        return VerificationResult(
            accepted=False,
            reason=(
                "preview: X.509 chain verification stubbed. Production "
                "deployments verify leaf-to-root chain and signature."
            ),
            signer_identifier=cert_serial,
            signer_trust_anchor_ref=f"x509:{self.root_identifier}",
        )


class DIDResolutionTrustRoot(ExternalTrustRoot):
    """Trust root backed by a non-did:wcp DID (e.g., did:web, did:key).

    `resolver_url`: optional resolver endpoint; if None, use universal resolver semantics
    """

    def __init__(
        self,
        root_identifier: str,
        *,
        did_method: str,
        resolver_url: Optional[str] = None,
        signature_algorithm: str = "EdDSA",
        max_payload_age_seconds: int = 3600,
    ) -> None:
        super().__init__(
            root_identifier,
            signature_algorithm=signature_algorithm,
            max_payload_age_seconds=max_payload_age_seconds,
        )
        self.did_method = did_method
        self.resolver_url = resolver_url

    def verify(self, evidence_payload: dict[str, Any]) -> VerificationResult:
        signer_did = evidence_payload.get("signer_did")
        if not signer_did or not signer_did.startswith(f"did:{self.did_method}:"):
            return VerificationResult(
                accepted=False,
                reason=(
                    f"signer_did missing or not a did:{self.did_method}: "
                    f"{signer_did!r}"
                ),
            )
        # Production: resolve the DID, fetch verification keys, verify signature.
        return VerificationResult(
            accepted=False,
            reason=(
                f"preview: did:{self.did_method} resolution stubbed. Production "
                "deployments resolve the DID and verify the signature."
            ),
            signer_identifier=signer_did,
            signer_trust_anchor_ref=f"did:{self.did_method}",
        )


def register_trust_root(
    root_identifier: str, root_instance: ExternalTrustRoot
) -> None:
    """Register an external trust root under its identifier.

    After registration, evidence with kind `external-trust-root.<root-identifier>`
    is verified by dispatching to `root_instance.verify()`.
    """
    emit_preview_warning(34, "external_trust_root")
    _REGISTRY[root_identifier] = root_instance


def unregister_trust_root(root_identifier: str) -> None:
    """Remove a trust root from the registry."""
    emit_preview_warning(34, "external_trust_root")
    _REGISTRY.pop(root_identifier, None)


def get_trust_root(root_identifier: str) -> Optional[ExternalTrustRoot]:
    """Look up a registered trust root."""
    emit_preview_warning(34, "external_trust_root")
    return _REGISTRY.get(root_identifier)


def verify_external_evidence(
    evidence_kind: str, evidence_payload: dict[str, Any]
) -> VerificationResult:
    """Dispatch verification to the trust root registered for the evidence kind.

    Evidence kind must be of the form `external-trust-root.<root-identifier>`.
    """
    emit_preview_warning(34, "external_trust_root")
    prefix = "external-trust-root."
    if not evidence_kind.startswith(prefix):
        return VerificationResult(
            accepted=False,
            reason=f"not an external-trust-root evidence kind: {evidence_kind!r}",
        )
    root_id = evidence_kind[len(prefix) :]
    root = _REGISTRY.get(root_id)
    if root is None:
        return VerificationResult(
            accepted=False,
            reason=f"no trust root registered for {root_id!r}",
        )
    return root.verify(evidence_payload)


def list_registered_roots() -> list[str]:
    """Return the sorted list of currently registered root identifiers."""
    emit_preview_warning(34, "external_trust_root")
    return sorted(_REGISTRY.keys())
