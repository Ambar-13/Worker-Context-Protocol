# Contributing to WCP

WCP is an open protocol. Contributions from any implementer or operator are welcome under the Apache 2.0 license.

## Where things land

| Contribution | Lives in | Process |
|---|---|---|
| Spec change | `spec/` | Open an RFC in `rfcs/` per `RFC_PROCESS.md` |
| Bug in a reference implementation | `wcp_coordinator/`, `wcp_worker/`, `pwa/wcp/`, `wcp_sdk_*/` | GitHub Issue with a reproduction; PR with tests |
| New evidence kind | `rfcs/0003-evidence-kinds-registry.md` | PR against that RFC with payload schema and verifier reference |
| New federation primitive | `rfcs/0016-federation-primitives.md` or a new RFC | Standards-track RFC |
| Documentation | `docs/`, `operator-guide/` | PR; CI builds the doc site |
| Conformance test | `conformance/test-suite/` | PR with test fixture and expected result |

## Developer Certificate of Origin

Every commit must carry a `Signed-off-by:` line indicating you have read and agree to the Developer Certificate of Origin 1.1 (https://developercertificate.org/):

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

- Python: `black` + `ruff`; `mypy --strict`.
- TypeScript: `prettier` + `eslint`; `tsc --strict`.
- Rust: `cargo fmt` + `cargo clippy --deny warnings`.
- Go: `gofmt` + `go vet`.
- Markdown: 100-character soft wrap; no em-dash characters.

## Review

PRs touching `spec/` or any `*.md` in the repo root require at least one TSC member's approval. Reference-implementation PRs require one maintainer's approval. RFC PRs run on the 14-day lazy-consensus clock per `RFC_PROCESS.md`.

## Community

- GitHub Issues for bug reports and draft RFCs.
- GitHub Discussions for design questions and integration help.
- A working-group call cadence will be announced by the TSC once v1.0 final stewardship is in place.

## Code of conduct

All contributors and users are bound by `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).

## Trademark

"WCP" and "WCP-conformant" are subject to the policy in `TRADEMARK_POLICY.md`. Pre-v1.0 final, Rentably holds the mark with a written non-enforcement commitment.

## Pre-v1.0 final

The protocol is a release candidate. v1.0 final waits on adoption signals — an independent Level 2 coordinator implementation, peer-reviewed acceptance, and neutral-foundation stewardship. Contributors targeting v1.0 final should expect potentially-breaking changes in subsequent RC releases.
