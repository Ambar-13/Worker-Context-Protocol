# WCP tools for CrewAI

**Worked-example domains:** industrial-maintenance, scientific-ops.

```bash
pip install crewai crewai-tools wcp-sdk
```

`make_wcp_tools(agent)` returns four CrewAI tool functions ready to plug into a Crew member's `tools=[...]` list.
