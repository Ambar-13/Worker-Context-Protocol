"""WCP capabilities as LangChain Tools.

Worked-example domains: scientific-ops, industrial-maintenance.

These tools wrap the WCP SDK so a LangChain agent can post tasks and read
attestation outcomes. The shapes mirror the Anthropic, OpenAI, and Gemini
adapters; the underlying calls are identical.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from wcp_sdk.v2 import Agent

try:
    from langchain_core.tools import BaseTool, Tool  # type: ignore[import-not-found]
except ImportError:  # langchain optional
    BaseTool = object  # type: ignore[assignment,misc]
    Tool = None  # type: ignore[assignment]


def make_wcp_tools(agent: Agent) -> list:
    """Return a list of LangChain Tools bound to the given Agent.

    Tools are built lazily; the caller is responsible for opening
    `async with agent:` before invoking any of them.
    """
    if Tool is None:
        raise ImportError(
            "langchain-core is required: pip install langchain-core"
        )

    async def discover(filter_json: str) -> str:
        f = json.loads(filter_json) if filter_json else {}
        res = await agent.discover_capabilities(filter=f)
        return json.dumps(res)

    async def post(task_args_json: str) -> str:
        args = json.loads(task_args_json)
        res = await _post(agent, args)
        return json.dumps(res)

    async def subscribe(task_id: str) -> str:
        return json.dumps({"subscribed": True, "task_id": task_id})

    async def audit(task_id: str) -> str:
        return json.dumps({"task_id": task_id, "note": "audit-chain endpoint pending"})

    return [
        Tool.from_function(
            name="wcp_discover_capabilities",
            description="Discover WCP workers; arg is a JSON object filter.",
            coroutine=discover,
            func=lambda f: "use the async version",
        ),
        Tool.from_function(
            name="wcp_post_task",
            description=(
                "Post a WCP task. Arg is a JSON object: "
                "{descriptor_type, descriptor_payload, attestation_modes, M, N, "
                "amount, currency, worker_class_filter, time_window_hours}."
            ),
            coroutine=post,
            func=lambda f: "use the async version",
        ),
        Tool.from_function(
            name="wcp_subscribe_attestation",
            description="Subscribe to attestation outcomes for a task_id.",
            coroutine=subscribe,
            func=lambda f: "use the async version",
        ),
        Tool.from_function(
            name="wcp_get_audit_chain",
            description="Fetch the audit chain for a task_id.",
            coroutine=audit,
            func=lambda f: "use the async version",
        ),
    ]


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
