# RFC 0030: Internationalization and Translations

- Author(s): TBD
- Status: open (v1.1 deliverable)
- Type: informational
- Created: 2026-05-23
- Targets: v1.1

## Summary

Translate the spec front-matter (overview, quickstart, conformance levels, the single sentence in `PLAN.md` Section 9) to at least 3 additional languages (Mandarin, Spanish, French) as a globalization signal.

## Motivation

WCP targets a global community. English-only documentation closes off prospective implementers in non-English-primary markets. A baseline translation set signals that the project values that audience.

## Open design questions

- Which sections to translate (full spec is large; front-matter and quickstart is tractable).
- Translation source-of-truth (community PRs vs paid translation).
- How to keep translations in sync as English iterates.
- Encoding considerations (CJK in JSON Schema descriptions).

## Implementation track

v1.1; `docs/i18n/<locale>/` directory structure.
