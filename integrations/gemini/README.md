# WCP tools for the Gemini API

WCP capabilities as Gemini function declarations.

**Worked-example domains:** logistics, field-research.

## Install

```bash
pip install google-generativeai wcp-sdk
```

Use `WCP_FUNCTION_DECLARATIONS` in `tools=[{"function_declarations": WCP_FUNCTION_DECLARATIONS}]` and route any returned `function_call` through `dispatch_function_call`.
