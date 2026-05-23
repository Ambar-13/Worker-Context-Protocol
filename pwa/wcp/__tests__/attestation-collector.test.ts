import { beforeAll, describe, expect, it } from "vitest";

import { AttestationCollector } from "../attestation-collector";
import { WorkerIdentity } from "../identity";

// The Ed25519 subtle algorithm is supported in modern Node (>=20). Vitest in
// jsdom or node mode must have `webcrypto` available. If a test environment
// lacks Ed25519, set the env var WCP_SKIP_CRYPTO=1 to skip these.

const SKIP = process.env.WCP_SKIP_CRYPTO === "1";

describe.skipIf(SKIP)("AttestationCollector", () => {
  let identity: WorkerIdentity;
  let collector: AttestationCollector;

  beforeAll(async () => {
    identity = await WorkerIdentity.generate();
    collector = new AttestationCollector(identity);
  });

  it("builds a customer_signature evidence with hashed image bytes", async () => {
    const sig_bytes = new Uint8Array([1, 2, 3, 4]);
    const ev = await collector.customerSignature({
      claim_id: "c1",
      signed_text: "Work done.",
      signature_image_bytes: sig_bytes,
    });
    expect(ev.mode).toBe("third-party-witness");
    expect(ev.kind).toBe("customer_signature");
    expect(ev.payload.signed_text).toBe("Work done.");
    expect(typeof ev.payload.signature_image_hash).toBe("string");
    expect(ev.sig.startsWith("ed25519:")).toBe(true);
    expect(ev.worker_id).toBe(identity.did);
    expect(ev.claim_id).toBe("c1");
  });

  it("builds a photo_with_exif evidence with photo hash, not raw bytes", async () => {
    const photo = new Uint8Array([10, 20, 30]);
    const ev = await collector.photoWithExif({
      claim_id: "c1",
      photoBytes: photo,
      exif: { datetime: "2026-06-01T10:00:00Z" },
    });
    expect(ev.kind).toBe("photo_with_exif");
    expect(typeof ev.payload.photo_hash).toBe("string");
    // Raw photo bytes MUST NOT appear in the payload.
    expect("photo_bytes" in ev.payload).toBe(false);
  });

  it("includes the worker DID as worker_id on every evidence", async () => {
    const ev = await collector.whatsappBusinessSignedLink({
      claim_id: "c1",
      signing_party_did: "did:wcp:customer",
      signed_token: "tok",
      issued_at: "2026-06-01T10:00:00Z",
    });
    expect(ev.worker_id).toBe(identity.did);
  });
});
