# Worker Context Protocol Project Charter

**Proposed Linux Foundation Projects LLC charter for the Worker Context Protocol (WCP) project.**

Derived from `CHARTER.md`, `TSC_BYLAWS.md`, `RFC_PROCESS.md`, `NON_COERCION_COMMITMENT.md`, and `TRADEMARK_POLICY.md` in the repository root, reshaped to LF Projects LLC conventions. Substantive content is preserved.

## 1. Mission

The Worker Context Protocol (WCP) project develops, maintains, and stewards an open protocol that coordinates AI agents and physical-world workers across institutional and industrial domains, under a permissive open-source license, with vendor-neutral governance.

## 2. Scope

WCP defines:

- A JSON-RPC-over-WebSocket protocol with a typed object model (CapabilityDescriptor, TaskDescriptor, AttestationEvidence)
- A `did:wcp` identity method built on W3C DID Core
- A hash-linked audit chain with reproducible verification semantics
- A two-phase escrow settlement primitive with split-party payouts
- A federation layer that allows independent coordinators to peer
- A conformance suite with three levels (protocol surface, attestation, federation)
- Reference implementations in Python, TypeScript, Rust, and Go
- An RFC process for ongoing evolution

Out of scope:

- Operator-specific business logic
- Specific escrow provider integrations beyond the reference implementation
- Specific worker hardware integrations beyond the reference ROS 2 plugin
- Marketplaces or applications built on WCP

## 3. Governance

### 3.1 Technical Steering Committee

The Technical Steering Committee (TSC) is the primary technical decision-making body. Composition, seating, and bylaws are documented in `TSC_BYLAWS.md` (which becomes a project document under LF stewardship). Briefly:

- TSC members are seated for 24-month renewable terms.
- Quorum is a simple majority of seated members.
- Decisions on RFC acceptance are by 2/3 supermajority of voting members present at quorum.
- The TSC chair is elected annually by majority vote of seated members.
- Conflict-of-interest rules apply per `TSC_BYLAWS.md`.

### 3.2 RFC process

All substantive protocol changes proceed via the RFC process documented in `RFC_PROCESS.md`. Briefly:

- RFCs are drafted in `rfcs/NNNN-short-title.md` per the template in `rfcs/0000-template.md`.
- RFC status progresses: open -> accepted (or rejected, deferred, superseded).
- Accepted RFCs that propose normative spec changes are integrated into the next minor version per `rfcs/0017-semver-policy.md`.
- The TSC has 2/3 supermajority approval authority over RFC acceptance.

### 3.3 Trademark

"Worker Context Protocol" and "WCP" are trademarks. Under LF stewardship, trademark management transfers to the LF Trademark Program. Pre-LF-acceptance, the donating organization commits to non-enforcement per `TRADEMARK_POLICY.md`.

### 3.4 Non-coercion commitment

`NON_COERCION_COMMITMENT.md` binds operators using WCP to a 5x maximum ratio between WCP and non-WCP integration time for any service they operate. The commitment is a covenant on operators, not a license condition; LF stewardship continues to host the text and document compliance.

## 4. Membership and contribution

### 4.1 Contributors

Any individual or organization may contribute under the project's Apache 2.0 license. Contributions are governed by `CONTRIBUTING.md` (Developer Certificate of Origin; no CLA).

### 4.2 Member organizations (post-LF acceptance)

LF Projects' standard membership tiers apply. Initial memberships are at the donating organization's option; the donating organization commits to a 12-month minimum membership commitment to ensure operational continuity.

### 4.3 Code of Conduct

Contributor Covenant 2.1, per `CODE_OF_CONDUCT.md`.

## 5. Intellectual property

### 5.1 License

Apache 2.0 for all project source code, RFCs, governance documents, examples, and conformance suites. Existing v1.0-rc1, v1.0-rc2, v1.0-rc2.1, and v1.0-rc3 artifacts retain their existing Apache 2.0 license under LF stewardship.

### 5.2 Patent grant

Apache 2.0 includes a patent grant covering implementations under the license. The donating organization makes no additional patent grants beyond Apache 2.0 at this time; future patent grants (if any) would proceed via standard LF Projects mechanisms.

### 5.3 Independent implementations

Independent implementations of the WCP spec (those not derived from the reference implementations) are governed by the spec text in `spec/1.0-rc1.md` and successor versions, not by the reference implementation license. Spec text is similarly Apache 2.0.

## 6. Financial

### 6.1 Project funding

LF Projects LLC's standard project-funding mechanisms apply. The project does not require dedicated funding to operate; existing maintainer time covers ongoing work.

### 6.2 Events

Project events (working group meetings, contributor conferences) follow LF Projects' event-hosting framework. WCP-specific events are at the TSC's discretion.

## 7. Trademark commitments under LF stewardship

- The "WCP" mark and "Worker Context Protocol" name transfer to LF Projects LLC on acceptance.
- LF Trademark Program governs use, conformance branding ("WCP-conformant at Level N" per `spec/conformance.md`), and protection.
- Pre-acceptance non-enforcement commitments per `TRADEMARK_POLICY.md` remain in effect; LF Trademark Program supersedes them on transfer.

## 8. Amendments

Charter amendments require:

1. 2/3 supermajority of the TSC
2. Approval from LF Projects LLC per LF Projects' standard amendment process
3. 30-day comment period before vote

## 9. Effective date

This charter is effective on acceptance of the WCP project into LF Projects LLC, which is conditioned on:

- Completion of the donation per `DONATION_COMMITMENT.md`
- Acceptance of the initial TSC roster per `tsc-roster-template.md`
- LF Projects LLC's standard acceptance procedure

---

**Document version:** 0.1 (proposed; matches LF Projects application packet dated [PRINCIPAL TO PROVIDE: submission date])
**Supersedes:** `CHARTER.md` and `TSC_BYLAWS.md` on LF acceptance; those documents remain in the repository as historical record and as the active governance until LF stewardship is effective.
