# {{NAME}}

WCP agent scaffold. LLM provider: `{{LLM}}`.

## What this agent does

Posts a `scheduled_presence` task to a WCP coordinator, attaches a stub bond
reference (operators wire real escrow providers via `escrow_provider`), and
awaits attestation. Replace the body of `build_demo_task` and add LLM-driven
task construction.

## Run

```bash
pip install -r requirements.txt
python agent.py
```

## Next steps

- Wire your LLM (`{{LLM}}`) into the task-building loop. See
  `docs/llm-integration.md` and `integrations/{{LLM}}/` for tool definitions
  in the canonical Anthropic / OpenAI / Gemini formats.
- Set `WCP_COORDINATOR` env var or edit the constant in `agent.py` to point
  at a remote coordinator.
- For richer subscriptions, replace the `post_task` call with `agent.run()`
  and add `@agent.on_capability(filter=...)` handlers.
