import { describe, it, expect } from "vitest";
import { canonicalJsonStringify } from "../src/canonical";

describe("canonicalJsonStringify", () => {
  it("sorts object keys", () => {
    expect(canonicalJsonStringify({ b: 1, a: 2 })).toBe('{"a":2,"b":1}');
  });

  it("preserves array order", () => {
    expect(canonicalJsonStringify([3, 1, 2])).toBe("[3,1,2]");
  });

  it("nests sorted keys", () => {
    expect(canonicalJsonStringify({ x: { c: 1, a: 2 } })).toBe(
      '{"x":{"a":2,"c":1}}',
    );
  });

  it("matches the canonical hash payload used by the Python SDK", () => {
    const payload = {
      claim_id: "c1",
      worker_id: "did:wcp:abc",
      eta: "2026-06-01T10:00:00Z",
      bid: null,
      payload_hash: "0".repeat(64),
      signed_at: "2026-05-23T12:00:00Z",
    };
    expect(canonicalJsonStringify(payload)).toBe(
      '{"bid":null,"claim_id":"c1","eta":"2026-06-01T10:00:00Z","payload_hash":"0000000000000000000000000000000000000000000000000000000000000000","signed_at":"2026-05-23T12:00:00Z","worker_id":"did:wcp:abc"}',
    );
  });
});
