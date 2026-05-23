# WCP tools for the Vercel AI SDK

**Worked-example domains:** logistics, disaster-response.

```bash
npm install ai zod @wcp/sdk
```

Use `makeWcpTools(agent, tool)` from `wcp-tools-vercel-ai.ts`, passing the Vercel AI SDK's `tool` helper and a `WcpAgentBinding` implementation backed by `@wcp/sdk`'s Agent class.
