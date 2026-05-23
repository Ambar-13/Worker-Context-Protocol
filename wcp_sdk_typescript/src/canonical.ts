/**
 * Canonical JSON serialization compatible with the Python SDK.
 *
 * Same approach as the Python implementation: sorted keys, no whitespace.
 * Matches `json.dumps(payload, sort_keys=True, separators=(",", ":"))`.
 */

export function canonicalJsonStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return "[" + value.map((x) => canonicalJsonStringify(x)).join(",") + "]";
  }
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  return (
    "{" +
    keys.map((k) => JSON.stringify(k) + ":" + canonicalJsonStringify(obj[k])).join(",") +
    "}"
  );
}

export async function sha256Hex(data: ArrayBuffer | Uint8Array): Promise<string> {
  const buf = data instanceof Uint8Array ? data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength) : data;
  const hash = await crypto.subtle.digest("SHA-256", buf);
  const bytes = new Uint8Array(hash);
  let out = "";
  for (const b of bytes) out += b.toString(16).padStart(2, "0");
  return out;
}
