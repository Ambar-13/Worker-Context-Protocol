/**
 * WCP worker identity for the human-side PWA.
 *
 * Holds the worker's Ed25519 DID keypair in Web Crypto Subtle. Persists the
 * private key with `extractable: false` so it cannot leave the device. The
 * public key drives the `did:wcp` identifier per spec/did-method-wcp.md.
 *
 * INTEGRATION-GAP: when merged into the existing Rentably contractor app,
 * the keypair lifecycle is bound to login/logout: generate on first login,
 * persist via IndexedDB-backed CryptoKey storage, rotate on principal change.
 */

const BASE58_ALPHABET =
  "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

function base58Encode(bytes: Uint8Array): string {
  let n = 0n;
  for (const b of bytes) {
    n = (n << 8n) | BigInt(b);
  }
  let out = "";
  while (n > 0n) {
    const r = Number(n % 58n);
    n = n / 58n;
    out = BASE58_ALPHABET[r] + out;
  }
  let lead = 0;
  for (const b of bytes) {
    if (b === 0) lead++;
    else break;
  }
  return "1".repeat(lead) + out;
}

function urlSafeB64NoPad(buf: ArrayBuffer | Uint8Array): string {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

/**
 * Stable canonical JSON serialization compatible with the backend canonical
 * form (RFC 8785-style: sorted keys, no whitespace).
 */
export function canonicalJsonStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value))
    return "[" + value.map(canonicalJsonStringify).join(",") + "]";
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  const parts = keys.map(
    (k) => JSON.stringify(k) + ":" + canonicalJsonStringify(obj[k])
  );
  return "{" + parts.join(",") + "}";
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
    // Web Crypto supports Ed25519 natively on modern browsers (per the
    // current spec); polyfill for older environments may use noble-curves.
    const kp = (await crypto.subtle.generateKey(
      { name: "Ed25519" } as EcKeyAlgorithm,
      false,
      ["sign", "verify"]
    )) as CryptoKeyPair;
    const pubRaw = await crypto.subtle.exportKey("raw", kp.publicKey);
    const pubBytes = new Uint8Array(pubRaw);
    const did = `did:wcp:${base58Encode(pubBytes)}`;
    return new WorkerIdentity(kp, did, urlSafeB64NoPad(pubBytes));
  }

  async sign(payload: unknown): Promise<string> {
    const data = new TextEncoder().encode(canonicalJsonStringify(payload));
    const sig = await crypto.subtle.sign(
      { name: "Ed25519" },
      this.key.privateKey,
      data,
    );
    return "ed25519:" + urlSafeB64NoPad(sig);
  }

  async signBytes(data: Uint8Array): Promise<string> {
    const sig = await crypto.subtle.sign(
      { name: "Ed25519" },
      this.key.privateKey,
      data,
    );
    return "ed25519:" + urlSafeB64NoPad(sig);
  }

  static async sha256Hex(data: Uint8Array): Promise<string> {
    const h = await crypto.subtle.digest("SHA-256", data);
    const bytes = new Uint8Array(h);
    return Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }
}
