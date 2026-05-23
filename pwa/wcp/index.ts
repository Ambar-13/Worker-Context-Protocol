/**
 * WCP PWA module entry point.
 *
 * Designed to merge into a worker-provider's existing contractor application at
 * `app/(contractor)/wcp/`. Hard cap: under 2000 LOC total delta.
 *
 * Composition example:
 *
 *   const id = await WorkerIdentity.generate();
 *   const rpc = new WcpRpcClient({ url: "wss://coordinator.rentably.ai/wcp/ws" });
 *   const publisher = new CapabilityPublisher(id, rpc);
 *   await publisher.publish(publisher.buildHumanDescriptor(profile));
 *   const collector = new AttestationCollector(id);
 *   // render <TaskListener /> and <ExecuteSession /> as the contractor works
 */

export { WorkerIdentity, canonicalJsonStringify } from "./identity";
export { WcpRpcClient, WcpRpcError } from "./rpc-client";
export type { RpcClientOptions, RpcMode } from "./rpc-client";
export { CapabilityPublisher } from "./capability-publisher";
export type { CapabilityDescriptor, WorkerClass } from "./capability-publisher";
export { AttestationCollector } from "./attestation-collector";
export type { AttestationEvidence, AttestationMode } from "./attestation-collector";
export { ServiceWorkerBridge } from "./service-worker-bridge";
export type { QueuedEvidence } from "./service-worker-bridge";
export { TaskListener } from "./task-listener";
export type { TaskSummary } from "./task-listener";
export { ExecuteSession } from "./execute-session";
