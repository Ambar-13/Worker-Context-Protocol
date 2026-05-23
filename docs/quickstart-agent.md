# Quickstart: Build and Run a WCP Agent in Five Minutes

Primary illustration: **logistics** (an AI agent dispatching pallet moves to autonomous-robot or human-forklift workers). The same flow applies to disaster-response, scientific-ops, and the other domains.

## Prerequisites

- Python 3.11+
- `pip install wcp wcp-sdk`

## 1. Scaffold

```bash
wcp init agent dock-orchestrator --llm anthropic
cd dock-orchestrator
```

You get:

```
dock-orchestrator/
  agent.py
  requirements.txt
  README.md
```

## 2. Run

```bash
pip install -r requirements.txt
python agent.py
```

The agent connects to `ws://localhost:8000/wcp/ws` by default and posts a stub task. Customize `build_demo_task()` for your domain.

## 3. Drive task construction from an LLM

The integrations under `integrations/` expose four WCP tools to the LLM of your choice:

```python
from anthropic import Anthropic
from wcp_sdk.v2 import Agent
from integrations.anthropic.wcp_tools_anthropic import WCP_TOOLS, dispatch_tool_call

agent = Agent(name="dock-orchestrator", coordinator="ws://localhost:8000/wcp/ws")
client = Anthropic()

async with agent:
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        tools=WCP_TOOLS,
        messages=[{"role": "user", "content": "Move pallet PLT-789 from bay-recv-3 to stage-d-row-14"}],
    )
    for block in msg.content:
        if block.type == "tool_use":
            result = await dispatch_tool_call(agent, block.name, block.input)
            # feed back into next turn
```

The same flow with OpenAI is at `integrations/openai/`; Gemini at `integrations/gemini/`; LangChain at `integrations/langchain/`. Each integration ships worked examples for at least two of the six reference domains.

## 4. Subscribe to capabilities

```python
result = await agent.discover_capabilities(
    filter={"worker_class_filter": ["autonomous_robot", "human"]}
)
```

## 5. Post a task

The TaskDescriptor shape at v0.955 is defined in `spec/0.955.md` Section 4. The minimum required fields:

- `descriptor_type` (transport, scheduled_presence, observe_and_report, or application-defined)
- `descriptor_payload` (opaque application-layer data)
- `attestation_requirement` with `modes`, `threshold`, `M`, `N`, `evidence_schema`

Optional v0.955 fields:

- `max_attestation_attempts` (default 1): bounds the recheck loop on verifier failure.
- `marketplace_ref` (opaque string): correlation key for any settlement layer above WCP (a Stripe PaymentIntent, an SAP work-order, a grant code).

Settlement, escrow, dispute, and refund were removed from the protocol at v0.955. If your deployment needs them, build that layer above WCP and subscribe to the audit chain. `wcp_sdk.session.make_task_descriptor` is an ergonomic helper.

## Next steps

- `docs/llm-integration.md`: detailed worked examples across multiple LLM providers.
- `docs/quickstart-coordinator.md`: run your own coordinator.
- The six reference agents at `examples/agents/` are full end-to-end demonstrations across institutionally distinct domains.
