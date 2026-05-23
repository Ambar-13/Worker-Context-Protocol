"""
Worker Context Protocol (WCP) Python SDK.

This SDK is for implementers building WCP workers or agents in Python. It is
vendor-neutral: it does not depend on any specific operator, escrow provider,
or currency. The reference coordinator (wcp_coordinator/) is ONE possible
endpoint the SDK can talk to; the SDK is not bound to that implementation.

Key entry points:

    from wcp_sdk import (
        WorkerIdentity,
        WorkerSession,
        AgentSession,
        canonical_json_bytes,
        TaskDescriptor,
        AttestationEvidence,
        CapabilityDescriptor,
        WcpRpcError,
    )

    # Worker side:
    identity = WorkerIdentity.generate()
    async with WorkerSession.connect("wss://coordinator.example.org/wcp/ws", identity) as ws:
        await ws.publish_capabilities(descriptor)
        await ws.claim(task_id, eta=...)
        await ws.attest(claim_id, [evidence])

    # Agent side:
    async with AgentSession.connect("wss://coordinator.example.org/wcp/ws", agent_did) as ag:
        result = await ag.post(task, bond_ref=..., expiry=...)
"""

from .canonical import canonical_json_bytes, sha256_hex
from .identity import WorkerIdentity, AgentIdentity, did_from_pubkey
from .rpc_client import RpcClient, WcpRpcError, JsonRpcResponse
from .session import WorkerSession, AgentSession
from .types import (
    AttestationEvidence,
    AttestationMode,
    CapabilityDescriptor,
    TaskDescriptor,
    VerifierDecision,
    WorkerClass,
)

__version__ = "0.95.0"
__schema_version__ = "wcp/1.0-rc1"

# v2 additive imports (decorator-style three-role API). Available as
# `from wcp_sdk.v2 import Worker, Agent, Coordinator`. v1 imports unchanged.
from . import v2  # noqa: E402,F401

__all__ = [
    "WorkerIdentity",
    "AgentIdentity",
    "WorkerSession",
    "AgentSession",
    "RpcClient",
    "WcpRpcError",
    "JsonRpcResponse",
    "TaskDescriptor",
    "CapabilityDescriptor",
    "AttestationEvidence",
    "AttestationMode",
    "VerifierDecision",
    "WorkerClass",
    "canonical_json_bytes",
    "sha256_hex",
    "did_from_pubkey",
    "__version__",
    "__schema_version__",
]
