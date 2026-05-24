import { describe, it, expect, vi, beforeEach } from "vitest";
import { RpcClient, WcpRpcError } from "../src/rpc-client";

/**
 * Inject a minimal stub WebSocket onto globalThis so RpcClient.connect()
 * resolves without a real network. Each test gets a fresh stub.
 */
type Handler = (ev: { data: string }) => void;

class StubSocket {
  static instances: StubSocket[] = [];
  public onopen: (() => void) | null = null;
  public onmessage: Handler | null = null;
  public onclose: (() => void) | null = null;
  public onerror: ((e: unknown) => void) | null = null;
  public sentMessages: string[] = [];
  public readonly CONNECTING = 0;
  public readonly OPEN = 1;
  public readyState = this.CONNECTING;

  constructor(public readonly url: string) {
    StubSocket.instances.push(this);
    queueMicrotask(() => {
      this.readyState = this.OPEN;
      this.onopen?.();
    });
  }

  send(s: string): void {
    this.sentMessages.push(s);
  }

  close(): void {
    this.readyState = 3;
    this.onclose?.();
  }

  // Test helper: simulate the server pushing a frame.
  pushFromServer(obj: unknown): void {
    this.onmessage?.({ data: JSON.stringify(obj) });
  }
}

beforeEach(() => {
  StubSocket.instances.length = 0;
  (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket =
    StubSocket as unknown as typeof WebSocket;
});

describe("RpcClient", () => {
  it("connects and resolves when the stub opens", async () => {
    const c = new RpcClient("ws://stub/wcp/ws");
    await c.connect();
    expect(StubSocket.instances.length).toBe(1);
  });

  it("serializes call() as JSON-RPC 2.0 with monotonic ids", async () => {
    const c = new RpcClient("ws://stub/wcp/ws");
    await c.connect();
    const ws = StubSocket.instances[0];

    // Fire two calls; immediately resolve them with stub server frames.
    const p1 = c.call("capabilities/list", { worker_id: "did:wcp:w1" });
    const p2 = c.call("tasks/post", { task: {}, expiry: "2099-01-01T00:00:00Z" });

    // Verify the sent frames are well-formed JSON-RPC.
    expect(ws.sentMessages.length).toBe(2);
    const req1 = JSON.parse(ws.sentMessages[0]);
    expect(req1.jsonrpc).toBe("2.0");
    expect(req1.method).toBe("capabilities/list");
    expect(req1.params).toEqual({ worker_id: "did:wcp:w1" });
    expect(typeof req1.id).toBe("number");

    const req2 = JSON.parse(ws.sentMessages[1]);
    expect(req2.id).toBe(req1.id + 1);

    // Resolve from the stub server.
    ws.pushFromServer({ jsonrpc: "2.0", id: req1.id, result: { worker_id: "did:wcp:w1" } });
    ws.pushFromServer({ jsonrpc: "2.0", id: req2.id, result: { task_id: "t1" } });

    const r1 = await p1;
    const r2 = await p2;
    expect(r1).toEqual({ worker_id: "did:wcp:w1" });
    expect(r2).toEqual({ task_id: "t1" });
  });

  it("rejects with WcpRpcError on JSON-RPC error frames", async () => {
    const c = new RpcClient("ws://stub/wcp/ws");
    await c.connect();
    const ws = StubSocket.instances[0];
    const p = c.call("capabilities/list", { worker_id: "did:wcp:unknown" });
    const sentReq = JSON.parse(ws.sentMessages[0]);
    ws.pushFromServer({
      jsonrpc: "2.0",
      id: sentReq.id,
      error: { code: -40003, message: "DID_NOT_RESOLVED" },
    });
    await expect(p).rejects.toBeInstanceOf(WcpRpcError);
    await expect(p).rejects.toMatchObject({ code: -40003 });
  });

  it("propagates the data field on errors and reports retryability", async () => {
    const e = new WcpRpcError(-43001, "HEARTBEAT_TIMEOUT", {
      retry: { retryable: true, class: "transient" },
    });
    expect(e.isRetryable()).toBe(true);
    const e2 = new WcpRpcError(-40001, "UNAUTHENTICATED");
    expect(e2.isRetryable()).toBe(false);
  });

  it("routes server-initiated stream events to the registered handler", async () => {
    const c = new RpcClient("ws://stub/wcp/ws");
    const events: Array<{ event_type: string; payload: unknown }> = [];
    c.onStreamEvent((e) => events.push(e));
    await c.connect();
    const ws = StubSocket.instances[0];
    ws.pushFromServer({ event_type: "heartbeat", payload: { ts: 1 } });
    ws.pushFromServer({ event_type: "task_completed", payload: { claim_id: "c1" } });
    expect(events.length).toBe(2);
    expect(events[0].event_type).toBe("heartbeat");
    expect(events[1].event_type).toBe("task_completed");
  });

  it("ignores response frames with no matching pending id", async () => {
    const c = new RpcClient("ws://stub/wcp/ws");
    await c.connect();
    const ws = StubSocket.instances[0];
    // Should not throw; should not affect anything.
    ws.pushFromServer({ jsonrpc: "2.0", id: 999, result: { stale: true } });
  });
});

describe("WcpRpcError", () => {
  it("carries code, message, and data", () => {
    const e = new WcpRpcError(-12345, "BAD", { foo: "bar" });
    expect(e.code).toBe(-12345);
    expect(e.message).toBe("BAD");
    expect(e.data).toEqual({ foo: "bar" });
    expect(e.name).toBe("WcpRpcError");
  });
});
