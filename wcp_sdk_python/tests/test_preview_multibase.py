"""Tests for wcp_sdk.preview.multibase_identifier (RFC 0031 preview)."""
from __future__ import annotations

import warnings

import pytest

from wcp_sdk.preview import WCPPreviewWarning
from wcp_sdk.preview import multibase_identifier as mb


def test_encode_base58btc_default():
    pubkey = b"\x00" * 32
    did = mb.encode(pubkey)
    assert did.startswith("did:wcp:z")


def test_encode_base64url():
    pubkey = bytes(range(32))
    did = mb.encode(pubkey, encoding="base64url")
    assert did.startswith("did:wcp:u")


def test_encode_hex():
    pubkey = b"\xde\xad\xbe\xef"
    did = mb.encode(pubkey, encoding="hex")
    assert did == "did:wcp:fdeadbeef"


def test_encode_base32():
    pubkey = b"\x01\x02\x03\x04"
    did = mb.encode(pubkey, encoding="base32")
    assert did.startswith("did:wcp:b")


def test_encode_unsupported_raises():
    with pytest.raises(ValueError, match="unsupported encoding"):
        mb.encode(b"abc", encoding="rot13")


def test_decode_multibase_base58btc_roundtrip():
    pubkey = b"Hello, WCP-multibase!"
    did = mb.encode(pubkey)
    assert mb.decode(did) == pubkey


def test_decode_multibase_base64url_roundtrip():
    pubkey = bytes(range(40))
    did = mb.encode(pubkey, encoding="base64url")
    assert mb.decode(did) == pubkey


def test_decode_legacy_raw_base58btc():
    # Legacy v0.2 form: did:wcp:<base58btc> with no multibase prefix
    pubkey = b"legacy-test-key-payload-bytes!!!"
    # Build a known legacy identifier
    encoded = mb._b58btc_encode(pubkey)
    legacy_did = f"did:wcp:{encoded}"
    # Must NOT start with a multibase prefix
    assert not mb.is_multibase(legacy_did)
    # But must decode to the same bytes
    assert mb.decode(legacy_did) == pubkey


def test_is_multibase_true_for_v11():
    pubkey = b"x" * 32
    did = mb.encode(pubkey)
    assert mb.is_multibase(did)


def test_is_multibase_false_for_legacy():
    pubkey = b"legacy"
    encoded = mb._b58btc_encode(pubkey)
    legacy_did = f"did:wcp:{encoded}"
    assert not mb.is_multibase(legacy_did)


def test_decode_rejects_non_did_wcp():
    with pytest.raises(ValueError, match="not a did:wcp"):
        mb.decode("did:key:zABC")


def test_canonicalize_converts_legacy_to_multibase():
    pubkey = b"canonicalize-me"
    legacy = f"did:wcp:{mb._b58btc_encode(pubkey)}"
    canonical = mb.canonicalize(legacy)
    assert canonical.startswith("did:wcp:z")
    assert mb.decode(canonical) == pubkey


def test_canonicalize_idempotent_on_multibase():
    pubkey = b"already-multibase"
    did = mb.encode(pubkey)
    assert mb.canonicalize(did) == did


def test_encoding_used_distinguishes_forms():
    pubkey = b"\x00" * 16
    assert mb.encoding_used(mb.encode(pubkey, encoding="base58btc")) == "base58btc"
    assert mb.encoding_used(mb.encode(pubkey, encoding="base64url")) == "base64url"
    assert mb.encoding_used(mb.encode(pubkey, encoding="base32")) == "base32"
    assert mb.encoding_used(mb.encode(pubkey, encoding="hex")) == "hex"
    legacy = f"did:wcp:{mb._b58btc_encode(pubkey)}"
    assert mb.encoding_used(legacy) == "legacy"


def test_preview_warning_emitted_once_per_process():
    # Reset emitted set to ensure we observe the warning
    from wcp_sdk.preview import _emitted
    _emitted.discard("multibase_identifier:rfc31")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", WCPPreviewWarning)
        mb.encode(b"\x00" * 32)
        # The set is cleared above, so the first call must emit
        assert any(issubclass(rec.category, WCPPreviewWarning) for rec in w)
