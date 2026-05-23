# RFC 0026: TypeScript SDK

- Author(s): TBD
- Status: open (v1.1 deliverable)
- Type: informational
- Created: 2026-05-23
- Targets: v1.0-rc1 final or v1.1

## Summary

A TypeScript SDK (`wcp_sdk_typescript/`) mirroring the Python SDK's surface. Designed for Node, browser, and edge runtimes.

## Motivation

Many agents and PWAs are TypeScript-first. The Python SDK ships at v1.0-rc1; the TypeScript SDK is the next priority.

## Open design questions

- Web Crypto Subtle vs noble-curves for Ed25519 (browser support varies).
- Package manager: npm only or also pnpm/yarn classic.
- Tree-shakeable build for browser targets.

## Implementation track

v1.0-rc1 final; the PWA module at `pwa/wcp/` is a related but not identical surface (the PWA module is application-shaped React; the SDK is library-shaped).
