# The Orchestration vs Control Boundary

WCP is an orchestration protocol, not a control protocol. This document explains the boundary and gives a worked example.

## The two loops

```
+----------------------------------------------------------+
|                                                          |
|              REAL-TIME INNER LOOP                        |
|              (worker-internal)                           |
|                                                          |
|     - Microseconds to milliseconds                       |
|     - Vendor SDK or fieldbus or ROS 2 actions            |
|     - Deterministic where applicable                     |
|     - Closed-loop sensor-to-actuator                     |
|     - No coordinator in the loop                         |
|     - No network round-trip on the critical path         |
|                                                          |
+----------------------------------------------------------+
                          |
                          | (worker emits state changes,
                          |  receives task assignments)
                          |
+----------------------------------------------------------+
|                                                          |
|              WCP OUTER LOOP                              |
|              (coordinator-mediated)                      |
|                                                          |
|     - Seconds to hours                                   |
|     - JSON-RPC over WebSocket                            |
|     - Task assignment, attestation, settlement           |
|     - Audit chain                                        |
|     - Federation                                         |
|     - Network round-trips OK; jitter tolerated           |
|                                                          |
+----------------------------------------------------------+
```

The inner loop is the worker's business: motor control, balance, vision processing, navigation, manipulation. WCP does not look inside.

The outer loop is the protocol's business: which task does the worker take, what evidence does it submit, who settles, what gets recorded.

## Why the split

Real-time control needs deterministic latency and bounded jitter. JSON-RPC over WebSocket over TCP over the public internet provides neither. A coordinator-mediated control loop with a 30 ms median round-trip and 200 ms p99 cannot close a 1 kHz current loop on a manipulator's joint. The physics of the protocol stack force the split.

The split is also good engineering. Worker-internal loops use the best tool for that domain (ROS 2 actions for ROS-based robots, EtherCAT for industrial automation, vendor SDKs for proprietary platforms). The outer loop is uniform across heterogeneous worker fleets, which is exactly what WCP is for.

## Worked example: quadruped robot

A quadruped robot accepting WCP tasks operates two simultaneous loops:

### Inner loop (400 Hz, worker-internal)

The robot's onboard computer runs balance control, foot placement, terrain estimation, and contact dynamics at 400 Hz. The control stack is the vendor's (e.g., ANYbotics ANYmal, Boston Dynamics Spot, Unitree Go2). Latency budget: 2.5 ms per cycle. Jitter budget: well under 1 ms. The robot's safety controller is also in this loop, with its own deadline.

None of this touches WCP.

### Outer loop (seconds to hours, WCP)

An agent posts a WCP `observe_and_report` task: "walk to GPS coordinates (37.421, -122.083), capture thermal imagery of the substation, return". The robot's WCP plugin receives the task via `tasks/post`, claims it via `tasks/claim`, begins execution. The robot's onboard mission planner (NOT WCP) decomposes the high-level task into a sequence of waypoints and feeds them to the inner loop's navigation stack.

While the robot is walking, the WCP outer loop is mostly quiet:
- Heartbeat every N seconds (per RFC 0029 or v1.0-rc1 default)
- State updates every M seconds (per operator policy)
- Attestation evidence submission once the work is done

The inner loop is hammering through 400 Hz of control updates the whole time. The outer loop sees the robot at the seconds-to-minutes timescale.

### Where they connect

The connection points are exactly two:

1. **Task assignment** (outer to inner): WCP delivers the task descriptor to the worker. The worker's mission planner parses the descriptor's `descriptor_payload` and feeds the inner loop the waypoints/setpoints/objectives.

2. **Attestation evidence** (inner to outer): The inner loop accumulates evidence (GPS track, thermal imagery hash, navigation success/failure). The worker submits this evidence to WCP via `tasks/attest` when the task completes.

That's it. Two crossings per task.

## What if the inner loop is missing?

For pure-software workers (an LLM-driven knowledge worker, a code-review agent), there is no inner control loop. The whole flow is at the outer loop's timescale. WCP works fine; the inner-loop column is just empty.

For purely human workers, the inner loop is the human's own sensorimotor cycle (perception, decision, action). WCP doesn't standardize that. It just delivers the task and collects the evidence.

## What if both loops need to talk more frequently?

This is the symptom that says you are about to misuse WCP. If the worker needs frequent input from outside during execution, the right answer is one of:

- **Increase the worker's autonomy.** The worker should be able to handle the task without per-step external input. The task descriptor declares the constraints; the worker handles execution.
- **Use supervision handoff.** WCP has `tasks/supervise(...)` for graded autonomy. If the worker hits an uncertainty bound, it hands off to a supervisor with a state snapshot. The supervisor takes over (outside WCP's outer loop), then returns control with a fresh state.
- **Break the task into smaller tasks.** A monolithic 30-minute task with constant external check-ins is better as a chain of 1-minute tasks where each task's `attestation_requirement` records the checkpoint. See `docs/patterns/composite-tasks.md`.

The wrong answer is to thread control through WCP. The network does not allow it; the protocol does not promise it.

## How to know which side a feature belongs on

Ask: does this feature need bounded latency?

- **Yes, microseconds or milliseconds**: inner loop. WCP cannot help.
- **Yes, seconds**: outer loop. WCP is fine.
- **No, eventually consistent**: outer loop. WCP is fine.

Ask: does the feature need to record evidence?

- **Yes, tamper-evident**: outer loop (audit chain).
- **No**: either loop; pick by latency.

Ask: does the feature need to coordinate across worker classes (humans + robots)?

- **Yes**: outer loop (this is what WCP is for).
- **No**: probably inner loop; vendor-specific.

## See also

- `docs/limits/wcp-is-not.md` for the canonical list of non-uses
- `docs/limits/safety-system-boundary.md` for the safety-rated systems boundary
- `docs/patterns/composite-tasks.md` for the chained-task pattern
- `spec/1.0-rc1.md` Section 7 for the heartbeat and supervision specifics
