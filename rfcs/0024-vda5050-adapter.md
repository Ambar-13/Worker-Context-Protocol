# RFC 0024: VDA 5050 Adapter

- Author(s): TBD
- Status: open (v1.1 deliverable)
- Type: informational
- Created: 2026-05-23
- Targets: v1.1

## Summary

A reference adapter that bridges VDA 5050 fleet protocol to WCP. Lets AGV/AMR fleets already speaking VDA 5050 expose themselves as WCP workers without firmware change.

## Motivation

VDA 5050 has installed base in warehousing. A WCP gateway that translates VDA 5050 Order/State/Visualization messages to WCP RPCs unlocks that fleet for WCP marketplaces.

## Open design questions

- How to derive a WCP CapabilityDescriptor from VDA 5050 Factsheet messages.
- How to map VDA 5050 Order's nodes/edges to a WCP `transport` descriptor_payload.
- How to translate WCP `tasks/attest` to VDA 5050 OrderUpdate confirmations.

## Implementation track

Targeted as a v1.1 deliverable; reference adapter code lives in `examples/vda5050-bridge/` once written.
