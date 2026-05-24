import { describe, it, expect } from "vitest";
import { canonicalJsonStringify, sha256Hex } from "../src/canonical";

describe("canonicalJsonStringify — additional coverage", () => {
  it("encodes primitives", () => {
    expect(canonicalJsonStringify("hello")).toBe('"hello"');
    expect(canonicalJsonStringify(42)).toBe("42");
    expect(canonicalJsonStringify(true)).toBe("true");
    expect(canonicalJsonStringify(null)).toBe("null");
  });

  it("encodes empty containers", () => {
    expect(canonicalJsonStringify({})).toBe("{}");
    expect(canonicalJsonStringify([])).toBe("[]");
  });

  it("escapes string contents per JSON.stringify", () => {
    expect(canonicalJsonStringify({ s: "a\"b\\c" })).toBe('{"s":"a\\"b\\\\c"}');
  });

  it("preserves insertion order WITHIN arrays even when the array contains objects", () => {
    const input = [{ b: 1, a: 2 }, { z: 9 }];
    expect(canonicalJsonStringify(input)).toBe('[{"a":2,"b":1},{"z":9}]');
  });

  it("recurses into nested arrays", () => {
    expect(canonicalJsonStringify([[1, 2], [3]])).toBe("[[1,2],[3]]");
  });

  it("byte-identical to Python json.dumps(sort_keys=True, separators=(\",\", \":\"))", () => {
    // Pinned regression vectors captured from the Python SDK.
    expect(canonicalJsonStringify({ a: 1, b: [2, 3], c: { d: null } })).toBe(
      '{"a":1,"b":[2,3],"c":{"d":null}}',
    );
  });
});

describe("sha256Hex", () => {
  it("hashes the empty buffer to the SHA-256 zero-vector", async () => {
    const empty = new Uint8Array(0);
    expect(await sha256Hex(empty)).toBe(
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    );
  });

  it("hashes 'abc' to the canonical test vector", async () => {
    const abc = new TextEncoder().encode("abc");
    expect(await sha256Hex(abc)).toBe(
      "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    );
  });

  it("accepts both Uint8Array and ArrayBuffer", async () => {
    const u = new TextEncoder().encode("abc");
    const a = u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength);
    expect(await sha256Hex(u)).toBe(await sha256Hex(a));
  });
});
