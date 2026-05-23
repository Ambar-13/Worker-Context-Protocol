/**
 * v2-shape Agent class for the TypeScript SDK.
 */

import { AgentIdentity } from "./identity";
import { RpcClient } from "./rpc-client";

export interface AgentOptions {
  name: string;
  coordinator: string;
}

export class Agent {
  public did = "";
  private identity: AgentIdentity | null = null;
  private rpc: RpcClient;

  constructor(public readonly options: AgentOptions) {
    this.rpc = new RpcClient(options.coordinator);
  }

  async connect(): Promise<void> {
    this.identity = await AgentIdentity.generate();
    this.did = this.identity.did;
    await this.rpc.connect();
  }

  async postTask(
    task: Record<string, unknown>,
    args: { bondRef: string; expiry: string; supervision?: Record<string, unknown> },
  ): Promise<Record<string, unknown>> {
    const params: Record<string, unknown> = {
      task,
      bond_ref: args.bondRef,
      expiry: args.expiry,
    };
    if (args.supervision) params.supervision = args.supervision;
    return (await this.rpc.call("tasks/post", params)) as Record<string, unknown>;
  }

  async discoverCapabilities(filter?: Record<string, unknown>): Promise<Record<string, unknown>> {
    const params: Record<string, unknown> = { agent_did: this.did };
    if (filter) params.filter = filter;
    return (await this.rpc.call("capabilities/subscribe", params)) as Record<string, unknown>;
  }

  close(): void {
    this.rpc.close();
  }
}
