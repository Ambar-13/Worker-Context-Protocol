# LLM Integration

How to give Claude, GPT, Gemini, or any function-calling LLM the ability to dispatch physical-world work via WCP. The eight integrations under `integrations/` expose the same four tools to the LLM: discover capabilities, post a task, subscribe to attestation, fetch the audit chain.

## The four canonical tools

Every integration exposes:

1. `wcp_discover_capabilities(filter)`: returns eligible workers per filter (worker class, certifications, location scope).
2. `wcp_post_task(args)`: posts a TaskDescriptor with bonded escrow.
3. `wcp_subscribe_attestation(task_id)`: subscribes to attestation outcomes.
4. `wcp_get_audit_chain(task_id)`: fetches the hash-linked audit chain entries.

The tool surface is identical across providers; only the function-declaration syntax differs.

## Three worked examples (cross-domain)

### 1. Industrial maintenance with Claude

Domain: heavy industry.

```python
from anthropic import Anthropic
from wcp_sdk.v2 import Agent
from integrations.anthropic.wcp_tools_anthropic import WCP_TOOLS, dispatch_tool_call

agent = Agent(name="plant-ops-agent", coordinator="ws://localhost:8000/wcp/ws")
client = Anthropic()

system = (
    "You schedule thermal inspections of cooling-tower bearings. "
    "Eligible workers: human inspectors or autonomous wall-climbing robots. "
    "Attestation: thermal-imagery sensor recording plus supervisor signature."
)

async with agent:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        system=system,
        max_tokens=2048,
        tools=WCP_TOOLS,
        messages=[{"role": "user", "content":
                   "Schedule a thermal inspection of bearing-tower-3-deck-c."}],
    )
    for block in response.content:
        if block.type == "tool_use":
            result = await dispatch_tool_call(agent, block.name, block.input)
            print(result)
```

### 2. Disaster response zone survey with GPT

Domain: emergency services.

```python
import json
from openai import OpenAI
from wcp_sdk.v2 import Agent
from integrations.openai.wcp_tools_openai import WCP_FUNCTIONS, dispatch_function_call

agent = Agent(name="incident-commander", coordinator="ws://localhost:8000/wcp/ws")
client = OpenAI()

async with agent:
    resp = client.chat.completions.create(
        model="gpt-4.1",
        tools=WCP_FUNCTIONS,
        messages=[
            {"role": "system",
             "content": "You are an incident commander. Dispatch zone surveys "
                        "to mixed drone, ground-vehicle, and human teams. "
                        "Require 3-of-5 cross-attested sensor evidence."},
            {"role": "user",
             "content": "Survey zone-c-northeast for structural damage."},
        ],
    )
    msg = resp.choices[0].message
    if msg.tool_calls:
        for call in msg.tool_calls:
            result = await dispatch_function_call(
                agent, call.function.name, json.loads(call.function.arguments)
            )
            print(result)
```

### 3. Field-research sampling with Gemini

Domain: scientific field operations.

```python
import google.generativeai as genai
from wcp_sdk.v2 import Agent
from integrations.gemini.wcp_tools_gemini import WCP_FUNCTION_DECLARATIONS, dispatch_function_call

agent = Agent(name="watershed-monitoring-agent", coordinator="ws://localhost:8000/wcp/ws")

async with agent:
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        tools=[{"function_declarations": WCP_FUNCTION_DECLARATIONS}],
    )
    chat = model.start_chat()
    resp = chat.send_message(
        "Dispatch environmental-sample collection across watershed sites WS-N-001, WS-N-002, WS-N-003."
    )
    for part in resp.parts:
        if part.function_call:
            fc = part.function_call
            result = await dispatch_function_call(agent, fc.name, dict(fc.args))
            print(result)
```

## The two-domain rotation across integrations

Each integration's README names two of the six reference-agent domains for its worked example. The full corpus across the eight integrations cycles through all six domains:

| Integration | Worked-example domains |
|---|---|
| Anthropic | scientific-ops, disaster-response |
| OpenAI | industrial-maintenance, healthcare-logistics |
| Gemini | logistics, field-research |
| LangChain | scientific-ops, industrial-maintenance |
| AutoGen | logistics, disaster-response |
| LlamaIndex | field-research, healthcare-logistics |
| CrewAI | industrial-maintenance, scientific-ops |
| Vercel AI SDK | logistics, disaster-response |

Six visibly different institutional domains demonstrate the worker-class agnosticism is real, not aspirational.

## Production-readiness

For production agent deployments:

- Wrap the tool dispatchers in retry / backoff on the SDK's `is_retryable()` predicate.
- Cache `wcp_discover_capabilities` per `subscription.ttl_seconds`.
- Log every tool call with correlation IDs (the LLM trace and the audit chain should align).
- Respect rate limits per `spec/security-baseline.md` Section 7.

## See also

- `spec/1.0-rc1.md` Section 3 for the full RPC surface.
- `examples/agents/` for six fully runnable demos.
- `integrations/` for the per-framework adapter source.
