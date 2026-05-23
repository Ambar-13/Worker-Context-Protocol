"""
wcp_sdk.preview - v1.1-candidate preview implementations.

These modules implement v1.1-candidate RFCs as preview code. They are NOT
v1.1 final. The API may change before v1.1 ships. The v1.0 protocol surface
is unaffected.

Modules:
    multibase_identifier  - RFC 0031 (Multibase Identifier Migration)
    wcp_lite              - RFC 0029 (WCP-Lite for Intermittent Connectivity)
    trust_classes         - RFC 0033 (Attestation Key Trust Classes)
    external_trust_root   - RFC 0034 (External Trust-Root Signed Evidence)
    federation_settlement - RFC 0032 (Cross-Coordinator Settlement Clearing)

Every preview module emits WCPPreviewWarning on first use. Production
deployments SHOULD NOT depend on preview modules for v1.0 conformance;
they are explicitly intended for early implementer testing of v1.1
candidate features.

Import example:

    from wcp_sdk.preview import multibase_identifier
    did = multibase_identifier.encode(pubkey_bytes, encoding="base58btc")
    # WCPPreviewWarning: This is a v1.1 preview implementation of RFC 0031.
    # The API may change. v1.0 protocol surface is unaffected.
"""

from __future__ import annotations

import warnings
from typing import Optional


class WCPPreviewWarning(UserWarning):
    """Emitted on first use of any wcp_sdk.preview module.

    Filter via warnings.simplefilter('ignore', WCPPreviewWarning) if needed,
    but consider whether your code should depend on preview implementations
    in production.
    """


_emitted: set[str] = set()


def emit_preview_warning(rfc_number: int, module_name: str) -> None:
    """Emit a WCPPreviewWarning once per (rfc, module) pair per process.

    Called by each preview module on first invocation of a public function.
    """
    key = f"{module_name}:rfc{rfc_number}"
    if key in _emitted:
        return
    _emitted.add(key)
    warnings.warn(
        f"This is a v1.1 preview implementation of RFC {rfc_number:04d} "
        f"({module_name}). The API may change before v1.1 ships. The v1.0 "
        f"protocol surface is unaffected.",
        WCPPreviewWarning,
        stacklevel=3,
    )


# Convenience re-exports. Each individual import path also works (e.g.,
# `from wcp_sdk.preview.multibase_identifier import encode`).
from . import (  # noqa: E402,F401
    multibase_identifier,
    wcp_lite,
    trust_classes,
    external_trust_root,
    federation_settlement,
)

__all__ = [
    "WCPPreviewWarning",
    "emit_preview_warning",
    "multibase_identifier",
    "wcp_lite",
    "trust_classes",
    "external_trust_root",
    "federation_settlement",
]
