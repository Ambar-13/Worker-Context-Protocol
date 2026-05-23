# WCP tools for LangChain

WCP capabilities as LangChain `Tool` objects.

**Worked-example domains:** scientific-ops, industrial-maintenance.

## Install

```bash
pip install langchain-core wcp-sdk
```

## Use

```python
from wcp_sdk.v2 import Agent
from integrations.langchain.wcp_langchain_tools import make_wcp_tools

agent = Agent(name="lc-agent", coordinator="ws://localhost:8000/wcp/ws")
async with agent:
    tools = make_wcp_tools(agent)
    # pass `tools` to your AgentExecutor or to a tool-calling LLM chain
```

The four tools have the same surface as the Anthropic, OpenAI, and Gemini adapters.
