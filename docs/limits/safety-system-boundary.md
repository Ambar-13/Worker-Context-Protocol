# The Safety-System Boundary

WCP does NOT replace, augment, or substitute for safety-rated systems. This document is the explicit statement of that boundary, the reasoning, and the practical implications for operators.

## What WCP is not

WCP is not certified to any functional-safety standard. It is not assessed against:

- **IEC 61508** (functional safety of electrical/electronic/programmable systems)
- **ISO 13849** (safety of machinery; Performance Levels PLa-PLe)
- **IEC 62061** (machinery safety; Safety Integrity Levels SIL 1-3)
- **ISO 10218** (industrial robots; safety requirements)
- **ISO 13482** (personal-care robots; safety requirements)
- **ISO 22737** (low-speed automated driving systems; safety)
- **ISO 21448 SOTIF** (Safety Of The Intended Functionality)
- **IEC 62443** (industrial cybersecurity, distinct from functional safety)

WCP is a software protocol. It does not have the architectural redundancy, the deterministic timing guarantees, the diagnostic coverage, or the formal verification required for safety certification. It also does not have the certification-body relationship and the documented hazard analysis required for any operator to claim safety conformance via WCP alone.

## What the safety layer is

The authoritative safety layer in any WCP deployment is the operator's separately certified safety system. For industrial deployments this is typically:

- **Safety-rated PLC** (Pilz PSS, Siemens F-CPU SIMATIC S7-1500F, Allen-Bradley GuardLogix, Mitsubishi MELSEC iQ-F SIL2)
- **Safety I/O modules** (Pilz PSSu, Siemens F-DI/F-DQ, Beckhoff EL69xx)
- **Safety-rated sensors** (light curtains, safety scanners, safety mats, safety edges, e-stops, enabling devices)
- **Safety-rated drives** (with safe stop SS1/SS2, safely-limited speed SLS, safe operating stop SOS)
- **Risk assessment** per ISO 12100, machine-specific hazard analysis, safety manual, validation report

For autonomous mobile robot (AMR) and autonomous guided vehicle (AGV) deployments:

- **Safety-rated lidar** (SICK microScan3, Pilz PSENscan, Hokuyo UAM)
- **Safe motion controllers** certified per ISO 3691-4 (driverless industrial trucks)
- **Emergency stop circuits** with appropriate stop categories

For drone deployments:

- **Geofencing** enforced at the flight controller level (PX4, ArduPilot with geofence breach handling)
- **Return-to-home** and **failsafe behavior** certified per the airframe's type certificate or operator-side risk-based authorization
- **Aviation-authority airspace authorization** (FAA Part 107 waivers, EASA SORA categorization)

For surgical, medical, or care robots:

- **Class II/III medical device** certifications (FDA, CE MDR, MHRA UKCA)
- **IEC 60601-1** electrical safety and IEC 60601-1-2 EMC
- **ISO 80601-2-77** for surgical robotic equipment

## What WCP CAN do for safety

WCP can record safety-relevant events in the audit chain as forensic evidence. Examples:

- The worker emits an event when its safety controller transitions to E-stop. The audit chain records `worker reported e-stop at T=12:34:56`. This does NOT enforce the e-stop (the safety controller already did); it records that the event happened.
- A safety-rated lidar detects a person in the safety zone. The vendor's safety system halts the AMR. The AMR's WCP plugin emits an event noting the safety-zone breach. The audit chain captures the timestamp, the worker, the task that was in progress.
- A task posted with `minimum_trust_class: hardware-attested-tpm2` (RFC 0033) won't be claimed by a worker without an attested key. This is operator-policy enforcement, not functional safety.

These are evidence-collection features. They make incident review faster. They do not prevent unsafe action.

## What WCP CANNOT do for safety

- Replace the safety controller's emergency stop circuit
- Substitute for the safety scanner's protective stop
- Be the only thing preventing an industrial robot from colliding with a human
- Be the only thing preventing a drone from flying into a no-fly zone
- Be the only thing preventing a surgical robot from over-articulating

In all of these cases, a separate, certified, safety-rated system must be in place. WCP sits beside it as the orchestration and evidence layer.

## Practical implications for operators

### Risk assessment

The operator's hazard analysis must NOT depend on WCP for any safety function. WCP can appear as "evidence collection mechanism" in the safety manual; it must not appear as "protective measure" or "safety function" anywhere.

### Documentation

The operator's safety documentation must explicitly note:

- WCP records events but does not enforce safety.
- The authoritative safety layer is (named certified system).
- Failure of WCP coordinator, network partition, or audit chain corruption does NOT introduce a hazard.

If the operator cannot make these statements truthfully, they are using WCP in a context where it does not belong, or they are missing a certified safety layer.

### Audit and inspection

When an auditor reviews the deployment:

- They are reviewing the certified safety system against the applicable standard.
- WCP audit chain entries are admissible evidence of what happened (timestamp, signatures, hashes), useful for incident reconstruction.
- WCP audit chain entries are NOT a substitute for the safety system's own audit trail required by certification.

### Failure modes

If the WCP coordinator is unreachable:

- Worker behavior reverts to its onboard fallback (defined by the worker's own safe-state design)
- Safety system continues to operate independently
- No new tasks are claimed; in-progress tasks continue per the worker's autonomous policy
- The audit chain has a gap until reconnect (WCP-Lite per RFC 0029 mitigates if configured)

If the worker's safety system trips:

- The worker stops or enters safe state per the safety system's design
- The worker emits a WCP event reporting the stop (if connectivity allows)
- WCP records the event; the recovery is handled by the operator's standard safety-system recovery procedure

If a task descriptor demands behavior that the worker's safety system would prevent:

- The worker SHOULD reject the task at claim time
- If accepted but the safety system trips during execution, the task moves to `disputed` via abort-with-safety-event
- The audit chain records the safety event

## The single-sentence summary

WCP records that something happened; the safety system makes sure the right things happen. These are different jobs, performed by different layers, certified to different standards. WCP is the protocol; the safety system is the law.

## See also

- `docs/limits/wcp-is-not.md` for the canonical list of non-uses
- `docs/limits/real-time-boundary.md` for the orchestration-vs-control split
- `docs/limits/failure-modes.md` for the comprehensive failure catalog
- ISO 12100 (general risk assessment for machinery)
- IEC 61508 part 0 (overview of functional safety lifecycle)
