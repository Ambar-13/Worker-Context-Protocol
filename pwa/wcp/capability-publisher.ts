/**
 * Publishes the worker's CapabilityDescriptor to the coordinator.
 *
 * Called on PWA load and on any profile mutation that changes the required
 * fields (location move, certifications added, policy windows changed).
 */

import type { WorkerIdentity } from "./identity";
import type { WcpRpcClient } from "./rpc-client";

export type WorkerClass =
  | "human"
  | "autonomous_robot"
  | "teleoperated_robot"
  | "semi_autonomous"
  | "hybrid";

export interface CapabilityDescriptor {
  schema_version: "wcp/0.1";
  worker_id: string;
  principal_id: string;
  class: WorkerClass;
  required: {
    current_location:
      | { geohash: string }
      | { venue_id: string; map_id: string };
    available_windows: { rrule: string; timezone: string }[];
    attestation_methods_supported: string[];
    certifications: { issuer: string; id: string; expires?: string }[];
    policy_windows: { type: string; scope: string }[];
    attestation_keys: { kty: "OKP"; crv: "Ed25519"; x: string }[];
    as_of: string;
  };
  class_extension: Record<string, unknown>;
}

export interface ContractorProfileSnapshot {
  principal_id: string;
  current_venue_id: string;
  current_map_id: string;
  skills: string[];
  languages: string[];
  certifications: { issuer: string; id: string; expires?: string }[];
}

export class CapabilityPublisher {
  constructor(
    private readonly identity: WorkerIdentity,
    private readonly rpc: WcpRpcClient,
  ) {}

  buildHumanDescriptor(
    profile: ContractorProfileSnapshot,
  ): CapabilityDescriptor {
    return {
      schema_version: "wcp/0.1",
      worker_id: this.identity.did,
      principal_id: profile.principal_id,
      class: "human",
      required: {
        current_location: {
          venue_id: profile.current_venue_id,
          map_id: profile.current_map_id,
        },
        available_windows: [
          { rrule: "FREQ=DAILY;BYHOUR=8-22", timezone: "Asia/Singapore" },
        ],
        attestation_methods_supported: [
          "sensor-witness",
          "third-party-witness",
          "cryptographic-presence",
          "owner-sign-off",
        ],
        certifications: profile.certifications,
        policy_windows: [{ type: "geographic", scope: "Singapore" }],
        attestation_keys: [
          { kty: "OKP", crv: "Ed25519", x: this.identity.publicKeyB64 },
        ],
        as_of: new Date().toISOString(),
      },
      class_extension: {
        skills: profile.skills,
        languages: profile.languages,
      },
    };
  }

  async publish(descriptor: CapabilityDescriptor): Promise<void> {
    // capabilities/list is worker-initiated in spec/0.1.md; coordinators
    // store the latest descriptor and assign monotonic revisions. The PWA
    // calls the method whenever the worker's profile changes.
    await this.rpc.call<{
      worker_id: string;
      capabilities: CapabilityDescriptor;
      ttl_seconds: number;
      revision: number;
    }>("capabilities/list", { worker_id: this.identity.did, capabilities: descriptor });
  }
}
