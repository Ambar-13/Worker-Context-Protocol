/**
 * v2-shape Worker class for the TypeScript SDK.
 *
 * Decorators are unstable across TC39 and TypeScript versions; this SDK uses
 * method-builder fallback (`.handle(...)`, `.attest(...)`) which is decorator-
 * compatible when the TC39 stage-3 decorators land in the consumer's tsc.
 */

import { canonicalJsonStringify, sha256Hex } from "./canonical";
import { WorkerIdentity } from "./identity";
import { RpcClient } from "./rpc-client";

export type WorkerClass =
  | "human"
  | "autonomous_robot"
  | "teleoperated_robot"
  | "semi_autonomous"
  | "hybrid";

export type AttestationMode =
  | "sensor-witness"
  | "third-party-witness"
  | "cryptographic-presence"
  | "owner-sign-off";

type Handler = (task: Record<string, unknown>) => Promise<Record<string, unknown>>;
type Attester = (
  claimId: string,
  task: Record<string, unknown>,
) => Promise<{ kind: string; payload: Record<string, unknown> }>;

export interface WorkerOptions {
  name: string;
  workerClass: WorkerClass;
  coordinator: string;
  principalId?: string;
  descriptorTypes?: string[];
  certifications?: Array<{ issuer: string; id: string; expires?: string }>;
  classExtension?: Record<string, unknown>;
  currentLocation?: Record<string, unknown>;
}

export class Worker {
  public did = "";
  public publicKeyB64 = "";
  private identity: WorkerIdentity | null = null;
  private rpc: RpcClient;
  private handlers = new Map<string, Handler>();
  private attesters = new Map<AttestationMode, Attester>();

  constructor(public readonly options: WorkerOptions) {
    this.rpc = new RpcClient(options.coordinator);
  }

  handle(descriptorType: string, fn: Handler): this {
    this.handlers.set(descriptorType, fn);
    return this;
  }

  attest(mode: AttestationMode, fn: Attester): this {
    this.attesters.set(mode, fn);
    return this;
  }

  async run(): Promise<void> {
    this.identity = await WorkerIdentity.generate();
    this.did = this.identity.did;
    this.publicKeyB64 = this.identity.publicKeyB64;
    await this.rpc.connect();
    const descriptor = this.buildDescriptor();
    await this.rpc.call("capabilities/list", {
      worker_id: this.did,
      capabilities: descriptor,
    });
    // Stream-driven loop: claim tasks as the coordinator posts dispatches.
    this.rpc.onStreamEvent((event) => {
      if (event.event_type === "task_posted_for_worker") {
        void this.executeFullLifecycle(event.payload as Record<string, unknown>);
      }
    });
  }

  private buildDescriptor(): Record<string, unknown> {
    const o = this.options;
    return {
      schema_version: "wcp/1.0-rc1",
      worker_id: this.did,
      principal_id: o.principalId ?? "did:wcp:example-principal",
      class: o.workerClass,
      required: {
        current_location: o.currentLocation ?? { venue_id: "venue-a", map_id: "map-a" },
        available_windows: [{ rrule: "FREQ=DAILY", timezone: "UTC" }],
        attestation_methods_supported: [
          "sensor-witness",
          "third-party-witness",
          "cryptographic-presence",
          "owner-sign-off",
        ],
        certifications: o.certifications ?? [],
        policy_windows: [],
        attestation_keys: [
          { kty: "OKP", crv: "Ed25519", x: this.publicKeyB64 },
        ],
        as_of: new Date().toISOString(),
      },
      class_extension: {
        ...(o.classExtension ?? {}),
        descriptor_types: o.descriptorTypes ?? [],
      },
    };
  }

  private async executeFullLifecycle(dispatch: Record<string, unknown>): Promise<void> {
    const task = (dispatch.task as Record<string, unknown>) ?? {};
    const taskId = (dispatch.task_id ?? task.task_id) as string;
    const descriptorType = task.descriptor_type as string;
    const handler = this.handlers.get(descriptorType);
    if (!handler) return;

    const eta = new Date().toISOString();
    const payloadHash = await sha256Hex(
      new TextEncoder().encode(canonicalJsonStringify({ task_id: taskId })),
    );
    const signedAt = new Date().toISOString();
    const accCanonical = {
      task_id: taskId,
      worker_id: this.did,
      eta,
      bid: null,
      payload_hash: payloadHash,
      signed_at: signedAt,
    };
    const sig = await this.identity!.sign(accCanonical);
    const claim = (await this.rpc.call("tasks/claim", {
      task_id: taskId,
      worker_id: this.did,
      eta,
      acceptance_attestation: {
        sig,
        alg: "Ed25519",
        payload_hash: payloadHash,
        signed_at: signedAt,
      },
    })) as { claim_id: string; accepted: boolean };

    await this.rpc.call("tasks/execute", { claim_id: claim.claim_id });
    await handler(task);

    const attestations = [];
    for (const [mode, fn] of this.attesters.entries()) {
      const built = await fn(claim.claim_id, task);
      const collectedAt = new Date().toISOString();
      const ph = await sha256Hex(
        new TextEncoder().encode(canonicalJsonStringify(built.payload)),
      );
      const evCanonical = {
        mode,
        kind: built.kind,
        payload_hash: ph,
        worker_id: this.did,
        claim_id: claim.claim_id,
        collected_at: collectedAt,
      };
      const evSig = await this.identity!.sign(evCanonical);
      attestations.push({
        schema_version: "wcp/1.0-rc1",
        mode,
        kind: built.kind,
        payload: built.payload,
        payload_hash: ph,
        sig: evSig,
        worker_id: this.did,
        claim_id: claim.claim_id,
        collected_at: collectedAt,
      });
    }
    if (attestations.length > 0) {
      await this.rpc.call("tasks/attest", {
        claim_id: claim.claim_id,
        attestations,
      });
    }
  }

  close(): void {
    this.rpc.close();
  }
}
