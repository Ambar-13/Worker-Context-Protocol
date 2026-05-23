# Contributing to WCP

Thank you for considering a contribution. WCP is an open protocol; contributions from any implementer or operator are welcome under the Apache 2.0 license.

## How to contribute

| What | Where | Process |
|---|---|---|
| Spec change | `spec/` | Open an RFC in `rfcs/` per `RFC_PROCESS.md` |
| Bug in a reference implementation | `wcp_coordinator/`, `wcp_worker/`, `pwa/wcp/`, `wcp_sdk_*/` | GitHub Issue with reproduction; PR with tests |
| New evidence kind | `rfcs/0003-evidence-kinds-registry.md` | PR against that RFC with payload schema and verifier reference |
| New federation primitive | `rfcs/0016-federation-primitives.md` or new RFC | Standards-track RFC |
| Documentation | `docs/`, `operator-guide/` | PR; CI builds the doc site |
| Conformance test | `conformance/test-suite/` | PR with test fixture and expected result |

## Developer certificate of origin

Every commit must include a `Signed-off-by:` line indicating you have read and agree to the Developer Certificate of Origin 1.1 ([https://developercertificate.org/](https://developercertificate.org/)).

```
Signed-off-by: Random J Developer <random@example.org>
```

`git commit -s` adds this automatically.

## Pull request checklist

- [ ] Tests added or updated; CI green.
- [ ] Spec-affecting changes accompanied by an RFC PR.
- [ ] Documentation updated where the change is user-facing.
- [ ] `CHANGELOG.md` entry added under the next pending version.
- [ ] `Signed-off-by:` on all commits.

## Code style

- Python: black + ruff; mypy strict.
- TypeScript: prettier + eslint; `tsc --strict`.
- Rust: `cargo fmt` + `cargo clippy --deny warnings`.
- Go: `gofmt` + `go vet`.
- Markdown: 100-character soft wrap; no emdash characters.

## Review process

PRs require at least one TSC member's approval for changes under `spec/` or any `*.md` in the repo root. Reference-implementation PRs require one maintainer's approval. RFC PRs run on the 14-day lazy-consensus clock per `RFC_PROCESS.md`.

## Community

- GitHub Issues: bug reports, RFCs in draft.
- GitHub Discussions: design questions, integration help.
- Pre-v1.0 final: a working group call cadence is TBD; the TSC will publish.

## Code of conduct

All contributors and users are bound by `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).

## Trademark

"WCP" and "WCP-conformant" are subject to the policy in `TRADEMARK_POLICY.md`. Pre-v1.0 final, Rentably holds the mark with a written non-enforcement commitment.

## Pre-v1.0 final disclaimers

The protocol is at v1.0-rc1. The surface is the candidate for v1.0 final, but adoption validation has not yet occurred. Contributors targeting v1.0 final should expect potentially-breaking changes in subsequent RC releases.
