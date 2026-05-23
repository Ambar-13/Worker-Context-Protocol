# Operator Guide: Onboarding

**Status:** RECOMMENDED practice; not normative.

This document describes patterns operators have used to onboard workers and to onboard themselves into a federation.

## 1. Worker onboarding

A worker becomes WCP-active when its DID is registered with a coordinator and a CapabilityDescriptor is accepted via `capabilities/list`. The operator-side steps before and after that protocol moment are operator-defined.

### Pattern A: KYC-then-DID

1. Worker registers an account with the operator (email, phone, or single-sign-on).
2. Operator runs KYC: identity document scan, liveness check, address verification, AML screening.
3. Operator's onboarding service generates an Ed25519 keypair on the worker's device (PWA via Web Crypto Subtle; mobile app via Keystore/Secure Enclave; robot via TPM).
4. Operator's onboarding service computes `did:wcp:<base58(pubkey)>` and registers the worker DID in the coordinator's worker table.
5. Worker publishes the first CapabilityDescriptor via `capabilities/list`.

### Pattern B: DID-first then KYC

For pseudonymous worker classes (some robot vendors prefer not to disclose customer-level identity), the worker DID is created first with a low trust class declared in the CapabilityDescriptor (`required.trust_class: "software_keypair_unverified"`). KYC is gated on the first paid task and applied to the principal DID rather than the worker DID.

This pattern preserves cross-class reputation portability for robot workers whose owners change.

### Pattern C: Sponsored onboarding

A trusted sponsor (an established worker with high reputation, or an institutional partner) vouches for a new worker. The sponsor's DID is recorded in the new worker's onboarding audit chain entry. Operators MAY weight matching toward sponsored workers in the first 30 days.

## 2. Operator onboarding (becoming a coordinator)

An operator becomes a WCP coordinator by:

1. Deploying a WCP-conformant coordinator implementation (reference or third-party).
2. Generating an Ed25519 coordinator signing key (HSM-backed in production).
3. Registering the coordinator's `did:wcp` document with a `WcpCoordinator` service endpoint.
4. Running the conformance suite Level 1; publishing the passing report.
5. Optionally federating with peer coordinators per `spec/federation.md`.

The operator publishes:

- Privacy policy (per local jurisdiction)
- Dispute resolution policy (see `dispute-resolution.md`)
- Non-coercion commitment (if claiming "open marketplace")
- Conformance report URL
- Coordinator DID document

## 3. Agent onboarding

An agent (AI-platform-side caller) onboards by:

1. Obtaining a coordinator-issued agent DID.
2. Generating an Ed25519 keypair.
3. Calling `capabilities/subscribe` to discover workers.

For agents serving production traffic, operators typically require a service agreement, rate-limit tier configuration, and an escrow funding mechanism.

## 4. Worker class transitions

A worker who later operates in additional classes (a contractor who supervises robots; a robot whose teleoperated tier is enabled) MUST preserve their DID. The CapabilityDescriptor's `class` field changes; the DID does not. Reputation accrues across class transitions.

## 5. Offboarding

- A worker offboards by publishing a final CapabilityDescriptor with `available_windows: []` (no times available). Reputation is preserved on the DID for reference.
- A coordinator offboards a worker by tombstoning their record per `privacy-architecture.md` if the worker requests data erasure.
- A coordinator that ceases operation SHOULD publish an audit chain export per `federation.md` for federation peers to retain task records.
