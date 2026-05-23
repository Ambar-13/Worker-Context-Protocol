# delivery_robot_dispatcher: the robot-as-agent reference deployment

Reference implementation of the robot-as-agent pattern. An autonomous mobile robot inside a manufacturing facility claims a `transport` task, completes the move, and from inside its own execute loop posts a follow-up `place_on_shelf` task to a stationary manipulator. The wire protocol is unchanged from `wcp/0.2`; the new piece is that the AMR's onboard controller holds an agent credential (`agent_class: embodied_agent`) and uses the `continuation_of` block to link the two tasks in the audit chain.

## What this deployment shows

- An autonomous robot acting as a WCP agent.
- A typed `continuation_of` block linking two tasks across the audit chain.
- A different worker class (`semi_autonomous` stationary manipulator) claiming the follow-up posted by the autonomous-robot AMR.
- All of the above through the existing nine RPCs. No protocol surface change.

## What this deployment is NOT

- Not peer-to-peer. The AMR does not call the manipulator directly. Both go through the coordinator.
- Not joint execution. The two tasks are sequential; the transport settles before the place follow-up is claimed.
- Not swarm coordination. One task to one worker, twice.
- Not real-time coordination during execution. The AMR runs its execute loop; on attestation, it posts a follow-up. Latency is the standard `tasks/post -> tasks/claim` matching latency.

## Files

- `agent.py` — the upstream planner agent that posts the initial transport task.
- `worker.py` — the AMR worker. Its `tasks/execute` handler invokes a `RobotAgent` and posts the place-on-shelf follow-up via `continuation_of`.
- `manipulator_worker.py` — the stationary manipulator worker that claims the follow-up.
- `run.sh` — brings up both workers and the planner agent against a local coordinator.

## Run

```
# Start a local coordinator if you do not have one already:
# python -m uvicorn wcp_dev_runtime.coordinator_dev_app:app --port 8000 &

cd examples/agents/delivery-robot-dispatcher
./run.sh
```

Expected output (compressed):

```
[planner] posted transport task_id=... (1 eligible workers)
[amr] moving component component-bb-1042 from staging-bay-2 to workstation-7
[amr-onboard-agent] posted place_on_shelf continuation; task_id=... continuation_of=...
[manipulator] placing component component-bb-1042 on shelf at workstation-7; continuation_of=...
[planner] AMR worker will post a place_on_shelf follow-up via continuation_of after the transport attests; watch the coordinator's audit chain for the linked entries.
```

End-to-end in under sixty seconds on a developer laptop.

## Architectural notes

- The AMR's onboard `RobotAgent` is a separate DID from the AMR worker's own DID. The worker DID has reputation for completing transports; the agent DID has reputation for posting clean continuations.
- `agent_class = "embodied_agent"` is preserved through the audit chain entry for the posted follow-up task. Operators may filter or surface this in monitoring.
- The manipulator reads `continuation_of.required_evidence_kinds` for its runbook (deciding whether the AMR's prior attestation is sufficient context to claim). The verifier does not enforce this check; it is operator policy.

## See also

- `spec/0.95.md` for the spec.
- `docs/patterns/robot-as-agent.md` for the pattern walk-through and Mermaid diagram.
- `rfcs/0002-subcontracting-v0.2.md` for the rejected worker-layer subcontracting design that the agent-layer continuation pattern supersedes.
