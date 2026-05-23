# @wcp/sdk

Worker Context Protocol TypeScript SDK. Vendor-neutral.

```bash
npm install @wcp/sdk
```

## Worker

```typescript
import { Worker } from "@wcp/sdk";

const worker = new Worker({
  name: "my-worker",
  workerClass: "autonomous_robot",
  coordinator: "ws://localhost:8000/wcp/ws",
  descriptorTypes: ["transport"],
});

worker.handle("transport", async (task) => {
  return { delivered_at: new Date().toISOString() };
});

worker.attest("sensor-witness", async (claimId, task) => {
  return {
    kind: "indoor_pose_track",
    payload: { track: [{ t: new Date().toISOString(), x: 0, y: 0 }] },
  };
});

await worker.run();
```

## Agent

```typescript
import { Agent } from "@wcp/sdk";

const agent = new Agent({ name: "my-agent", coordinator: "ws://localhost:8000/wcp/ws" });
await agent.connect();
const result = await agent.postTask(taskDescriptor, {
  bondRef: "example-bond-1",
  expiry: "2099-12-31T00:00:00Z",
});
```

The wire shapes match the Python SDK. Cross-SDK interop (TS agent posting tasks to a coordinator backing a Python worker, or the reverse) works as long as both SDKs target the same coordinator.

## License

Apache 2.0
