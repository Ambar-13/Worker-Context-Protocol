"""WCP tools as Gemini function declarations.

Worked-example domains: logistics, field-research.

The Gemini function-calling schema differs in surface shape from OpenAI's
but is structurally equivalent. This file emits both the function
declarations and a dispatcher.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from wcp_sdk.v2 import Agent


def _declaration(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "description": description, "parameters": parameters}


WCP_FUNCTION_DECLARATIONS: list[dict[str, Any]] = [
    _declaration(
        "wcp_discover_capabilities",
        "Discover WCP workers eligible for a task.",
        {"type": "OBJECT", "properties": {
            "worker_class_filter": {"type": "ARRAY", "items": {"type": "STRING"}},
            "location_scope": {"type": "OBJECT"},
        }},
    ),
    _declaration(
        "wcp_post_task",
        "Post a WCP task descriptor with bonded escrow.",
        {"type": "OBJECT", "properties": {
            "descriptor_type": {"type": "STRING"},
            "descriptor_payload": {"type": "OBJECT"},
            "attestation_modes": {"type": "ARRAY", "items": {"type": "STRING"}},
            "M": {"type": "INTEGER"},
            "N": {"type": "INTEGER"},
            "amount": {"type": "STRING"},
            "currency": {"type": "STRING"},
            "worker_class_filter": {"type": "ARRAY", "items": {"type": "STRING"}},
            "time_window_hours": {"type": "NUMBER"},
        }, "required": ["descriptor_type", "descriptor_payload", "attestation_modes",
                        "amount", "currency"]},
    ),
    _declaration(
        "wcp_subscribe_attestation",
        "Subscribe to attestation outcomes for a posted task.",
        {"type": "OBJECT", "properties": {"task_id": {"type": "STRING"}},
         "required": ["task_id"]},
    ),
    _declaration(
        "wcp_get_audit_chain",
        "Fetch the hash-linked audit chain entries for a task.",
        {"type": "OBJECT", "properties": {"task_id": {"type": "STRING"}},
         "required": ["task_id"]},
    ),
]


async def dispatch_function_call(
    agent: Agent, name: str, args: dict[str, Any]
) -> dict[str, Any]:
    if name == "wcp_discover_capabilities":
        return await agent.discover_capabilities(filter=args or {})
    if name == "wcp_post_task":
        return await _post(agent, args)
    if name == "wcp_subscribe_attestation":
        return {"subscribed": True, "task_id": args["task_id"]}
    if name == "wcp_get_audit_chain":
        return {"task_id": args["task_id"], "note": "audit-chain endpoint pending"}
    return {"error": f"unknown function: {name}"}


async def _post(agent: Agent, args: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    modes = args["attestation_modes"]
    M = int(args.get("M", 1))
    N = int(args.get("N", max(1, len(modes))))
    task = {
        "schema_version": "wcp/1.0-rc1",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": args["descriptor_type"],
        "descriptor_payload": args["descriptor_payload"],
        "constraints": {
            "time_window": {
                "earliest": now.isoformat(),
                "latest": (
                    now + timedelta(hours=args.get("time_window_hours", 4))
                ).isoformat(),
            },
            "worker_class_filter": {"allowed": args.get("worker_class_filter", ["human"])},
        },
        "attestation_requirement": {
            "modes": modes, "threshold": "M-of-N", "M": M, "N": N,
            "evidence_schema": [{"mode": m, "kinds": []} for m in modes],
            "override_authority": "did:wcp:example-operator-ops",
            "override_audit_required": True,
        },
        "settlement": {
            "currency": args["currency"], "amount": args["amount"],
            "escrow_provider": "example-escrow",
            "split": [{"party": "did:wcp:worker-pool", "pct": 100}],
        },
        "supervision": {"default": "autonomous"},
        "x-subcontract-allowed": False,
    }
    return await agent.post_task(
        task,
        bond_ref=f"example-bond-{task['task_id']}",
        expiry=(now + timedelta(hours=24)).isoformat(),
    )
