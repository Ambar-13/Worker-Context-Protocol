"""WCP tools for CrewAI.

Worked-example domains: industrial-maintenance, scientific-ops.
"""
from __future__ import annotations

import json
from typing import Any

from wcp_sdk.v2 import Agent

try:
    from crewai_tools import tool  # type: ignore[import-not-found]
except ImportError:
    tool = None  # type: ignore[assignment]

from integrations.langchain.wcp_langchain_tools import _post  # type: ignore[import-not-found]


def make_wcp_tools(agent: Agent) -> list[Any]:
    if tool is None:
        raise ImportError("crewai-tools is required: pip install crewai-tools")

    @tool("wcp_discover_capabilities")
    async def discover(filter_json: str = "{}") -> str:
        """Discover WCP workers eligible for a task."""
        return json.dumps(await agent.discover_capabilities(filter=json.loads(filter_json)))

    @tool("wcp_post_task")
    async def post(args_json: str) -> str:
        """Post a WCP task descriptor with bonded escrow."""
        return json.dumps(await _post(agent, json.loads(args_json)))

    @tool("wcp_subscribe_attestation")
    async def subscribe(task_id: str) -> str:
        """Subscribe to attestation outcomes for a posted task_id."""
        return json.dumps({"subscribed": True, "task_id": task_id})

    @tool("wcp_get_audit_chain")
    async def audit(task_id: str) -> str:
        """Fetch the audit chain for a task_id."""
        return json.dumps({"task_id": task_id, "note": "audit-chain endpoint pending"})

    return [discover, post, subscribe, audit]
