# wcp-sdk (Python)

Worker Context Protocol (WCP) Python SDK.

This SDK is for implementers building WCP workers or agents in Python. It is **vendor-neutral**: it does not assume any specific operator, escrow provider, or currency.

## Status

Pre-v1.0 final. The surface follows `spec/1.0-rc1.md` and MAY change before v1.0 final.

## Install

```bash
pip install wcp-sdk
```

## Worker example

```python
import asyncio
from datetime import datetime, timezone
from wcp_sdk import (
    WorkerIdentity, WorkerSession,
    AttestationMode, CapabilityDescriptor, WorkerClass,
)

async def main():
    ident = WorkerIdentity.generate()
    async with await WorkerSession.connect(
        "wss://coordinator.example.org/wcp/ws", ident
    ) as session:
        # Publish capabilities.
        descriptor = CapabilityDescriptor(
            worker_id=ident.did,
            principal_id="did:wcp:my-employer",
            worker_class=WorkerClass.HUMAN,
            current_location={"venue_id": "v1", "map_id": "m1"},
            attestation_methods_supported=[
                "sensor-witness", "third-party-witness",
                "cryptographic-presence", "owner-sign-off",
            ],
            attestation_keys=[
                {"kty": "OKP", "crv": "Ed25519", "x": ident.public_key_b64url}
            ],
            class_extension={"skills": ["aircon_servicing_quarterly"]},
        )
        await session.publish_capabilities(descriptor)

        # Claim a task.
        result = await session.claim(
            task_id="...",
            eta=datetime.now(timezone.utc).isoformat(),
        )

        # Execute, attest, etc.
        # ...

asyncio.run(main())
```

## Agent example

```python
from wcp_sdk import AgentIdentity, AgentSession, AttestationMode, WorkerClass
from wcp_sdk.session import make_task_descriptor

agent = AgentIdentity.generate()
async with await AgentSession.connect(
    "wss://coordinator.example.org/wcp/ws", agent
) as session:
    task = make_task_descriptor(
        posted_by=agent.did,
        descriptor_type="scheduled_presence",
        descriptor_payload={"duration_minutes": 45},
        attestation_modes=[
            AttestationMode.CRYPTOGRAPHIC_PRESENCE,
            AttestationMode.OWNER_SIGN_OFF,
        ],
        attestation_kinds={
            "cryptographic-presence": ["geofence_check_in_out"],
            "owner-sign-off": ["whatsapp_business_signed_link"],
        },
        M=2, N=2,
        currency="SGD",
        amount="120.00",
        escrow_provider="example-escrow",
        split=[
            ("did:wcp:worker-principal", 80),
            ("did:wcp:platform", 15),
            ("did:wcp:insurance-pool", 5),
        ],
        worker_class_filter=[WorkerClass.HUMAN],
    )
    result = await session.post(
        task,
        bond_ref="example-bond-ref",
        expiry="2026-12-31T23:59:00Z",
    )
```

## License

Apache 2.0
