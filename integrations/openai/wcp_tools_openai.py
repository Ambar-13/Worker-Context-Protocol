"""WCP tools in the OpenAI function-calling format.

Worked-example domains: industrial-maintenance, healthcare-logistics.

Usage:

    from openai import OpenAI
    from integrations.openai.wcp_tools_openai import (
        WCP_FUNCTIONS, dispatch_function_call,
    )
    from wcp_sdk.v2 import Agent

    agent = Agent(name="gpt-driven-agent", coordinator="ws://localhost:8000/wcp/ws")
    client = OpenAI()
    async with agent:
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[...],
            tools=WCP_FUNCTIONS,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            for call in msg.tool_calls:
                result = await dispatch_function_call(
                    agent, call.function.name, json.loads(call.function.arguments)
                )
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from wcp_sdk.v2 import Agent


def _function(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


WCP_FUNCTIONS: list[dict[str, Any]] = [
    _function(
        "wcp_discover_capabilities",
        "Discover WCP workers eligible for a task.",
        {
            "type": "object",
            "properties": {
                "worker_class_filter": {"type": "array", "items": {"type": "string"}},
                "required_certifications": {"type": "array", "items": {"type": "string"}},
                "location_scope": {"type": "object"},
            },
        },
    ),
    _function(
        "wcp_post_task",
        "Post a WCP task descriptor with bonded escrow.",
        {
            "type": "object",
            "required": ["descriptor_type", "descriptor_payload",
                         "attestation_modes", "amount", "currency"],
            "properties": {
                "descriptor_type": {"type": "string"},
                "descriptor_payload": {"type": "object"},
                "attestation_modes": {"type": "array", "items": {"type": "string"}},
                "M": {"type": "integer", "default": 1},
                "N": {"type": "integer", "default": 1},
                "amount": {"type": "string"},
                "currency": {"type": "string"},
                "worker_class_filter": {"type": "array", "items": {"type": "string"}},
                "time_window_hours": {"type": "number", "default": 4},
            },
        },
    ),
    _function(
        "wcp_subscribe_attestation",
        "Subscribe to attestation outcomes for a posted task.",
        {
            "type": "object",
            "required": ["task_id"],
            "properties": {"task_id": {"type": "string"}},
        },
    ),
    _function(
        "wcp_get_audit_chain",
        "Fetch the hash-linked audit chain entries for a task.",
        {
            "type": "object",
            "required": ["task_id"],
            "properties": {"task_id": {"type": "string"}},
        },
    ),
]


async def dispatch_function_call(
    agent: Agent, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    if name == "wcp_discover_capabilities":
        return await agent.discover_capabilities(filter=arguments or {})
    if name == "wcp_post_task":
        return await _post(agent, arguments)
    if name == "wcp_subscribe_attestation":
        return {"subscribed": True, "task_id": arguments["task_id"]}
    if name == "wcp_get_audit_chain":
        return {"task_id": arguments["task_id"], "note": "audit-chain endpoint pending"}
    return {"error": f"unknown function: {name}"}


async def _post(agent: Agent, args: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    modes = args["attestation_modes"]
    M = int(args.get("M", 1))
    N = int(args.get("N", max(1, len(modes))))
    task = {
        "schema_version": "wcp/0.2",
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
            "worker_class_filter": {
                "allowed": args.get("worker_class_filter", ["human"])
            },
        },
        "attestation_requirement": {
            "modes": modes, "threshold": "M-of-N", "M": M, "N": N,
            "evidence_schema": [{"mode": m, "kinds": []} for m in modes],
        },
                "supervision": {"default": "autonomous"},
        "x-subcontract-allowed": False,
    }
    return await agent.post_task(
        task,
        expiry=(now + timedelta(hours=24)).isoformat(),
    )
