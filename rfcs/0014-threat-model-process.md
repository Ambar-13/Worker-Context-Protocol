# RFC 0014: Threat Model Process

- Author(s): Rentably (principal)
- Status: accepted (part of v0.2)
- Type: standards-track
- Created: 2026-05-23

## Summary

Adopts STRIDE-per-RPC-and-per-asset as the canonical threat-modeling methodology. The current model lives at `spec/threat-model.md` and updates by RFC.

## Motivation

Security analyses age. Pinning the methodology and cadence keeps the model current.

## Design

- STRIDE applied per asset and per trust boundary.
- Three adversary profiles (rational economic, regulatory, safety-critical).
- The Security WG (per `TSC_BYLAWS.md`) owns the threat-model document.
- Updates require RFC; emergency updates use the security emergency flag.

## Cadence

The Security WG reviews the threat model at least quarterly. Material updates ship as RFC amendments.

## Implementation track

`spec/threat-model.md` is the artifact; updates via PR + RFC reference.
