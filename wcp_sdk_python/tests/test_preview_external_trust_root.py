"""Tests for wcp_sdk.preview.external_trust_root (RFC 0034 preview)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from wcp_sdk.preview.external_trust_root import (
    DIDResolutionTrustRoot,
    ExternalTrustRoot,
    JWKSTrustRoot,
    VerificationResult,
    X509ChainTrustRoot,
    get_trust_root,
    list_registered_roots,
    register_trust_root,
    unregister_trust_root,
    verify_external_evidence,
)


@pytest.fixture(autouse=True)
def _clear_registry():
    """Each test starts with an empty registry and cleans up after."""
    from wcp_sdk.preview.external_trust_root import _REGISTRY

    _REGISTRY.clear()
    yield
    _REGISTRY.clear()


def test_register_and_lookup():
    root = JWKSTrustRoot(
        "test-root",
        jwks_url="https://example.test/.well-known/jwks.json",
    )
    register_trust_root("test-root", root)
    assert get_trust_root("test-root") is root


def test_unregister_removes():
    root = JWKSTrustRoot("test-root", jwks_url="https://example.test/jwks")
    register_trust_root("test-root", root)
    unregister_trust_root("test-root")
    assert get_trust_root("test-root") is None


def test_list_registered_roots_sorted():
    register_trust_root("zeta", JWKSTrustRoot("zeta", jwks_url="https://a/jwks"))
    register_trust_root("alpha", JWKSTrustRoot("alpha", jwks_url="https://b/jwks"))
    register_trust_root("mu", JWKSTrustRoot("mu", jwks_url="https://c/jwks"))
    assert list_registered_roots() == ["alpha", "mu", "zeta"]


def test_verify_external_evidence_unknown_kind():
    result = verify_external_evidence("external-trust-root.unknown-root", {})
    assert result.accepted is False
    assert "no trust root registered" in result.reason


def test_verify_external_evidence_wrong_prefix():
    result = verify_external_evidence("sensor-witness.gps_track", {})
    assert result.accepted is False
    assert "not an external-trust-root" in result.reason


def test_jwks_trust_root_missing_freshness_field():
    root = JWKSTrustRoot(
        "demo",
        jwks_url="https://example.test/jwks",
        freshness_field="issued_at",
    )
    root.cached_jwks = {"keys": []}  # pretend cache exists
    result = root.verify({"kid": "abc"})  # no issued_at
    assert result.accepted is False
    assert "missing freshness field" in result.reason


def test_jwks_trust_root_expired_payload():
    root = JWKSTrustRoot(
        "demo",
        jwks_url="https://example.test/jwks",
        max_payload_age_seconds=60,
    )
    root.cached_jwks = {"keys": []}
    old = (datetime.now(timezone.utc) - timedelta(seconds=3600)).isoformat()
    result = root.verify({"kid": "abc", "issued_at": old})
    assert result.accepted is False
    assert "too old" in result.reason
    assert result.payload_age_seconds is not None and result.payload_age_seconds > 60


def test_jwks_trust_root_fresh_payload_accepted_in_preview():
    root = JWKSTrustRoot("demo", jwks_url="https://example.test/jwks")
    root.cached_jwks = {"keys": []}
    fresh = datetime.now(timezone.utc).isoformat()
    result = root.verify({"kid": "abc", "issued_at": fresh})
    assert result.accepted is True
    assert result.signer_identifier == "abc"
    assert result.signer_trust_anchor_ref == "https://example.test/jwks"


def test_jwks_trust_root_no_cache_rejects():
    root = JWKSTrustRoot("demo", jwks_url="https://example.test/jwks")
    # cached_jwks is None
    result = root.verify({"kid": "abc", "issued_at": "2026-01-01T00:00:00Z"})
    assert result.accepted is False
    assert "JWKS not cached" in result.reason


def test_x509_chain_trust_root_returns_stub_preview_result():
    root = X509ChainTrustRoot("demo", trust_store_pem="-----BEGIN CERTIFICATE-----")
    result = root.verify({"certificate_serial": "01:23:45"})
    assert result.accepted is False
    assert "X.509" in result.reason
    assert result.signer_identifier == "01:23:45"


def test_did_resolution_trust_root_validates_did_method():
    root = DIDResolutionTrustRoot("demo", did_method="key")
    # Wrong method
    result = root.verify({"signer_did": "did:web:example.com"})
    assert result.accepted is False
    assert "did:key" in result.reason


def test_did_resolution_trust_root_accepts_matching_method_with_stub_verification():
    root = DIDResolutionTrustRoot("demo", did_method="key")
    result = root.verify({"signer_did": "did:key:zABC123"})
    assert result.accepted is False  # stubbed verification
    assert result.signer_identifier == "did:key:zABC123"
    assert "stubbed" in result.reason


def test_verify_external_evidence_dispatches_to_registered_root():
    root = JWKSTrustRoot("medical-vendor", jwks_url="https://medical.test/jwks")
    root.cached_jwks = {"keys": []}
    register_trust_root("medical-vendor", root)
    fresh = datetime.now(timezone.utc).isoformat()
    result = verify_external_evidence(
        "external-trust-root.medical-vendor",
        {"kid": "device-42", "issued_at": fresh},
    )
    assert result.accepted is True
    assert result.signer_identifier == "device-42"


def test_jwks_trust_root_freshness_field_override():
    root = JWKSTrustRoot(
        "vendor-x",
        jwks_url="https://vx.test/jwks",
        freshness_field="generated_at",
    )
    root.cached_jwks = {"keys": []}
    fresh = datetime.now(timezone.utc).isoformat()
    # Wrong field present, correct field absent: rejection
    result = root.verify({"kid": "k", "issued_at": fresh})
    assert result.accepted is False
    assert "generated_at" in result.reason
    # Correct field present: accept
    result = root.verify({"kid": "k", "generated_at": fresh})
    assert result.accepted is True


def test_external_trust_root_is_abstract():
    class IncompleteRoot(ExternalTrustRoot):
        pass

    with pytest.raises(TypeError):
        IncompleteRoot("test")
