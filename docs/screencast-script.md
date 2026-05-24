# Five-Minute Screencast Script

A storyboard for the README hero demo.

## Setup before recording

- Terminal with large readable font, dark background
- `pip` cache primed (`pip install wcp wcp-sdk` already once on the recording machine)
- Clean working directory
- Browser tab pre-opened to `http://localhost:8765` (the inspector)
- Audio levels checked

## Beats (target: 5 minutes total)

### 00:00 - 00:20 Cold open
A single sentence on screen: "WCP coordinates AI agents and physical-world workers, across institutional and industrial domains. Same protocol for humans, robots, and hybrid teams."
Cut to terminal.

### 00:20 - 00:45 Install
`pip install wcp wcp-sdk`
`wcp doctor` (shows all required packages green)

### 00:45 - 01:30 Scaffold
`wcp init worker thermal-inspector --class hybrid --domain industrial`
Show the four files that drop out.
Open `worker.py` briefly: highlight `@worker.capability`, `@worker.handle("observe_and_report")`, `@worker.attest(AttestationMode.SENSOR_WITNESS)`.

### 01:30 - 02:45 First task
Terminal 1: `wcp dev` (the coordinator boots; the worker connects)
Terminal 2: `cd examples/agents/industrial-maintenance && python agent.py`
Browser: open `http://localhost:8765`, the inspector now shows the coordinator's audit chain tail with the new task.

### 02:45 - 03:30 Seven domains
Cut to a screen displaying the seven reference agents (table from the README).
Point at each: "Same ten RPCs. Different descriptor payloads. The verifier never branches on worker class."

### 03:30 - 04:15 LLM integration
Show `docs/llm-integration.md` opened to the Anthropic example.
Run the example script: `python examples/agents/industrial-maintenance/agent.py` with the `claude-sonnet-4-5` model in the loop posting a task.

### 04:15 - 04:45 Conformance
`wcp test --conformance --level 1 --target wss://localhost:8000/wcp/ws`
Show the report summary.

### 04:45 - 05:00 Close
"This is pre-v1.0. v1.0 final requires adoption validation. Try it. File RFCs. Federate."
GitHub URL on screen.

## Post-production

- Title: "Worker Context Protocol: 5-minute walk-through"
- Description includes spec link, RFC pointers, donation commitment.
- Subtitles in English; community translations land per RFC 0030.
