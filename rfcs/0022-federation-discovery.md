# RFC 0022: Federation Discovery at Scale

- Author(s): TBD
- Status: open (v1.1 open question)
- Type: standards-track
- Created: 2026-05-23
- Targets: v1.1

## Summary

How to discover federation peers without a global directory while avoiding O(N^2) bilateral negotiations.

## Motivation

`spec/federation.md` defines bilateral trust anchors. As the number of coordinators grows, bilateral discovery scales poorly. Some discovery primitive is needed without re-introducing the central-authority failure mode WCP rejects in `spec/1.0-rc1.md` Section 2 (MQTT-rejection).

## Candidate approaches under evaluation

1. **Federation overlay graphs**: coordinators advertise their peer list publicly; transitive discovery via 1-hop walk.
2. **Trust hubs**: voluntary opt-in to a list-curating hub (Linux-Foundation-hosted, for example) without centralized authority.
3. **Self-publishing via well-known**: every coordinator publishes `/.well-known/wcp-federation-peers.json`; agents and other coordinators scrape on demand.
4. **DNS-SD**: discover coordinators via DNS service records.

Unresolved at v1.0-rc1.
