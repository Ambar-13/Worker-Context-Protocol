"""
RFC 0031 preview: Multibase Identifier Migration.

Provides encode/decode/is_multibase helpers for the v1.1 `did:wcp:z<base58btc>`
identifier grammar, while remaining backward-compatible with v1.0-rc1's raw
`did:wcp:<base58>` form during the three-version compatibility window.

Encodings supported in this preview:
- base58btc (multibase prefix 'z') - the recommended default for v1.1
- base64url (prefix 'u') - URL-safe contexts
- base32 (prefix 'b') - case-insensitive contexts (RFC 4648)
- hex (prefix 'f') - debugging contexts (RFC 4648)

The preview does NOT implement on-wire migration for the reference coordinator
or SDKs. Both legacy and multibase forms are decodable; emission defaults to
multibase. See RFC 0031 for the full spec and three-version compatibility
window.
"""

from __future__ import annotations

import base64
from typing import Tuple

from . import emit_preview_warning


# Base58btc alphabet (per Multibase RFC; standard encoding for W3C DID methods
# that carry raw cryptographic identifier bytes). Excludes 0, O, I, l for
# visual disambiguation.
_B58_ALPHABET = (
    "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
)
_B58_INDEX = {ch: i for i, ch in enumerate(_B58_ALPHABET)}


def _b58btc_encode(data: bytes) -> str:
    if not data:
        return ""
    # Handle leading zeros.
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    n = int.from_bytes(data, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = _B58_ALPHABET[r] + out
    return ("1" * pad) + out


def _b58btc_decode(s: str) -> bytes:
    if not s:
        return b""
    pad = 0
    for ch in s:
        if ch == "1":
            pad += 1
        else:
            break
    n = 0
    for ch in s:
        if ch not in _B58_INDEX:
            raise ValueError(f"invalid base58btc character: {ch!r}")
        n = n * 58 + _B58_INDEX[ch]
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n > 0 else b""
    return (b"\x00" * pad) + body


# Multibase prefixes per draft-msporny-multibase.
_PREFIX_BASE58BTC = "z"
_PREFIX_BASE64URL = "u"
_PREFIX_BASE32 = "b"
_PREFIX_HEX = "f"

_KNOWN_PREFIXES = (
    _PREFIX_BASE58BTC,
    _PREFIX_BASE64URL,
    _PREFIX_BASE32,
    _PREFIX_HEX,
)


def encode(pubkey_bytes: bytes, encoding: str = "base58btc") -> str:
    """Encode pubkey bytes into a `did:wcp:<multibase>` identifier.

    Returns the full DID string (`did:wcp:z<base58btc>` by default).
    """
    emit_preview_warning(31, "multibase_identifier")
    if encoding == "base58btc":
        return f"did:wcp:{_PREFIX_BASE58BTC}{_b58btc_encode(pubkey_bytes)}"
    if encoding == "base64url":
        return f"did:wcp:{_PREFIX_BASE64URL}{base64.urlsafe_b64encode(pubkey_bytes).rstrip(b'=').decode('ascii')}"
    if encoding == "base32":
        return f"did:wcp:{_PREFIX_BASE32}{base64.b32encode(pubkey_bytes).rstrip(b'=').decode('ascii').lower()}"
    if encoding == "hex":
        return f"did:wcp:{_PREFIX_HEX}{pubkey_bytes.hex()}"
    raise ValueError(
        f"unsupported encoding {encoding!r}; supported: base58btc, base64url, base32, hex"
    )


def decode(identifier: str) -> bytes:
    """Decode a `did:wcp:...` identifier (legacy or multibase) into raw pubkey bytes.

    Accepts:
    - Legacy v1.0-rc1: `did:wcp:<base58btc-bytes>` (no multibase prefix)
    - Multibase v1.1: `did:wcp:z<base58btc-bytes>` (or u/b/f prefixes)

    Raises ValueError on malformed input.
    """
    emit_preview_warning(31, "multibase_identifier")
    if not identifier.startswith("did:wcp:"):
        raise ValueError(f"not a did:wcp identifier: {identifier!r}")
    body = identifier[len("did:wcp:") :]
    if not body:
        raise ValueError("empty did:wcp identifier body")
    if body[0] in _KNOWN_PREFIXES:
        prefix, payload = body[0], body[1:]
        if prefix == _PREFIX_BASE58BTC:
            return _b58btc_decode(payload)
        if prefix == _PREFIX_BASE64URL:
            return base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        if prefix == _PREFIX_BASE32:
            up = payload.upper()
            return base64.b32decode(up + "=" * (-len(up) % 8))
        if prefix == _PREFIX_HEX:
            return bytes.fromhex(payload)
    # Legacy raw-base58btc form (v1.0-rc1 compatibility).
    return _b58btc_decode(body)


def is_multibase(identifier: str) -> bool:
    """True if the identifier uses a v1.1 multibase prefix; False for legacy."""
    emit_preview_warning(31, "multibase_identifier")
    if not identifier.startswith("did:wcp:"):
        raise ValueError(f"not a did:wcp identifier: {identifier!r}")
    body = identifier[len("did:wcp:") :]
    return bool(body) and body[0] in _KNOWN_PREFIXES


def canonicalize(identifier: str) -> str:
    """Canonicalize any accepted form to the v1.1 base58btc multibase form.

    Used by v1.1 coordinators to index legacy identifiers under the canonical
    key. See RFC 0031 section "Identifier persistence".
    """
    emit_preview_warning(31, "multibase_identifier")
    raw = decode(identifier)
    return f"did:wcp:{_PREFIX_BASE58BTC}{_b58btc_encode(raw)}"


def encoding_used(identifier: str) -> str:
    """Return the multibase encoding name used in the identifier (or 'legacy')."""
    emit_preview_warning(31, "multibase_identifier")
    if not identifier.startswith("did:wcp:"):
        raise ValueError(f"not a did:wcp identifier: {identifier!r}")
    body = identifier[len("did:wcp:") :]
    if not body:
        raise ValueError("empty did:wcp identifier body")
    if body[0] == _PREFIX_BASE58BTC:
        return "base58btc"
    if body[0] == _PREFIX_BASE64URL:
        return "base64url"
    if body[0] == _PREFIX_BASE32:
        return "base32"
    if body[0] == _PREFIX_HEX:
        return "hex"
    return "legacy"
