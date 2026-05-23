# Pattern: Long-Lived Monitoring Tasks

How to model work that runs for hours, days, or longer (continuous inspection, weather observation, persistent sensor coverage, etc.) inside a protocol designed around discrete tasks with one claim and one attestation cycle.

## The mismatch and the resolution

WCP's core model: a task is `posted -> claimed -> executing -> attested -> settled`. The state machine assumes finite duration, finite attestation, and a settlement event that closes the task. A long-lived monitor (say, a 30-day weather watch) does not fit cleanly.

The resolution: **a long monitor is a sequence of short tasks, posted on a schedule, each with its own attestation cycle.** The agent's runbook defines the cadence and the rollover behavior; WCP provides the per-segment primitives.

This is not a workaround; it is the design. Long monitors fit better as scheduled re-posts than as one infinite task, because:

- Per-segment attestation gives operators a per-segment audit chain entry, which is what regulators usually ask for.
- Worker rotation is natural: the same worker may claim every segment, or different workers may claim different segments.
- Settlement happens per segment, which matches how monitoring contracts price in practice (per day, per week, per N samples).
- Faults in one segment do not blow up the whole monitor; the failed segment disputes and the next segment can still be claimed.

## Recommended segment lengths

| Monitor duration | Segment length |
|---|---|
| Hours | 5-15 minutes |
| Days | 1-6 hours |
| Weeks | 12-24 hours |
| Months | 1-7 days |
| Quarters or longer | 1-2 weeks |

These are reasoned defaults, not a normative requirement. The right segment is the one whose attestation cycle the operator can reliably support and whose settlement cadence matches the deployment's invoicing.

## Posting cadence: agent-side scheduling

The agent (not the coordinator) holds the scheduling state. A long-monitor agent typically runs as a small daemon that:

1. Holds the monitor's start time, end time, segment length, and worker class
2. Posts segment N when segment N-1 attests (or, in fixed-cadence mode, posts at the scheduled wallclock time regardless of segment N-1's state)
3. Records the segment_index in each task's `descriptor_payload` and the parent monitor's ID in `x-monitor-id`
4. Watches for disputes; the runbook says whether to repost the same segment, advance, or pause the monitor

A reference monitor-agent skeleton:

```python
@dataclass
class MonitorAgent:
    coordinator: Agent
    monitor_id: str
    start: datetime
    end: datetime
    segment_seconds: int
    descriptor_template: dict

    async def run(self):
        seg = 0
        cur = self.start
        while cur < self.end:
            task = self._build_segment(seg, cur, cur + timedelta(seconds=self.segment_seconds))
            res = await self.coordinator.post_task(task, ...)
            await self._await_segment_close(res["task_id"])
            seg += 1
            cur += timedelta(seconds=self.segment_seconds)

    def _build_segment(self, idx, start, end):
        t = dict(self.descriptor_template)
        t["task_id"] = str(uuid.uuid4())
        t["descriptor_payload"] = dict(t.get("descriptor_payload", {}))
        t["descriptor_payload"]["segment_index"] = idx
        t["descriptor_payload"]["segment_start"] = start.isoformat()
        t["descriptor_payload"]["segment_end"] = end.isoformat()
        t["x-monitor-id"] = self.monitor_id
        return t
```

## Worker continuity

Three patterns for the worker side:

1. **Same worker, every segment.** The agent expresses preference via `worker_did_filter` or by claiming first-come-first-served and trusting the eligible-workers ordering. This is the simplest and lowest-overhead approach.

2. **Different workers across segments.** No worker_did_filter; whichever eligible worker claims first wins. Good for resilience (no single point of failure) but the audit chain shows a procession of distinct DIDs.

3. **Primary + warm fallback.** Two-tier worker_class filter: the primary worker class is preferred; a secondary worker class is acceptable as a fallback. If the primary cannot claim within a short window, the secondary takes over. Requires coordinator-side configuration of the fallback semantics.

## Attestation per segment

Each segment produces its own evidence per the segment's attestation_requirement. For a weather monitor:

- Segment payload: raw weather samples for the segment
- Evidence kind: `weather_sample_window` (operator-defined per RFC 0003)
- M-of-N: typically 1-of-1 (the sensor's own readings)
- For high-stakes monitors (insurance, regulatory), 2-of-2: device sensor + third-party reference station

The per-segment audit chain entries form the forensic record for the whole monitor; a query across `x-monitor-id` retrieves them as a group.

## Disputes mid-monitor

A disputed segment does NOT cancel the monitor. The agent's runbook decides:

- **Continue and repost the disputed segment** (most common; the monitor keeps running, the disputed segment goes through dispute resolution in parallel)
- **Pause the monitor** until the dispute resolves (used when continuity of evidence is essential, e.g., a chain-of-custody monitor)
- **Abort the monitor** (used when the dispute reveals a problem that invalidates downstream segments, e.g., the worker's calibration is wrong)

The agent's choice is recorded in the audit chain as an operator-defined event.

## Settlement: per segment vs. roll-up

| Pattern | Trade-off |
|---|---|
| Settle per segment | Workers get paid frequently; refunds are localized to a single segment; treasury overhead scales linearly |
| Roll up settlement weekly/monthly | Lower treasury overhead; refunds become harder (must unwind across many segments); workers wait for payment |

Most production monitors settle per segment. The roll-up pattern is used in deployments where the worker is a fleet operator who runs many monitors concurrently and prefers consolidated invoicing.

## Coordinator policy considerations

Coordinators handling long monitors should:

- Reject ultra-short segments (< 1 minute) by policy; the audit chain churn rate is wasteful
- Enforce a maximum live monitor count per agent to prevent runaway agents
- Surface monitor metadata in the coordinator's monitoring dashboard so operators see the running monitor count and segment cadence

## Worked example: 30-day flood-monitor

A flood-monitor that runs for 30 days using an MQTT-attached sensor fleet:

- Monitor ID: `flood-monitor-2026-06`
- Segment length: 6 hours (120 segments total)
- Worker class: `autonomous_robot` (the MQTT IoT adapter, see `examples/adapters/mqtt-iot/`)
- Evidence kind: `mqtt_sensor_window` (river-level + rainfall + soil saturation samples)
- M-of-N: 1-of-1 (the sensor's own readings; insurance grade would add a third-party witness)
- Settlement: per segment, paid daily to the fleet operator
- Override authority: regional emergency management agency's signing DID

If a segment disputes (sensor offline, evidence rejected), the monitor continues; the disputed segment's dispute resolution proceeds in parallel and its settlement is held.

## See also

- `docs/patterns/composite-tasks.md` for the broader composite pattern
- `rfcs/0029-wcp-lite.md` for intermittent-connectivity workers in monitor roles
- `rfcs/0003-evidence-kinds-registry.md` for evidence kind registration
- `examples/adapters/mqtt-iot/` for an MQTT bridge that's a natural fit for monitor work
