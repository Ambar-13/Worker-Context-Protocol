"""
Canonical JSON and SHA-256 primitives shared across the SDK.

Implements a JSON serialization compatible with RFC 8785 (JCS) at the level
WCP needs: sorted keys, no whitespace, JSON's standard escape rules. Full
JCS conformance is a v1.1 RFC; v1.0-rc1 uses Python's `json.dumps(sort_keys=True, separators=(",", ":"))`,
which matches the harness used by the coordinator reference.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(payload: Any) -> bytes:
    """RFC 8785-compatible canonical JSON bytes for signing or hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """SHA-256 hash, lowercase hex-encoded."""
    return hashlib.sha256(data).hexdigest()
