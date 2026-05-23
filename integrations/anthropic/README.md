# WCP tools for the Anthropic API

Plug WCP capabilities into the Anthropic Messages API tool-use format.

**Worked-example domains:** scientific-ops, disaster-response (further reading: `integrations/openai/` covers industrial-maintenance and healthcare-logistics).

## Install

```bash
pip install anthropic wcp-sdk
```

## Use

```python
from anthropic import Anthropic
from integrations.anthropic.wcp_tools_anthropic import (
    WCP_TOOLS, dispatch_tool_call,
)
from wcp_sdk.v2 import Agent

agent = Agent(name="claude-driven-agent", coordinator="ws://localhost:8000/wcp/ws")
client = Anthropic()

# In your conversation loop:
# 1. Call client.messages.create with tools=WCP_TOOLS.
# 2. Inspect resp.content for tool_use blocks.
# 3. For each, call dispatch_tool_call(agent, block.name, block.input).
# 4. Feed tool_result blocks back in the next turn's messages list.
```

A canonical loop for scientific-ops (calibration scheduling) and disaster-response (zone survey dispatch) lives in `examples.py` (not yet shipped; coming in a future iteration).

## Tools exposed

- `wcp_discover_capabilities(filter)`
- `wcp_post_task(task)`
- `wcp_subscribe_attestation(task_id)`
- `wcp_get_audit_chain(task_id)`
