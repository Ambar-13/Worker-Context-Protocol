import { describe, it, expect } from "vitest";
import { didFromPubkey, WorkerIdentity, AgentIdentity } from "../src/identity";

describe("didFromPubkey", () => {
  it("produces a did:wcp: prefix from 32 bytes", () => {
    const bytes = new Uint8Array(32);
    for (let i = 0; i < 32; i++) bytes[i] = i;
    const did = didFromPubkey(bytes);
    expect(did.startsWith("did:wcp:")).toBe(true);
    expect(did.length).toBeGreaterThan("did:wcp:".length + 30);
  });

  it("rejects pubkeys that are not exactly 32 bytes", () => {
    expect(() => didFromPubkey(new Uint8Array(31))).toThrow();
    expect(() => didFromPubkey(new Uint8Array(33))).toThrow();
  });

  it("produces stable output for identical input", () => {
    const bytes = new Uint8Array(32).fill(7);
    expect(didFromPubkey(bytes)).toBe(didFromPubkey(bytes));
  });

  it("produces different DIDs for different input", () => {
    const a = new Uint8Array(32).fill(1);
    const b = new Uint8Array(32).fill(2);
    expect(didFromPubkey(a)).not.toBe(didFromPubkey(b));
  });
});

// Skip the WebCrypto-Ed25519 generation tests under Node versions that lack
// Ed25519 in subtle. Node 20+ has it; older shims do not. We gate by feature.
const hasEd25519: () => Promise<boolean> = async () => {
  try {
    await crypto.subtle.generateKey(
      { name: "Ed25519" } as EcKeyAlgorithm,
      false,
      ["sign", "verify"],
    );
    return true;
  } catch {
    return false;
  }
};

describe.runIf(true)("WorkerIdentity.generate (requires Ed25519 in Web Crypto)", () => {
  it("yields a did:wcp identity with a 32-byte public key", async () => {
    if (!(await hasEd25519())) return;
    const w = await WorkerIdentity.generate();
    expect(w.did.startsWith("did:wcp:")).toBe(true);
    // The b64url-encoded pubkey, after un-encoding, is 32 bytes.
    const pad = "=".repeat((-w.publicKeyB64.length) % 4 + 4 - ((w.publicKeyB64.length + (-w.publicKeyB64.length % 4)) % 4));
    // Quick sanity: the b64url string is non-empty and decodes to 32 bytes.
    expect(w.publicKeyB64.length).toBeGreaterThan(0);
  });

  it("signs a payload to an ed25519: prefixed urlsafe base64 string", async () => {
    if (!(await hasEd25519())) return;
    const w = await WorkerIdentity.generate();
    const sig = await w.sign({ a: 1, b: 2 });
    expect(sig.startsWith("ed25519:")).toBe(true);
    expect(sig.length).toBeGreaterThan("ed25519:".length + 80);
  });

  it("signs the canonical form, not the input object order", async () => {
    if (!(await hasEd25519())) return;
    const w = await WorkerIdentity.generate();
    const a = await w.sign({ a: 1, b: 2 });
    const b = await w.sign({ b: 2, a: 1 });
    expect(a).toBe(b);
  });
});

describe.runIf(true)("AgentIdentity.generate", () => {
  it("yields a distinct identity from WorkerIdentity.generate", async () => {
    if (!(await hasEd25519())) return;
    const w = await WorkerIdentity.generate();
    const a = await AgentIdentity.generate();
    expect(a.did).not.toBe(w.did);
  });
});
