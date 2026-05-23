export { canonicalJsonStringify, sha256Hex } from "./canonical";
export { WorkerIdentity, AgentIdentity, didFromPubkey } from "./identity";
export { RpcClient, WcpRpcError } from "./rpc-client";
export { Worker } from "./worker";
export type {
  WorkerClass,
  AttestationMode,
  WorkerOptions,
} from "./worker";
export { Agent } from "./agent";
export type { AgentOptions } from "./agent";

export const SCHEMA_VERSION = "wcp/1.0-rc1";
export const SDK_VERSION = "1.0.0-rc2";
