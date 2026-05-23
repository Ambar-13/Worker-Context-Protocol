"""WCP tools for the AutoGen framework.

Worked-example domains: logistics, disaster-response.

The Microsoft AutoGen API surface evolves quickly; this adapter targets
the AssistantAgent tool registration shape used as of 2026-Q2. Adjust
the registration call if AutoGen's API differs in your version.
"""
from __future__ import annotations

from typing import Any

from wcp_sdk.v2 import Agent

from integrations.openai.wcp_tools_openai import (  # type: ignore[import-not-found]
    WCP_FUNCTIONS,
    dispatch_function_call,
)


def register_wcp_tools(assistant: Any, agent: Agent) -> None:
    """Register WCP tools onto an AutoGen AssistantAgent.

    AutoGen's tool registration accepts the OpenAI function-calling shape;
    we reuse `WCP_FUNCTIONS` and bind the dispatcher to `agent`.
    """
    for fn_def in WCP_FUNCTIONS:
        fn_name = fn_def["function"]["name"]

        async def tool_impl(_n: str = fn_name, **kwargs: Any) -> Any:
            return await dispatch_function_call(agent, _n, kwargs)

        if hasattr(assistant, "register_for_llm"):
            assistant.register_for_llm(
                name=fn_name, description=fn_def["function"]["description"]
            )(tool_impl)
        if hasattr(assistant, "register_for_execution"):
            assistant.register_for_execution(name=fn_name)(tool_impl)
