# Pattern: Composite Tasks

How to use multiple WCP tasks to express a single piece of work that spans several workers, several worker classes, or several phases. WCP's `tasks/post` is single-task by design (one descriptor, one claim, one settlement); composite work is built by the agent on top.

## When you need this pattern

- The work requires more than one worker class (e.g., a robot picks something up at one location and a human verifies a label on it at the destination).
- The work has natural phases with different attestation requirements per phase (e.g., a survey collects evidence, then a separate inspector evaluates the evidence).
- The work has a fan-out shape (e.g., one coordinating action posts ten parallel sub-tasks, then aggregates).
- The work has a long-lived monitoring phase preceded by a short setup phase (see also `long-lived-monitoring.md`).

## When you do NOT need this pattern

- The work is a single self-contained task with one worker doing the whole thing end-to-end. Use a single `tasks/post`.
- The work is dynamic real-time control with sub-second coordination across actors. WCP is not the right granularity; see `docs/limits/real-time-boundary.md`.
- The work is a swarm (many workers cooperating with shared perception). See `docs/limits/swarm-boundary.md`.

## The three composite shapes

### Shape A: sequential (pipeline)

```
agent posts task A     ->   task A completes   ->   agent posts task B
                                                    referencing task A's outputs
```

The agent (not the coordinator) holds the pipeline state. After task A's `tasks/attest` returns, the agent inspects the evidence and uses it to construct the descriptor_payload for task B.

**Audit chain linkage.** The descriptor for task B SHOULD include an `x-derived-from` field pointing to task A's `task_id` and the relevant audit chain entry hash. This is operator-defined metadata; coordinators preserve it in the audit chain but do not enforce semantics.

**Failure handling.** If task A disputes, the agent decides whether to post task B (probably not) or to handle the dispute through the override authority and either retry or abort the pipeline. WCP does not auto-cancel B based on A's failure.

### Shape B: fan-out + aggregate

```
                          +-- worker 1 claims sub-task 1
agent posts N parallel    +-- worker 2 claims sub-task 2
sub-tasks 1..N            +-- ...
                          +-- worker N claims sub-task N

then: agent (or a designated aggregator worker) posts task N+1
      with x-aggregates-from referencing tasks 1..N
```

The aggregator pattern in particular benefits from a *separate aggregator worker class*: an agent posts the fan-out, then posts a task with a descriptor like `aggregate_evidence` that accepts inputs in its `descriptor_payload` referencing the N sub-task audit chain entries.

**Audit chain linkage.** The aggregator's task descriptor lists the input task_ids; the aggregator's attestation evidence shows it consumed those inputs.

**Settlement.** Each sub-task settles independently. The aggregator task settles independently. If the aggregator finds the inputs incomplete or invalid, it MAY dispute itself (per the override authority).

### Shape C: setup + long-monitor + teardown

```
task A: setup (short, may need a specific worker class with setup capability)
task B: monitor (long-lived; often a different worker class)
task C: teardown (short, often same class as setup)
```

This is the pattern most often used for instrumentation deployments, recurring inspections, and ongoing health monitoring. See `long-lived-monitoring.md` for the details on the monitor phase.

## Audit chain considerations

When the composite spans several tasks, the deployment's forensic story spans multiple audit chain entries. Operators wanting a single "composite story" view typically:

1. Define a `composite_id` UUID and put it in each constituent task's `descriptor_payload` and `attestation_evidence`
2. Add a coordinator-side query that retrieves all entries where `composite_id` matches
3. Optionally publish the composite as a derived audit chain entry (a `composite_completion` event) referencing all the constituent task_ids and their entry hashes

This is operator-side tooling. The protocol provides the primitive (audit chain entries with arbitrary `x-*` metadata); the operator builds the composite view.

## Settlement across composites

Each constituent task is its own escrow contract. If the agent wants the composite to settle "atomically" (all sub-tasks settle or none do), the operator must build that on top:

- Option 1: agent holds total escrow off-WCP, releases per-task escrow only after each task succeeds (sequential).
- Option 2: agent uses a "rollback" task: if any constituent fails, it posts a `composite_rollback` task that triggers refund logic in the escrow provider (requires escrow provider support for partial-refund / unwind).
- Option 3: agent accepts non-atomic settlement; constituent tasks pay out on their own.

WCP itself has no atomic-across-tasks settlement primitive. Cross-coordinator settlement (RFC 0032 preview) addresses cross-coordinator value flow, NOT cross-task atomicity.

## Override authority in composites

Each constituent task names its own override authority. The override authority for the composite as a whole is whichever authority the agent chooses; common choices:

- Same authority for all constituents (simplest; one human or one body adjudicates all disputes)
- Different authority per phase (e.g., setup uses a technical override, the long-monitor uses a regulatory override)

When two constituents in the composite name different override authorities and both dispute simultaneously, the agent's runbook handles arbitration; WCP does not.

## Worked example: rooftop solar inspection

A composite that uses all three shapes:

1. **Task A (setup, sequential):** A human pre-flight checker visits the site, verifies the airspace authorization is in hand, photographs the access path. Worker class: `human`. Attestation: signed checklist + photo manifest.
2. **Task B (work, fan-out):** Once A completes, the agent posts 4 parallel tasks, one per quadrant of the rooftop, each a `aerial_inspection` task. Worker class: `autonomous_robot` (MAVLink drone, see `examples/adapters/mavlink-drone/`). Attestation: `geo_track` + `image_capture_manifest`.
3. **Task C (verification, aggregate):** Once all four B-tasks complete, the agent posts an `aggregate_inspection_report` task to a human inspector. Worker class: `human`. The inspector reviews the captured imagery and produces a written assessment. Attestation: signed PDF inspection report.

Each task has its own escrow. The agent's pipeline logic is responsible for not advancing if a previous step fails. The composite_id ties the audit chain together.

## See also

- `docs/limits/swarm-boundary.md` for when *not* to use this pattern (use swarm-coordinator-worker instead)
- `docs/patterns/long-lived-monitoring.md` for the monitor-phase details
- `rfcs/0006-rpc-tasks-post.md` for task post semantics
- `rfcs/0009-rpc-tasks-attest.md` for attestation semantics that flow into the audit chain
