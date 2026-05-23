# WCP tools for AutoGen

Reuses the OpenAI function-calling shape. **Worked-example domains:** logistics, disaster-response.

```bash
pip install pyautogen wcp-sdk
```

Bind via `register_wcp_tools(assistant, agent)` on your `AssistantAgent`.
