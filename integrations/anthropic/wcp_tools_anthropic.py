"""WCP tools for the Anthropic Messages API tool-use format.

Worked-example domains: scientific-ops, disaster-response. Plug-in for any
operator's coordinator; no operator-specific assumptions.

Usage:

    from anthropic import Anthropic
    from integrations.anthropic.wcp_tools_anthropic import (
        WCP_TOOLS, dispatch_tool_call,
    )
    from wcp_sdk.v2 import Agent

    agent = Agent(name="claude-driven-agent", coordinator="ws://localhost:8000/wcp/ws")
    client = Anthropic()

    async with agent:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            tools=WCP_TOOLS,
            messages=[{"role": "user", "content": "Dispatch a calibration on spectrometer-12"}],
        )
        for block in resp.content:
            if block.type == "tool_use":
                tool_result = await dispatch_tool_call(agent, block.name, block.input)
                # feed tool_result back into the next messages call
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from wcp_sdk.v2 import Agent


WCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "wcp_discover_capabilities",
        "description": (
            "Discover WCP workers eligible for a task. Filter on worker class, "
            "certifications, location scope, attestation methods."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "worker_class_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "subset of: human, autonomous_robot, teleoperated_robot, semi_autonomous, hybrid",
                },
                "required_certifications": {
                    "type": "array", "items": {"type": "string"},
                },
                "location_scope": {"type": "object"},
            },
        },
    },
    {
        "name": "wcp_post_task",
        "description": (
            "Post a WCP TaskDescriptor. v0.955: settlement is not a protocol concern; pass marketplace_ref to correlate with an external settlement layer if needed."
        ),
        "input_schema": {
            "type": "object",
            "required": [
                "descriptor_type", "descriptor_payload", "attestation_modes",
                "amount", "currency",
            ],
            "properties": {
                "descriptor_type": {
                    "type": "string",
                    "description": "transport, scheduled_presence, observe_and_report, or application-defined",
                },
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
    },
    {
        "name": "wcp_subscribe_attestation",
        "description": "Subscribe to attestation outcomes for a posted task.",
        "input_schema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {"task_id": {"type": "string"}},
        },
    },
    {
        "name": "wcp_get_audit_chain",
        "description": "Fetch the hash-linked audit chain entries for a task.",
        "input_schema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {"task_id": {"type": "string"}},
        },
    },
]


async def dispatch_tool_call(
    agent: Agent, tool_name: str, tool_input: dict[str, Any]
) -> dict[str, Any]:
    """Execute a Claude tool_use block by calling into the WCP coordinator."""
    if tool_name == "wcp_discover_capabilities":
        filter_dict = {
            k: v for k, v in tool_input.items()
            if k in ("worker_class_filter", "required_certifications", "location_scope")
        }
        return await agent.discover_capabilities(filter=filter_dict)

    if tool_name == "wcp_post_task":
        return await _post_via_tool(agent, tool_input)

    if tool_name == "wcp_subscribe_attestation":
        # In a long-running session, this yields stream events. Returning a
        # subscription marker keeps the tool call synchronous-friendly.
        return {"subscribed": True, "task_id": tool_input["task_id"]}

    if tool_name == "wcp_get_audit_chain":
        # The reference coordinator exposes audit chain via /wcp/audit/<task_id>
        # in a future RFC. Until that endpoint ships, return a stub indicating
        # the call was recorded.
        return {"task_id": tool_input["task_id"], "note": "audit-chain endpoint pending"}

    return {"error": f"unknown tool: {tool_name}"}


async def _post_via_tool(agent: Agent, tool_input: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    modes = tool_input["attestation_modes"]
    M = int(tool_input.get("M", 1))
    N = int(tool_input.get("N", max(1, len(modes))))
    task = {
        "schema_version": "wcp/0.2",
        "task_id": str(uuid.uuid4()),
        "posted_by": agent.did,
        "descriptor_type": tool_input["descriptor_type"],
        "descriptor_payload": tool_input["descriptor_payload"],
        "constraints": {
            "time_window": {
                "earliest": now.isoformat(),
                "latest": (
                    now + timedelta(hours=tool_input.get("time_window_hours", 4))
                ).isoformat(),
            },
            "worker_class_filter": {
                "allowed": tool_input.get("worker_class_filter", ["human"])
            },
        },
        "attestation_requirement": {
            "modes": modes, "threshold": "M-of-N", "M": M, "N": N,
            "evidence_schema": [
                {"mode": m, "kinds": _default_kinds(m)} for m in modes
            ],
        },
        "max_attestation_attempts": 1,
        "marketplace_ref": tool_input.get("marketplace_ref"),
        "supervision": {"default": "autonomous"},
        "x-subcontract-allowed": False,
    }
    return await agent.post_task(
        task,
        expiry=(now + timedelta(hours=24)).isoformat(),
    )


def _default_kinds(mode: str) -> list[str]:
    return {
        "sensor-witness": ["gps_track", "signed_sensor_recording", "photo_with_exif"],
        "third-party-witness": ["customer_signature", "iot_beacon_proximity"],
        "cryptographic-presence": ["geofence_check_in_out"],
        "owner-sign-off": ["whatsapp_business_signed_link"],
    }.get(mode, [])
