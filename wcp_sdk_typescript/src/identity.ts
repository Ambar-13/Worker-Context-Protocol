/**
 * did:wcp identity primitives for the TypeScript SDK.
 *
 * Uses Web Crypto Subtle (Ed25519) where available. Node 20+ supports
 * Ed25519 via subtle natively; browsers depend on the implementation status.
 */

const BASE58 =
  "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

function base58Encode(bytes: Uint8Array): string {
  let n = 0n;
  for (const b of bytes) n = (n << 8n) | BigInt(b);
  let out = "";
  while (n > 0n) {
    const r = Number(n % 58n);
    n = n / 58n;
    out = BASE58[r] + out;
  }
  let lead = 0;
  for (const b of bytes) {
    if (b === 0) lead++;
    else break;
  }
  return "1".repeat(lead) + out;
}

function urlSafeB64NoPad(b: ArrayBuffer | Uint8Array): string {
  const bytes = b instanceof Uint8Array ? b : new Uint8Array(b);
  let s = "";
  for (const x of bytes) s += String.fromCharCode(x);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function didFromPubkey(pubkey: Uint8Array): string {
  if (pubkey.length !== 32) throw new Error("Ed25519 public key must be 32 bytes");
  return `did:wcp:${base58Encode(pubkey)}`;
}

export class WorkerIdentity {
  private readonly key: CryptoKeyPair;
  public readonly did: string;
  public readonly publicKeyB64: string;

  private constructor(key: CryptoKeyPair, did: string, publicKeyB64: string) {
    this.key = key;
    this.did = did;
    this.publicKeyB64 = publicKeyB64;
  }

  static async generate(): Promise<WorkerIdentity> {
    const kp = (await crypto.subtle.generateKey(
      { name: "Ed25519" } as EcKeyAlgorithm,
      false,
      ["sign", "verify"],
    )) as CryptoKeyPair;
    const raw = await crypto.subtle.exportKey("raw", kp.publicKey);
    const bytes = new Uint8Array(raw);
    const did = didFromPubkey(bytes);
    return new WorkerIdentity(kp, did, urlSafeB64NoPad(bytes));
  }

  async sign(payload: unknown): Promise<string> {
    const { canonicalJsonStringify } = await import("./canonical");
    const data = new TextEncoder().encode(canonicalJsonStringify(payload));
    const sig = await crypto.subtle.sign({ name: "Ed25519" }, this.key.privateKey, data);
    return "ed25519:" + urlSafeB64NoPad(sig);
  }
}

export class AgentIdentity {
  private readonly key: CryptoKeyPair;
  public readonly did: string;

  private constructor(key: CryptoKeyPair, did: string) {
    this.key = key;
    this.did = did;
  }

  static async generate(): Promise<AgentIdentity> {
    const kp = (await crypto.subtle.generateKey(
      { name: "Ed25519" } as EcKeyAlgorithm,
      false,
      ["sign", "verify"],
    )) as CryptoKeyPair;
    const raw = await crypto.subtle.exportKey("raw", kp.publicKey);
    const did = didFromPubkey(new Uint8Array(raw));
    return new AgentIdentity(kp, did);
  }

  async sign(payload: unknown): Promise<string> {
    const { canonicalJsonStringify } = await import("./canonical");
    const data = new TextEncoder().encode(canonicalJsonStringify(payload));
    const sig = await crypto.subtle.sign({ name: "Ed25519" }, this.key.privateKey, data);
    return "ed25519:" + urlSafeB64NoPad(sig);
  }
}
