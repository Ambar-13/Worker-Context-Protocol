"""
WCP Coordinator: reference FastAPI backend for the Worker Context Protocol v0.1.

This module is designed to be merged into the existing Rentably FastAPI service.
At v0.1 it ships as a standalone Python package importable as `wcp_coordinator`.

Architecture: see PLAN.md Section 2.3 and spec/0.1.md.

Key design points:
- The attestation_verifier package is the SINGLE POINT where worker-class
  agnosticism is mechanically checked. See attestation_verifier/__init__.py.
- All signatures verified by did_resolver before any state mutation.
- All state transitions emit a hash-linked audit chain entry.
- Stripe two-phase escrow wrapped by settlement_adapter (INTEGRATION-GAP at v0.1).
"""

__version__ = "0.1.0"
__schema_version__ = "wcp/0.1"
