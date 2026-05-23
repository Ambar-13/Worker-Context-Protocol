# Worker Context Protocol (WCP)

WCP is an open Apache-2.0 standard for AI agents to hire physical-world workers of any class (human contractor, autonomous robot, teleoperated robot, semi-autonomous, hybrid) through one worker-agnostic RPC surface.

Same lever as the Model Context Protocol (MCP) (informational and algorithmic: in-band capability discovery plus a typed call contract), applied to physical workers rather than software tools. The primitives MCP does not need, because tools cannot fail in physically irreversible ways, are **attest, supervise, settle, and abort**.

## Front door for the outside reader

You are most likely here because you are a robotics or platform engineer evaluating WCP for integration. The shortest path:

1. Read **[spec/0.1.md](./spec/0.1.md)** (under 30 pages; lead with the ASCII settlement state machine; nine RPCs with schemas).
2. Read **[spec/d4-verification.md](./spec/d4-verification.md)** to see that the same nine RPCs handle three application-layer task descriptors across two worker classes (six cells) without modification.
3. Skim **[GOVERNANCE.md](./GOVERNANCE.md)** for the donation-and-non-coercion commitments.
4. Clone, install, run the test suite:

```bash
python3.13 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
pytest wcp_coordinator/tests/
```

## Layout

```
spec/                       # the normative specification
  0.1.md                    # lead document; ASCII state machine, 9 RPCs
  did-method-wcp.md         # W3C DID Core registration for did:wcp
  d4-verification.md        # 3 descriptors x 2 worker classes = 6 cells
  schemas/                  # JSON Schemas for typed objects
GOVERNANCE.md               # pointers; donation trajectory
DONATION_COMMITMENT.md      # binding v1.0 stewardship donation
NON_COERCION_COMMITMENT.md  # 5x integration-time ratio commitment
CHARTER.md                  # TSC composition + decision rights
RFC_PROCESS.md              # lazy consensus rules
rfcs/                       # RFCs: 0001 initial spec, 0002 subcontracting,
                            # 0003 evidence kinds registry, 0004-0012 one
                            # per RPC method
wcp_coordinator/            # FastAPI reference backend (Apache 2.0)
  attestation_verifier/     # SINGLE POINT of worker-class agnosticism
  tests/                    # 44 tests; D4 + 13 adversarial scenarios
pwa/wcp/                    # PWA module for the Rentably contractor app
                            # (TypeScript, under 2000 LOC)
wcp_worker/                 # ROS 2 Humble plugin (Jazzy-compat)
                            # (Python, under 2000 LOC)
paper/                      # CHI 2027 + ICRA 2027 dual-framing draft
                            # plus coalition outreach emails
PLAN.md                     # the consolidated execution plan
```

## The single sentence

WCP v0.1 is one worker-agnostic RPC surface that does not know whether the worker is human or robot, shipped with one ROS 2 Humble reference plugin under 2000 LOC and one PWA module extending Rentably's existing contractor app under 2000 LOC, one FastAPI reference backend wired into Rentably's existing Stripe two-phase escrow, a public Apache 2.0 license with a written commitment to donate to a neutral steward at v1.0, a non-coercion commitment bounding non-WCP integration time within a 5x ratio, an SDK ergonomics gate of under 8 hours for outside robot engineers and under 2 hours for outside human-side engineers, an adversarial test pass across three descriptors and two worker classes before publication, a coalition of two of three (academic, worker provider, AI-agent platform) committed before broad announcement, and a launch gate of three signed conditional pre-purchase pilots running on the human-contractor side of Rentably's existing Singapore wedge before any robot vendor is asked to ship.

## Status

Pre-publication v0.1.

| Artifact | State | Notes |
|---|---|---|
| Spec | drafted | spec/0.1.md, schemas, did-method, d4-verification |
| Governance | drafted | 5 separately citable files |
| FastAPI coordinator | shipped | 44 tests green; D4 + 13 adversarial scenarios |
| PWA module | shipped | 906 LOC; vitest config in place |
| ROS 2 plugin | shipped | 830 LOC; 8 host-independent tests green |
| Simulator demo | deferred | Day 1-2 work; Gazebo Harmonic + TurtleBot 4 |
| Coalition emails | drafted | placeholders preserved per PLAN |
| RFCs | seeded | 0000 template + 0001-0012 |
| Paper | outlined | CHI 2027 primary + ICRA 2027 secondary |

## Prior art

WCP positions explicitly against MCP, VDA 5050, ROS 2 actions, NVIDIA Isaac, OPC UA, FIPA-ACL, KQML, TaskRabbit/Upwork class platforms, ServiceTitan-class FSM tools, Matter/CHIP (governance lesson), and the OCI image/runtime split (governance template). See spec/0.1.md Section 9.

## License

Apache 2.0. See [LICENSE](./LICENSE).

## Contact

Issues: https://github.com/Ambar-13/Worker-Context-Protocol/issues
Security: security@rentably.ai
