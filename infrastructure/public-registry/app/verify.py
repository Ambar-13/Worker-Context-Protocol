"""Signature verification on coordinator registrations.

A coordinator signs its own descriptor with the Ed25519 key whose public
half is in `public_key_multibase`. The signed bytes are the descriptor
JSON canonicalised per RFC 8785 (JCS) with the `signature` field omitted.

This module isolates the cryptography. For preview use, it relies on the
PyNaCl library if available; if not, it short-circuits with a permissive
mode logged as a WARNING.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from nacl.exceptions import BadSignatureError
    from nacl.signing import VerifyKey
    _HAS_NACL = True
except ImportError:  # pragma: no cover
    _HAS_NACL = False
    logger.warning(
        "PyNaCl not installed; registry will accept registrations without "
        "verifying signatures. Install pynacl for production use."
    )


def _canonicalise_for_signing(descriptor: dict[str, Any]) -> bytes:
    """RFC-8785-style canonical JSON of the descriptor minus signature.

    Real JCS would require sorted keys, no whitespace, and specific
    number formatting. Python's json.dumps(sort_keys=True, separators)
    matches JCS for the data shapes used here (no scientific notation,
    no float exponents).
    """
    work = {k: v for k, v in descriptor.items() if k != "signature"}
    return json.dumps(
        work, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _decode_multibase_pubkey(multibase: str) -> bytes:
    """Decode a base58btc multibase string (prefix 'z') to raw bytes.

    For other multibase prefixes, this preview only handles 'z' (the
    encoding used by did:key and the WCP default). Other encodings raise.
    """
    if not multibase.startswith("z"):
        raise ValueError(
            f"only base58btc multibase ('z' prefix) supported in preview; "
            f"got {multibase[:1]!r}"
        )
    body = multibase[1:]
    # Inline base58btc decoder (avoid adding a dependency)
    alphabet = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = 0
    for ch in body.encode("utf-8"):
        if ch not in alphabet:
            raise ValueError(f"invalid base58 char {chr(ch)!r}")
        n = n * 58 + alphabet.index(ch)
    out = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    # Leading 'z' zeros not handled here for brevity; production decoders do
    return out


def verify_descriptor_signature(descriptor: dict[str, Any]) -> bool:
    """Return True if the signature verifies against public_key_multibase."""
    if not _HAS_NACL:
        # Permissive mode: warning already logged at module import
        return True
    try:
        pubkey_bytes = _decode_multibase_pubkey(
            descriptor["public_key_multibase"]
        )
    except (KeyError, ValueError) as e:
        logger.info("signature verification failed: %s", e)
        return False
    # Ed25519 public keys are 32 bytes
    if len(pubkey_bytes) != 32:
        logger.info(
            "signature verification failed: expected 32-byte Ed25519 pubkey, "
            "got %d", len(pubkey_bytes),
        )
        return False
    canonical = _canonicalise_for_signing(descriptor)
    sig_b64u = descriptor.get("signature", "")
    try:
        import base64
        sig = base64.urlsafe_b64decode(sig_b64u + "==")
    except Exception as e:
        logger.info("signature decode failed: %s", e)
        return False
    try:
        VerifyKey(pubkey_bytes).verify(canonical, sig)
        return True
    except BadSignatureError:
        return False
