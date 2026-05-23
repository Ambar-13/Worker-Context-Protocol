"""WCP tools for LlamaIndex.

Worked-example domains: field-research, healthcare-logistics.
"""
from __future__ import annotations

import json
from typing import Any

from wcp_sdk.v2 import Agent

try:
    from llama_index.core.tools import FunctionTool  # type: ignore[import-not-found]
except ImportError:
    FunctionTool = None  # type: ignore[assignment]

from integrations.langchain.wcp_langchain_tools import _post  # type: ignore[import-not-found]


def make_wcp_tools(agent: Agent) -> list[Any]:
    """Return a list of LlamaIndex FunctionTools bound to the given agent."""
    if FunctionTool is None:
        raise ImportError("llama-index-core is required: pip install llama-index-core")

    async def discover(filter_json: str = "{}") -> str:
        return json.dumps(await agent.discover_capabilities(filter=json.loads(filter_json)))

    async def post(args_json: str) -> str:
        return json.dumps(await _post(agent, json.loads(args_json)))

    async def subscribe(task_id: str) -> str:
        return json.dumps({"subscribed": True, "task_id": task_id})

    async def audit(task_id: str) -> str:
        return json.dumps({"task_id": task_id, "note": "audit-chain endpoint pending"})

    return [
        FunctionTool.from_defaults(
            fn=discover, name="wcp_discover_capabilities",
            description="Discover WCP workers; arg is a JSON filter.",
            async_fn=discover,
        ),
        FunctionTool.from_defaults(
            fn=post, name="wcp_post_task",
            description="Post a WCP task. Arg is the task spec as a JSON string.",
            async_fn=post,
        ),
        FunctionTool.from_defaults(
            fn=subscribe, name="wcp_subscribe_attestation",
            description="Subscribe to attestation outcomes for a task_id.",
            async_fn=subscribe,
        ),
        FunctionTool.from_defaults(
            fn=audit, name="wcp_get_audit_chain",
            description="Fetch the audit chain for a task_id.",
            async_fn=audit,
        ),
    ]
