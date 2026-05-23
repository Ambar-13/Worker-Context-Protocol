# What WCP Is Not

WCP is a protocol for coordinating AI agents and physical-world workers (humans, autonomous robots, teleoperated systems, hybrid worker classes) across institutional and industrial domains. This document is the canonical list of what WCP is NOT, so that integrators do not deploy it into contexts where a different layer of the stack is the right answer.

If you are about to use WCP for any of the things below, stop and use the named alternative instead. WCP can sit above or beside these systems; it does not replace them.

## 1. WCP is not a real-time control protocol

WCP runs JSON-RPC over WebSocket (TCP). No quality-of-service guarantees. Coordinator-mediated. Sub-millisecond cycle times are unreachable; sub-second is on a good day with a near coordinator and uncongested network.

If you need:
- Closed-loop motor or actuator control (microseconds to milliseconds)
- Hard real-time deadline guarantees
- Deterministic jitter bounds
- Bus arbitration with priorities

Use instead:
- EtherCAT, PROFINET IRT, POWERLINK, Sercos III, TSN (fieldbus and time-sensitive networking)
- DDS (Data Distribution Service) for soft real-time
- ROS 2 actions and topics for intra-robot control loops
- The robot vendor's native SDK for tight motion control

WCP sits ABOVE these systems. The control loop runs inside the worker; WCP delivers the task to the worker and collects the attestation. See `docs/limits/real-time-boundary.md` for the orchestration-vs-control split.

## 2. WCP is not a safety-rated system

WCP is not certified to any functional-safety standard. It does not replace, augment, or substitute for safety-rated systems.

If you need:
- Emergency-stop circuits (Cat 0/1 stop)
- Safety-rated PLC functionality (IEC 61508 SIL 2/3, ISO 13849 PLd/PLe)
- Light curtains, safety scanners, two-hand-control devices
- Safe stop, safely-limited speed, safe operating stop (SS1, SLS, SOS)
- ISO 13482 (personal care robots), ISO 10218 (industrial robots), ISO 22737 (low-speed automated driving)
- IEC 62443 (industrial cybersecurity, distinct from functional safety)
- SOTIF (ISO 21448) coverage

Use instead:
- Vendor safety controllers (Pilz PSS, Siemens F-CPU, Allen-Bradley GuardLogix)
- Safety-rated PLCs and I/O modules
- Functional safety hardware certified to the applicable standard

WCP MAY record safety events in its audit chain as evidence (e.g., "worker reported emergency stop at T=123") but does NOT enforce safety. The authoritative safety layer is the vendor's certified hardware and the operator's risk assessment.

See `docs/limits/safety-system-boundary.md` for the boundary in detail.

## 3. WCP is not a swarm coordination protocol

WCP assumes one task to one worker. The matching engine matches a single posted task to a single eligible worker; the worker claims, executes, attests, and settles.

If you need:
- Multi-agent coordination with shared global state (formation flight, area coverage)
- Auction-based task allocation across a fleet (CBBA, CBAA)
- Consensus on shared world models
- Swarm intelligence (boids-style flocking, distributed pheromone trails)
- Inter-worker direct communication

Use instead:
- Vendor swarm SDKs (PX4 swarm, AnyWalker swarm coordinator)
- Multi-agent reinforcement learning frameworks
- Dedicated swarm protocols (DJI Onboard SDK swarm extensions, Skydio multi-agent)
- ROS 2 multi-machine deployments with ROS DDS

The WCP-compatible workaround is the "swarm coordinator worker" pattern: a single worker on WCP is a swarm coordinator that internally orchestrates a fleet. The agent posts ONE WCP task to the swarm coordinator; the coordinator's internal orchestration is opaque to WCP. See `docs/limits/swarm-boundary.md`.

## 4. WCP is not a file transfer protocol

The audit chain carries evidence references, not payloads above approximately 10 KB. Settlement amounts, signatures, hashes, and small inline metadata fit. Photos, videos, point clouds, large sensor archives do NOT belong in the audit chain.

If you need:
- File transfer up to ~10 KB inline: use evidence_payload directly
- Files above 10 KB: store externally, reference by hash and URL in evidence_payload
- High-bandwidth media streams: use RTSP, WebRTC, or RTMP from worker directly to a media server; WCP records only the stream's metadata

Use instead:
- Operator-side object storage (S3, GCS, Azure Blob, MinIO) for the large payloads
- Content-addressable storage (IPFS, S3 with hash-named keys) when verifiable references matter
- WebRTC for live media; WCP records the session URL and the session hash

The pattern: worker stores the file in operator-side storage, computes a hash, includes `{"file_hash": "sha256:...", "file_url": "s3://..."}` in the evidence_payload. The audit chain has tamper-evidence on the reference; the operator's storage policy governs durability.

## 5. WCP is not a real-time perception or planning protocol

Perception (computer vision, lidar segmentation, SLAM) runs inside the worker. Planning (motion planning, trajectory optimization, task-and-motion planning) runs inside the worker. WCP does not standardize either.

If you need:
- Worker-side perception pipelines: use the worker's native stack (ROS 2 + Nav2, OpenCV, PyTorch, vendor SDKs)
- Planning: vendor SDKs (MoveIt for manipulators, Nav2 for mobile bases, OMPL for sampling-based planning)
- Vision-language-action models: run inside the worker; expose their output via WCP attestation evidence

WCP standardizes the worker's interface to the outside world. What runs inside is application code; WCP cares only about the result (the evidence the worker submits at attestation time).

## 6. WCP is not an authentication standard

WCP consumes W3C DID resolution. Identity establishment, key management lifecycle, and trust anchor governance are upstream.

If you need:
- New identity issuance protocols
- OAuth 2.0 / OIDC integration
- Enterprise SSO (SAML, Active Directory)
- KYC/AML compliance flows
- WebAuthn registration ceremonies

Use instead:
- W3C DID Core (the substrate WCP uses)
- W3C Verifiable Credentials for credential issuance
- WebAuthn for hardware-attested human authentication
- Vendor IAM solutions for enterprise integration

WCP can verify signatures against DIDs and accept evidence anchored in external trust roots (per RFC 0034). Establishing those DIDs and trust roots is operator-side.

## 7. WCP is not an escrow service

WCP defines settlement as a two-phase escrow primitive (hold-on-post, capture-on-attest). The escrow is operator-configured via `escrow_provider`. WCP does NOT operate escrows.

If you need:
- Actual fund custody
- Banking license
- Payment processing
- Dispute mediation (beyond the audit chain's evidence)
- KYC/AML for monetary flows

Use instead:
- Stripe Connect, Square Cash for Business, Wise Business (payment processors)
- Escrow.com, Tazapay (escrow specialists)
- Bank wire transfer with operator-side ledger
- Internal-bookkeeping escrow for non-commercial deployments

WCP records the value flow in the audit chain. The actual money moves through the escrow_provider operator chose. See `docs/patterns/non-commercial-settlement.md` for the non-commercial pattern (internal-bookkeeping escrow).

## 8. WCP is not a substitute for the operator's compliance and governance

WCP gives operators evidence (audit chain, signed attestations). It does NOT replace:

- Regulatory compliance (HIPAA, GDPR, FAA Part 107, FDA QSR, ISO 9001, ISO/IEC 27001)
- Insurance and liability frameworks
- Operator-side dispute resolution policies
- Privacy impact assessments (DPIA under GDPR)
- Auditor relationships

WCP's contribution to compliance is the audit chain: tamper-evident evidence of what happened, when, who attested. The operator's job is the rest.

---

If you find a case that should be on this list and isn't, file an RFC adding it. The architectural limits are part of the spec's clarity.
