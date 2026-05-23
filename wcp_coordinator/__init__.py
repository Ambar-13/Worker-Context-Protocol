"""
WCP Coordinator: reference FastAPI backend for the Worker Context Protocol.

At v0.955 the protocol surface contracts to eight RPCs (tasks/settle removed)
and the dispute mechanism is replaced by a recheck flow on tasks/attest. See
spec/0.955.md for the architectural decision; this reference coordinator
tracks that spec layer.

Key design points:
- The attestation_verifier package is the SINGLE POINT where worker-class
  agnosticism is mechanically checked. See attestation_verifier/__init__.py.
- All signatures verified by did_resolver before any state mutation.
- All state transitions emit a hash-linked audit chain entry.
- v0.955: no settlement adapter. External settlement layers subscribe to the
  audit chain (task_completed, task_voided, task_aborted) and run their own
  value-flow logic.
"""

__version__ = "0.955.0"
__schema_version__ = "wcp/0.2"
