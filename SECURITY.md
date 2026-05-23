# WCP Security Policy

## Supported versions

| Version | Supported |
|---|---|
| v0.2 | yes (RC; surface may change) |
| v0.1 | yes (legacy; security fixes only) |
| pre-v0.1 | no |

Post v1.0 final, an LTS policy will be published on the wcp-spec.org domain.

## Reporting a vulnerability

We accept reports via:

- Email: `security@rentably.ai` (pre-v1.0 final; PGP key fingerprint published below)
- GitHub Security Advisories: https://github.com/Ambar-13/Worker-Context-Protocol/security/advisories/new

**Do not** report security issues via public GitHub Issues, GitHub Discussions, or social media.

## Response SLA

| Severity | Initial acknowledgement | Fix availability |
|---|---|---|
| Critical (active exploit, identity bypass, audit chain forgery) | 24 hours | 7 days |
| High (signature verification gap, privilege escalation) | 48 hours | 30 days |
| Medium (information disclosure, replay attack window) | 5 business days | 60 days |
| Low (defense-in-depth, hardening) | 10 business days | 90 days |

After a fix is available, we coordinate disclosure with the reporter. Default disclosure window: 90 days from initial report, or sooner if a fix is publicly available.

## PGP key (pre-v1.0 final)

```
-----BEGIN PGP PUBLIC KEY BLOCK-----

[PRINCIPAL TO PROVIDE: PGP public key for security@rentably.ai]

-----END PGP PUBLIC KEY BLOCK-----
```

INTEGRATION-GAP: the PGP key has not yet been generated and published. v0.2 readers should fall back to GitHub Security Advisories.

## Threat model

See `spec/threat-model.md` for the STRIDE analysis per RPC and per trust boundary.

## What is in scope

- The protocol specification in `spec/`
- The reference implementations in `wcp_coordinator/`, `wcp_worker/`, `pwa/wcp/`, `wcp_sdk_*/`
- The conformance suite in `conformance/`

## What is out of scope

- Third-party implementations (report to those projects' security policies).
- Operator-specific deployments (report to those operators).
- Physical security of worker devices.
- Network-layer DDoS at the operator's infrastructure.
- Compromise of upstream dependencies (report to the upstream; we MAY accept and pass-through).

## Bug bounty

Pre-v1.0 final, there is no formal bug bounty. We acknowledge reporters in `CHANGELOG.md` with their consent. Post-v1.0 final, the steward MAY operate a bounty program.

## Anti-trust note

WCP is a vendor-neutral protocol. Security reports are evaluated on technical merit regardless of the reporter's affiliation or relationship to Rentably or the steward.
