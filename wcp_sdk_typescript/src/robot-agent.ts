/**
 * RobotAgent: convenience subclass of Agent for the robot-as-agent pattern.
 *
 * Spec: spec/0.95.md Sections 2 and 3 (continuation pattern), amended by
 * spec/0.955.md (settlement block removed from descriptor;
 * max_attestation_attempts and marketplace_ref added).
 * Pattern doc: docs/patterns/robot-as-agent.md.
 * Reference deployment: examples/agents/delivery-robot-dispatcher/.
 *
 * The wire protocol identifier is unchanged from v0.2. This class wraps
 * the common "robot posts a follow-up task from inside its execute loop" case
 * with a single method, `postContinuation`. agent_class is informational and
 * is preserved through the agent's DID document service array.
 */

import { Agent, AgentOptions } from "./agent";
import { v4 as uuidv4 } from "uuid";

export type AgentClass =
  | "llm_agent"
  | "embodied_agent"
  | "scheduled_agent"
  | "human_supervisor";

export interface RobotAgentOptions extends AgentOptions {
  agentClass?: AgentClass;
}

export interface BuildContinuationArgs {
  priorClaimId: string;
  descriptorType: string;
  descriptorPayload: Record<string, unknown>;
  requiredEvidenceKinds?: string[];
  constraints: Record<string, unknown>;
  attestationRequirement: Record<string, unknown>;
  maxAttestationAttempts?: number;
  marketplaceRef?: string;
}

export class RobotAgent extends Agent {
  public readonly agentClass: AgentClass;

  constructor(options: RobotAgentOptions) {
    super(options);
    this.agentClass = options.agentClass ?? "embodied_agent";
  }

  /**
   * Build a task descriptor that continues from a prior claim.
   *
   * The caller supplies the two required blocks (constraints,
   * attestationRequirement). The helper adds schema_version, task_id,
   * posted_by, descriptor type and payload, the continuation_of reference,
   * and the optional v0.955 fields max_attestation_attempts and
   * marketplace_ref. Settlement is no longer a protocol concern at v0.955.
   */
  buildContinuation(args: BuildContinuationArgs): Record<string, unknown> {
    const descriptor: Record<string, unknown> = {
      schema_version: "wcp/0.2",
      task_id: uuidv4(),
      posted_by: this.did,
      descriptor_type: args.descriptorType,
      descriptor_payload: args.descriptorPayload,
      continuation_of: {
        claim_id: args.priorClaimId,
        required_evidence_kinds: args.requiredEvidenceKinds ?? [],
      },
      constraints: args.constraints,
      attestation_requirement: args.attestationRequirement,
      max_attestation_attempts: args.maxAttestationAttempts ?? 1,
    };
    if (args.marketplaceRef !== undefined) {
      descriptor.marketplace_ref = args.marketplaceRef;
    }
    return descriptor;
  }

  /**
   * Post a follow-up task that continues from `priorClaimId`. Validates that
   * the descriptor's continuation_of block matches before calling tasks/post.
   */
  async postContinuation(args: {
    priorClaimId: string;
    descriptor: Record<string, unknown>;
    expiry: string;
    supervision?: Record<string, unknown>;
  }): Promise<Record<string, unknown>> {
    const cont =
      (args.descriptor.continuation_of as
        | { claim_id?: string }
        | undefined) ?? {};
    if (cont.claim_id !== args.priorClaimId) {
      throw new Error(
        "descriptor.continuation_of.claim_id does not match priorClaimId",
      );
    }
    return this.postTask(args.descriptor, {
      expiry: args.expiry,
      supervision: args.supervision,
    });
  }

  /**
   * The agent_class metadata block this agent advertises through its DID
   * document's service array. Coordinators do not branch on it; operators
   * may use it for filtering and accounting.
   */
  agentClassDeclaration(): Record<string, unknown> {
    return {
      type: "WCPAgentClass",
      agent_class: this.agentClass,
      advertised_at: new Date().toISOString(),
    };
  }
}
