# RFC 0002: Subcontracting (deferred to v0.2)

- Author(s): Rentably (principal)
- Status: deferred; v0.955 supersedes the open question on "settlement split" (settlement is no longer a protocol concern; cross-party value split happens at the settlement layer above WCP). Any future subcontracting design at the protocol layer concerns coordination only.
- Type: standards-track
- Created: 2026-05-23
- Targets: TBD post-v1.0

## Summary

Subcontracting is the case where a worker (human or robot) claims a task and then delegates part of it to another worker. v0.1 forbids subcontracting at the worker layer. This RFC opens as a tracking stub for v0.2 deployment evidence on whether worker-layer delegation is needed.

## Motivation

Hard-case real examples:

- An AMR claims `transport` to deliver a package and hands off to a stationary manipulator at the destination for final shelf placement.
- A senior fire-safety inspector claims `observe_and_report` and assigns one floor to a junior contractor.

Both are expressible at v0.1 as **multiple tasks posted at the agent layer** (one task per stage, one worker per task). The question this RFC tracks: does deployment evidence justify a worker-layer delegate primitive, or does agent-layer composition suffice?

## Design space (sketched, not adopted)

Three options under consideration:

### Option (a): forbid by hard prohibition (v0.1 behavior)

- TaskDescriptor.x-subcontract-allowed default false.
- Coordinator rejects any attempt with `SUBCONTRACT_FORBIDDEN`.

### Option (b): tasks/delegate primitive (rejected for v0.1; under review for v0.2)

A new RPC `tasks/delegate` extending the surface. Requires:

- A `tasks/delegate-accept` companion (delegate signs acceptance).
- A `reputation_attribution` field on the delegation envelope (does the delegate's failure reflect on the claimer?).
- A revised settlement split: does the delegate get paid by the claimer or by the agent?
- Attestation re-rooting: does the original acceptance_attestation bind the delegate, or only the claimer?

Adding tasks/delegate forces at least a tenth and an eleventh method. The primitive shape is therefore wrong at v0.1.

### Option (c): punt with `x-subcontract-allowed` reserved extension (v0.1 carve-out adopted)

- TaskDescriptor reserves the extension field `x-subcontract-allowed`, default `false`.
- Implementations MAY set `true` and define operator-discretionary behavior.
- Behavior under `true` is **not WCP-conformant at v0.1**.
- Coordinators MUST refuse `true` unless explicitly opted in.

## Drawbacks

v0.1's hard prohibition forecloses primitive choices at v0.2 if deployment evidence favors a worker-layer delegate.

## Alternatives

See Option (b) above. Rejected for v0.1 because the primitive shape requires too many new fields and methods.

## Prior art

- BPEL and similar workflow languages handle delegation via process composition at a higher layer.
- Saga pattern in distributed systems: compensating actions across multiple coordinated participants.

## Unresolved questions

These questions are tracked as part of this RFC and will inform a v0.2 decision:

1. Do agents in production prefer multi-task composition or a worker-layer delegate?
2. How should reputation attribute across delegation chains?
3. Does Scenario 12 (teleop-to-autonomous handoff) reveal a structural cousin of subcontracting?
4. How does the settlement split change when delegate is paid by claimer vs by agent?

Evidence will be collected from the Rentably wedge and from external coalition deployments between v0.1 and v0.2.

## Implementation track

v0.1 reference coordinator implements Option (c): rejects `x-subcontract-allowed=true` with `SUBCONTRACT_FORBIDDEN`. v0.2 RFC will revisit.
