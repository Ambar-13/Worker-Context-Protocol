/**
 * Collects attestation evidence on the human worker's device.
 *
 * Four modes per spec/0.1.md:
 *   - cryptographic-presence: WebGeolocation samples bracketing a duration
 *   - sensor-witness: photo with EXIF (server records only the hash)
 *   - third-party-witness: customer signature captured on canvas
 *   - owner-sign-off: WhatsApp Business signed link inbound (out of band)
 *
 * Evidence is queued in IndexedDB (via the service worker bridge) when
 * offline; flushed on reconnect.
 */

import { WorkerIdentity, canonicalJsonStringify } from "./identity";

export type AttestationMode =
  | "sensor-witness"
  | "third-party-witness"
  | "cryptographic-presence"
  | "owner-sign-off";

export interface AttestationEvidence {
  schema_version: "wcp/0.1";
  mode: AttestationMode;
  kind: string;
  payload: Record<string, unknown>;
  payload_hash: string;
  sig: string;
  worker_id: string;
  claim_id: string;
  collected_at: string;
}

export class AttestationCollector {
  constructor(private readonly identity: WorkerIdentity) {}

  async geofenceCheckInOut(args: {
    claim_id: string;
    region: unknown;
    checkInPosition: GeolocationPosition;
    checkOutPosition: GeolocationPosition;
  }): Promise<AttestationEvidence> {
    const payload = {
      check_in_at: new Date(args.checkInPosition.timestamp).toISOString(),
      check_out_at: new Date(args.checkOutPosition.timestamp).toISOString(),
      region: args.region,
      check_in_accuracy_m: args.checkInPosition.coords.accuracy,
      check_out_accuracy_m: args.checkOutPosition.coords.accuracy,
    };
    return this.makeEvidence(
      "cryptographic-presence",
      "geofence_check_in_out",
      payload,
      args.claim_id,
    );
  }

  async photoWithExif(args: {
    claim_id: string;
    photoBytes: Uint8Array;
    exif: { datetime: string; gps_lat?: number; gps_lon?: number };
  }): Promise<AttestationEvidence> {
    const photo_hash = await WorkerIdentity.sha256Hex(args.photoBytes);
    return this.makeEvidence(
      "sensor-witness",
      "photo_with_exif",
      { photo_hash, exif: args.exif },
      args.claim_id,
    );
  }

  async customerSignature(args: {
    claim_id: string;
    signed_text: string;
    signature_image_bytes: Uint8Array;
  }): Promise<AttestationEvidence> {
    const signature_image_hash = await WorkerIdentity.sha256Hex(
      args.signature_image_bytes,
    );
    return this.makeEvidence(
      "third-party-witness",
      "customer_signature",
      { signed_text: args.signed_text, signature_image_hash },
      args.claim_id,
    );
  }

  async whatsappBusinessSignedLink(args: {
    claim_id: string;
    signing_party_did: string;
    signed_token: string;
    issued_at: string;
  }): Promise<AttestationEvidence> {
    return this.makeEvidence(
      "owner-sign-off",
      "whatsapp_business_signed_link",
      {
        signing_party_did: args.signing_party_did,
        signed_token: args.signed_token,
        issued_at: args.issued_at,
      },
      args.claim_id,
    );
  }

  private async makeEvidence(
    mode: AttestationMode,
    kind: string,
    payload: Record<string, unknown>,
    claim_id: string,
  ): Promise<AttestationEvidence> {
    const collected_at = new Date().toISOString();
    const payload_bytes = new TextEncoder().encode(canonicalJsonStringify(payload));
    const payload_hash = await WorkerIdentity.sha256Hex(payload_bytes);
    const canonical = {
      mode,
      kind,
      payload_hash,
      worker_id: this.identity.did,
      claim_id,
      collected_at,
    };
    const sig = await this.identity.sign(canonical);
    return {
      schema_version: "wcp/0.1",
      mode,
      kind,
      payload,
      payload_hash,
      sig,
      worker_id: this.identity.did,
      claim_id,
      collected_at,
    };
  }
}
