/**
 * RobotAgent: convenience subclass of Agent for the robot-as-agent pattern.
 *
 * Spec: spec/1.0-rc5.md Sections 2 and 3.
 * Pattern doc: docs/patterns/robot-as-agent.md.
 * Reference deployment: examples/agents/delivery-robot-dispatcher/.
 *
 * The wire protocol is unchanged from v1.0-rc1. This class wraps the common
 * "robot posts a follow-up task from inside its execute loop" case with a
 * single method, `postContinuation`. agent_class is informational and is
 * preserved through the agent's DID document service array.
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
  settlement: Record<string, unknown>;
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
   * The caller supplies the three required blocks (constraints,
   * attestationRequirement, settlement). The helper adds schema_version,
   * task_id, posted_by, descriptor type and payload, and the
   * continuation_of reference.
   */
  buildContinuation(args: BuildContinuationArgs): Record<string, unknown> {
    return {
      schema_version: "wcp/1.0-rc1",
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
      settlement: args.settlement,
    };
  }

  /**
   * Post a follow-up task that continues from `priorClaimId`. Validates that
   * the descriptor's continuation_of block matches before calling tasks/post.
   */
  async postContinuation(args: {
    priorClaimId: string;
    descriptor: Record<string, unknown>;
    bondRef: string;
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
      bondRef: args.bondRef,
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
