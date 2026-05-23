# Worker Context Protocol (WCP)

**Current version:** v1.0-rc1 (release candidate; not v1.0 final until adoption validates)
**License:** Apache 2.0
**Schema version:** `wcp/1.0-rc1`

WCP is an open standard for AI agents to hire physical-world workers of any class (human contractor, autonomous robot, teleoperated robot, semi-autonomous system, hybrid) through one worker-agnostic RPC surface.

Same algorithmic lever as the Model Context Protocol (MCP) for software tools (informational and algorithmic: in-band capability discovery plus a typed call contract), applied to physical workers. The primitives MCP does not need, because tools cannot fail in physically irreversible ways, are first-class: **typed attestation, supervision handoff with autonomy grading, two-phase settlement, and partial-completion abort**.

## Front door for the outside reader

You are most likely here because you are evaluating WCP for integration. The shortest path:

1. **Read [spec/1.0-rc1.md](./spec/1.0-rc1.md)** (~30 pages; ASCII state machine first; nine RPCs with full schemas).
2. **Read [spec/d4-verification-1.0-rc1.md](./spec/d4-verification-1.0-rc1.md)** to see that the same nine RPCs handle three task descriptors across two worker classes plus federation cells without modification.
3. **Skim [GOVERNANCE.md](./GOVERNANCE.md)** for donation, non-coercion, charter, RFC process, TSC bylaws, and trademark policy.
4. **Clone, install, run the test suites:**

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pip install -e ./wcp_sdk_python
pip install -e ./conformance/runner-python

pytest wcp_coordinator/tests/           # 44 tests
pytest wcp_sdk_python/tests/            # 15 tests
pytest wcp_worker/test/                 # 8 host-independent tests

# Run the conformance suite Level 1 against the reference coordinator:
# (Start the coordinator first under uvicorn; then:)
# wcp-conformance --target wss://localhost:8000/wcp/ws --level 1
```

## Layout

```
spec/                       # the normative specification (v1.0-rc1)
  1.0-rc1.md                # lead document
  0.1.md                    # v0.1 preserved for reference
  did-method-wcp.md
  threat-model.md
  privacy-architecture.md
  federation.md
  conformance.md
  semver-policy.md
  error-codes.md
  security-baseline.md
  time-synchronization.md
  retry-idempotency.md
  performance-conformance.md
  d4-verification-1.0-rc1.md
  d4-verification.md        # v0.1 preserved
  schemas/                  # JSON Schemas

GOVERNANCE.md, DONATION_COMMITMENT.md, NON_COERCION_COMMITMENT.md,
CHARTER.md, RFC_PROCESS.md, TSC_BYLAWS.md, TRADEMARK_POLICY.md,
CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, CHANGELOG.md

rfcs/                       # 0000 template; 0001-0021 accepted/technical;
                            # 0022-0030 v1.1 open questions

wcp_coordinator/            # FastAPI reference backend (44 tests green)
  attestation_verifier/     # SINGLE POINT of worker-class agnosticism

wcp_worker/                 # ROS 2 Humble plugin (Jazzy CI matrix; 8 tests green)

pwa/wcp/                    # PWA module for the contractor app (906 LOC, vitest)

wcp_sdk_python/             # Python SDK (903 LOC, 15 tests green)

conformance/                # Conformance suite (Level 1, 2, 3 bundles)
  test-suite/               # Language-agnostic test definitions
  runner-python/            # Python runner (wcp-conformance CLI)
  fixtures/                 # Known-good and known-bad payloads

operator-guide/             # 7 RECOMMENDED-practice documents
                            # NOT normative; conformance does not require adoption

paper/                      # CHI 2027 full draft; v0.1 outline preserved;
                            # coalition outreach emails

PLAN.md                     # the consolidated execution plan
```

## The single sentence (preserved from PLAN.md Section 9)

WCP v0.1 is one worker-agnostic RPC surface that does not know whether the worker is human or robot, shipped with one ROS 2 Humble reference plugin under 2000 LOC and one PWA module extending an existing contractor app under 2000 LOC, one FastAPI reference backend wired into a two-phase escrow, a public Apache 2.0 license with a written commitment to donate to a neutral steward at v1.0 final, a non-coercion commitment bounding non-WCP integration time within a 5x ratio, an SDK ergonomics gate of under 8 hours for outside robot engineers and under 2 hours for outside human-side engineers, an adversarial test pass across three descriptors and two worker classes before publication, a coalition of two of three (academic, worker provider, AI-agent platform) committed before broad announcement, and a launch gate of three signed conditional pre-purchase pilots before any robot vendor is asked to ship.

v1.0-rc1 extends that artifact corpus to include the threat model, privacy architecture, federation, conformance suite, semver policy, error taxonomy, security baseline, time synchronization, retry semantics, performance conformance, Python SDK, operator implementation guide, full CHI 2027 paper draft, additional governance documents, and RFCs 0013-0030.

## Vendor neutrality

WCP is a protocol, not a product. The spec is written for ANY implementer. Specific operators, escrow providers, currencies, and jurisdictions appear only in clearly-labeled examples. WCP-conformance is determined by `conformance/`, not by similarity to any reference implementation.

The reference implementations under `wcp_coordinator/`, `wcp_worker/`, and `pwa/wcp/` describe one operator's choices. Other implementations are equally valid and welcome.

## Status

| Artifact | v0.1 | v1.0-rc1 |
|---|---|---|
| Spec | spec/0.1.md (4951 words) | spec/1.0-rc1.md + 10 companion normative docs |
| Governance | 5 files | + CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, TRADEMARK_POLICY, TSC_BYLAWS |
| Coordinator | 44 tests green | (carried forward; v1.0-rc1 final adds rate limiting, OpenTelemetry, federation; pending) |
| ROS 2 plugin | 830 LOC, 8 tests | (carried forward; v1.0-rc1 final adds Isaac scene; pending) |
| PWA | 906 LOC, vitest tests | (carried forward; v1.0-rc1 final adds WCAG 2.2 AA audit; pending) |
| Python SDK | (new) | 903 LOC, 15 tests green |
| TypeScript SDK | (new) | pending v1.0-rc1 final (RFC 0026) |
| Rust SDK | (new) | pending v1.1 (RFC 0027) |
| Go SDK | (new) | pending v1.1 (RFC 0028) |
| Conformance suite | (new) | scaffold with Python runner; Level 1/2/3 bundle definitions |
| Documentation site | (new) | pending (PLAN.md handoff) |
| CHI 2027 paper | outline | full draft |
| ICRA 2027 paper | outline | pending |
| RFCs | 0000-0012 | + 0013-0030 |
| Examples | (new) | pending |

## Pre-v1.0 final disclaimer

This is a release candidate. v1.0 final requires:

- At least 3 independent implementations passing the conformance suite at Level 2 (one at Level 3).
- At least one external paper accepted at a major venue (CHI, ICRA, IROS, CoRL, RSS, T-RO, CSCW, or T-RO).
- A neutral steward acceptance.

The RC label is the author's commitment to a candidate surface; surface stability is not guaranteed until v1.0 final.

## Contact

Issues: https://github.com/Ambar-13/Worker-Context-Protocol/issues
Security: security@rentably.ai (PGP key TBD; see SECURITY.md)
Code of Conduct violations: conduct@wcp-spec.org (or security@rentably.ai pre-v1.0 final)

## License

[Apache 2.0](./LICENSE)
