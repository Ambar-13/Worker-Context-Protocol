# WCP LLM Framework Integrations

Each integration exposes WCP coordinator capabilities as tools an LLM-driven agent can call. The structural move is identical across providers: discover capabilities, post a task, subscribe to attestation, settle.

## Coverage

| Integration | Path | Tool format | Worked-example domains |
|---|---|---|---|
| Anthropic | `anthropic/` | tool_use blocks | scientific-ops, disaster-response |
| OpenAI | `openai/` | function calling | industrial-maintenance, healthcare-logistics |
| Gemini | `gemini/` | function declarations | logistics, field-research |
| LangChain | `langchain/` | LangChain Tool | scientific-ops, industrial-maintenance |
| AutoGen | `autogen/` | AssistantAgent tool | logistics, disaster-response |
| LlamaIndex | `llamaindex/` | FunctionTool | field-research, healthcare-logistics |
| CrewAI | `crewai/` | tool decorator | industrial-maintenance, scientific-ops |
| Vercel AI SDK | `typescript-vercel-ai/` | TS tool definition | logistics, disaster-response |

The two-domain rotation per integration is intentional: the full integration corpus collectively demonstrates all six reference domains, none of them consumer services.

## Shape of every integration

All eight expose the same four tools to the LLM:

1. `wcp_discover_capabilities(filter)`: returns a list of eligible workers.
2. `wcp_post_task(task)`: posts a TaskDescriptor; returns task_id.
3. `wcp_subscribe_attestation(task_id)`: streams attestation outcomes.
4. `wcp_get_audit_chain(task_id)`: returns the hash-linked audit trail.

The integrations differ only in the surrounding tool-definition syntax of each framework.

## Vendor neutrality

WCP does not endorse any specific LLM provider. The eight integrations are listed alphabetically by framework name; the order does not imply ranking. Integrations call the WCP coordinator's JSON-RPC surface and do not depend on any operator-specific deployment.
