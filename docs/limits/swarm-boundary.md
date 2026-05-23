# The Swarm Boundary

WCP assumes one task to one worker. The matching engine pairs a single posted task with a single eligible worker; the worker claims, executes, attests, settles. This document explains the implications, the workaround for swarm-coordinated work, and what v1.2+ may add.

## The 1-task-to-1-worker assumption

A WCP task descriptor has one `task_id`. The matching engine returns a set of eligible workers; exactly one claims via `tasks/claim`. Subsequent state transitions (execute, attest, settle) are scoped to that one `claim_id`.

This is intentional. It keeps the attestation semantics simple: one signer per claim, one settlement payout per claim. It keeps the audit chain linear: one hash-linked sequence per claim, not a tree.

The cost of this simplicity is that swarm-coordinated work (formation flight, area coverage by multiple drones, distributed manipulation, multi-robot search-and-rescue) does not map directly onto WCP's matching primitive.

## Why this is intentional and not a bug

Swarm coordination protocols have their own design constraints that WCP does not satisfy:

- **Shared global state** (positions, intentions, area-of-interest progress). WCP has no notion of inter-worker state-sharing.
- **Inter-worker direct communication.** WCP routes everything through the coordinator. Adding peer-to-peer messaging would push WCP into a different design space.
- **Auction-based task allocation** (CBBA, CBAA, sequential single-item auctions). The auction itself is the protocol; WCP just delivers the resulting assignments.
- **Real-time consensus.** WCP's outer loop is seconds-to-hours. Swarm consensus often needs sub-second.

A protocol that did all of these would be a much larger, more complex protocol. WCP picks a smaller scope deliberately. See `docs/limits/wcp-is-not.md` Section 3.

## The swarm-coordinator-worker pattern

The standard workaround: introduce a worker on WCP whose internal implementation IS the swarm coordinator.

```
+-----------------+
|                 |
|     Agent       |
|                 |
+--------+--------+
         |
         | tasks/post (one task)
         |
+--------v--------+
|                 |
|  WCP            |
|  Coordinator    |
|                 |
+--------+--------+
         |
         | tasks/claim (one claim)
         |
+--------v---------------------+
|                              |
|  Swarm Coordinator Worker    |
|  (single WCP worker DID)     |
|                              |
|  Internally orchestrates:    |
|                              |
|     +-----+  +-----+  +----+ |
|     |Bot 1|  |Bot 2|  | ...| |
|     +-----+  +-----+  +----+ |
|                              |
+------------------------------+
```

To the WCP coordinator, the swarm coordinator worker is a single worker with a single DID. The agent posts one task. The worker claims, executes (internally distributing work across the fleet), attests with aggregated evidence, and settles.

The internal orchestration is opaque to WCP. The swarm coordinator worker is responsible for:

- Decomposing the WCP task into per-fleet-member assignments
- Communicating with fleet members (typically via a non-WCP protocol; ROS DDS, MAVLink swarm, vendor proprietary)
- Aggregating evidence from fleet members into a single WCP attestation
- Handling fleet-member failures internally (re-allocation, abort)
- Reporting completion or failure to WCP

## When the pattern works

The swarm-coordinator-worker pattern is the right fit when:

- The agent treats the swarm as a single capability ("survey this 1 km² area"), not as N individual workers.
- The swarm has a clear coordinator (a designated lead drone, a ground control station, a dedicated coordinator service).
- The fleet's internal communication is not WCP. Examples: PX4 swarm coordinated via custom MAVLink stream, ANYbotics fleet via ANYbotics fleet manager, Skydio multi-drone via Skydio cloud.
- The audit chain only needs the aggregate result, not per-member granularity.

## When the pattern does not work

The swarm-coordinator-worker pattern is the wrong fit when:

- The agent needs per-member visibility, control, or settlement. A logistics agent that wants to pay per drone per package, with per-drone attestation, will find the aggregate evidence insufficient.
- The fleet has no clear coordinator. A peer-to-peer swarm with no designated lead is a poor fit; designate a coordinator or use a different protocol.
- The fleet is dynamic mid-task. Joining and leaving members mid-execution is hard to express through a single WCP claim.
- Different fleet members have different worker classes or trust classes that the agent cares about individually. Tier-1 trust hardware on lead drones plus tier-0 software on follower drones cannot be expressed as a single worker's trust class.

For these cases, the answer is either:

- **A different protocol layer.** WCP is not the right hammer.
- **N parallel WCP tasks.** The agent posts N tasks; each fleet member claims one. The agent's application layer correlates them. This works but loses the swarm-as-unit abstraction.
- **WCP federation.** The fleet's coordinator is its own WCP coordinator; per-member tasks live there; the agent's coordinator federates. See `spec/federation.md` and RFC 0032.

## Worked example: drone area survey

### Pattern: swarm-coordinator-worker

An emergency-response agent posts: `observe_and_report` over a 4 km² damage zone, deliverable: thermal imagery covering 100% of the polygon.

The eligible workers include a drone-swarm-coordinator worker (let's call it `did:wcp:zSwarmCoordRescue42`). This worker is a service that internally controls 8 drones via PX4 swarm extensions.

The swarm-coordinator-worker claims the task. Internally:

- It decomposes the 4 km² polygon into 8 sub-areas (one per drone).
- It dispatches each drone to its sub-area via MAVLink (NOT WCP).
- It collects thermal imagery from each drone.
- It aggregates the imagery into a single deliverable (a mosaic, or 8 file URLs).
- It attests via WCP with `sensor-witness` evidence pointing at the aggregated deliverable, plus a hash of each contributing drone's imagery.

To WCP, this is one worker, one claim, one attestation. The 8 drones do not appear in the audit chain by name.

### Anti-pattern: 8 parallel WCP tasks

The agent posts 8 WCP tasks, each for a sub-area. 8 individual drones claim. Each drone attests separately. The agent's application code correlates them by sub-area.

This works but loses something. The matching engine is not aware that the 8 tasks belong together; if drone 3 fails and its sub-area is unclaimed, the agent must repost. The settlement is 8 separate flows. The aggregate semantics ("coverage completed") is an agent-level invariant, not a protocol-level invariant.

For some use cases this is fine; for others (where coverage completeness is contractual), the swarm-coordinator-worker is cleaner.

## What v1.2+ may add

The 1-task-to-1-worker assumption is a v1.0 design choice. Future versions may relax it. Candidate directions, tracked for v1.2 RFC consideration:

- **Multi-claim tasks.** A task allows N claims; each claim is an independent attestation; aggregate completion is task-level. Settlement splits across N workers per a declared rule.
- **Task hierarchies.** A parent task spawns subtasks; the parent task's attestation depends on subtasks' attestations.
- **Audit chain trees.** The audit chain becomes a Merkle tree instead of a linear hash chain, allowing branching for multi-worker tasks.

These are non-trivial changes. They would alter the verifier semantics, the federation contract, the dispute window math, and the settlement contract. v1.0 deliberately defers. The swarm-coordinator-worker pattern carries today's workload until the v1.2 design is settled.

## See also

- `docs/limits/wcp-is-not.md` Section 3 for the canonical statement
- `docs/patterns/composite-tasks.md` for chained tasks within a single worker's purview
- `docs/limits/real-time-boundary.md` for why WCP cannot serve as a swarm coordination message bus
- `rfcs/0029-wcp-lite.md` for the connectivity profile that some swarm members will have
