# Linux Foundation Projects LLC Application: Worker Context Protocol

**Submission target:** LF Projects LLC (lfprojects.org)
**Project name:** Worker Context Protocol (WCP)
**Project shortname:** wcp
**Submission date:** [PRINCIPAL TO PROVIDE: submission date]

## 1. Project identification

- **Project name:** Worker Context Protocol
- **Project shortname:** wcp
- **Primary repository:** https://github.com/Ambar-13/Worker-Context-Protocol
- **Project website (if any):** [PRINCIPAL TO PROVIDE: website URL or "TBD; repository README is the front door"]
- **License:** Apache 2.0 (existing); will remain Apache 2.0 under LF stewardship

## 2. Project description (per LF Projects LLC application template)

WCP is an open protocol that coordinates AI agents and physical-world workers across institutional and industrial domains. Human technicians, autonomous robots, teleoperated systems, and hybrid worker classes share one RPC surface. The matching engine and the attestation verifier discriminate by structural properties (capabilities, evidence kinds), not by worker class.

WCP is structured as a JSON-RPC-over-WebSocket protocol with a typed object model (CapabilityDescriptor, TaskDescriptor, AttestationEvidence), a `did:wcp` identity method built on W3C DID Core, a hash-linked audit chain, a two-phase escrow settlement primitive, and a federation layer that allows independent coordinators to peer.

Same algorithmic lever as the Model Context Protocol (MCP) (informational and algorithmic: in-band capability discovery plus a typed call contract), applied to physical workers rather than software tools. The primitives MCP does not need, because tools cannot fail in physically irreversible ways, are first-class in WCP: typed attestation, supervision handoff, two-phase settlement, partial-completion abort.

## 3. Why LF Projects?

- WCP is committed to open governance under a neutral steward; the DONATION_COMMITMENT.md document at the repository root binds the donating organization to donate before v1.0 final.
- LF Projects LLC's charter conversion process is well-trodden; the existing CHARTER.md and TSC_BYLAWS.md map cleanly to LF conventions with minor reshaping (see proposed-charter.md).
- WCP serves multiple institutional and industrial domains (industrial robotics, scientific operations, healthcare logistics, emergency response, logistics, public infrastructure, disaster response, research field operations, manufacturing dispatch, smart cities, construction, maritime, space). LF Projects' multi-domain neutrality fits.
- Adjacent LF projects (CNCF, Sigstore, OpenSSF, LF AI & Data, LF Edge) define analogous patterns at adjacent layers. WCP fits the LF ecosystem.

## 4. Governance model

The current governance documents in the repository root (GOVERNANCE.md, CHARTER.md, RFC_PROCESS.md, TSC_BYLAWS.md, NON_COERCION_COMMITMENT.md, TRADEMARK_POLICY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, SECURITY.md, DONATION_COMMITMENT.md) describe:

- A Technical Steering Committee (TSC) with seats and bylaws (TSC_BYLAWS.md)
- An RFC process (RFC_PROCESS.md) with 33+ RFCs already drafted or accepted
- Trademark policy with a non-enforcement commitment pre-v1.0 (TRADEMARK_POLICY.md)
- A 5x non-coercion ratio commitment for marketplace operators using WCP (NON_COERCION_COMMITMENT.md)
- Standard CoC (Contributor Covenant 2.1) and Apache 2.0 contribution flow

The proposed LF-format charter (proposed-charter.md) reshapes these documents into LF conventions while preserving substantive content.

## 5. Initial Technical Steering Committee

The TSC roster at donation time is documented in `tsc-roster-template.md`. The roster is filled in by the donating organization; the seating bylaws (TSC_BYLAWS.md) govern subsequent additions and removals.

- [PRINCIPAL TO PROVIDE: name and role of each initial TSC member]

## 6. Project assets to be donated

- The `wcp-spec` repository at https://github.com/Ambar-13/Worker-Context-Protocol, including all commits, tags, branches, RFCs, reference implementations, conformance suites, governance documents, paper drafts, and examples.
- The "Worker Context Protocol" and "WCP" trademarks (currently with non-enforcement commitment per TRADEMARK_POLICY.md; transferred to LF Projects on acceptance).
- The `wcp-spec` GitHub organization (or equivalent post-donation).
- The donating-organization-side maintainer accounts; replaced by LF-managed accounts on acceptance.

## 7. Donating organization

- **Legal entity:** [PRINCIPAL TO PROVIDE: donating organization legal name]
- **Authorized signer:** [PRINCIPAL TO PROVIDE: signer name]
- **Authorized signer title:** [PRINCIPAL TO PROVIDE: signer title]
- **Authorized signer email:** [PRINCIPAL TO PROVIDE: signer email]
- **Donation effective date:** [PRINCIPAL TO PROVIDE: target date]

The donating organization commits to:

- Transfer of trademark rights to LF Projects LLC on acceptance.
- No exercise of veto, retention of board seats, or other reserved governance powers beyond standard TSC participation.
- Engineering and maintenance contribution during a defined transition period (proposed: 12 months from acceptance) to ensure operational continuity.
- Compliance with the DONATION_COMMITMENT.md text.

## 8. Community evidence

At submission time, the following community-of-record indicators apply:

- [PRINCIPAL TO PROVIDE: actual GitHub repository star count, fork count, contributor count at submission time]
- [PRINCIPAL TO PROVIDE: list of independent implementations or adopters, if any, with their consent to be named]
- Conformance suite at `conformance/` with Level 1, 2, and 3 test bundles; the suite is the canonical determinant of "WCP-conformant" status.
- 34+ RFCs covering the protocol surface, federation, attestation, identity, settlement, trust classes, and connectivity profiles.
- v1.0-rc1 paper draft (`paper/chi-2027-draft.md`) targeting CHI 2027 (deadline 2026-09-10 AoE; verified).

## 9. Roadmap

Near-term (v1.0 final, 12-24 months post-donation):

- At least 3 independent implementations passing conformance Level 2
- At least 1 implementation passing Level 3 (federation)
- At least 1 external paper accepted at a major venue (CHI, ICRA, IROS, CoRL, RSS, T-RO, CSCW)
- LF stewardship effective

Mid-term (v1.1, 12-18 months post-acceptance):

- RFC 0029 (WCP-Lite for intermittent connectivity)
- RFC 0031 (Multibase identifier migration)
- RFC 0032 (Cross-coordinator settlement clearing)
- RFC 0033 (Attestation key trust classes)
- RFC 0034 (External trust-root signed evidence)

Long-term (v2.0, 3-5 years post-acceptance):

- Post-quantum cryptography migration
- Mandatory multibase identifiers (legacy raw-base58 deprecation)
- Working group adoption at IETF if WG forms

## 10. License confirmation

Apache 2.0 throughout. No CLA required (Developer Certificate of Origin per CONTRIBUTING.md). No exotic licensing terms.

## 11. Sponsorship tier

[PRINCIPAL TO PROVIDE: requested LF Projects tier (Standard, Sandbox, Incubating, Graduated, etc.) per current LF Projects LLC tiering]

## 12. Contacts

- **Donating organization contact:** [PRINCIPAL TO PROVIDE: name, email]
- **Initial TSC chair:** [PRINCIPAL TO PROVIDE: name, email]
- **Security contact:** see `SECURITY.md`
- **General inquiries:** see repository issues

---

**Signed:**

`[PRINCIPAL TO PROVIDE: signer name]`
`[PRINCIPAL TO PROVIDE: signer title]`
`[PRINCIPAL TO PROVIDE: signer organization]`
`[PRINCIPAL TO PROVIDE: signature date]`
