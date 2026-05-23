import { afterEach, describe, expect, it, vi } from "vitest";

import { WcpRpcClient, WcpRpcError } from "../rpc-client";

class MockResponse {
  constructor(private readonly body: unknown) {}
  async json(): Promise<unknown> {
    return this.body;
  }
}

describe("WcpRpcClient (https mode)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("posts JSON-RPC requests and returns result", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new MockResponse({
          jsonrpc: "2.0",
          id: 1,
          result: { task_id: "t-1", eligible_workers_count: 3, posted_at: "now" },
        }),
      ) as unknown as typeof fetch;
    const client = new WcpRpcClient({
      url: "https://test/wcp/rpc",
      mode: "https",
      fetch: fetchMock,
    });
    const result = await client.call<{ task_id: string }>("tasks/post", {
      task: { task_id: "t-1" },
      bond_ref: "pi_x",
      expiry: "2026-12-31T00:00:00Z",
    });
    expect(result.task_id).toBe("t-1");
  });

  it("throws WcpRpcError on JSON-RPC error", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new MockResponse({
        jsonrpc: "2.0",
        id: 1,
        error: { code: -45001, message: "SUBCONTRACT_FORBIDDEN" },
      }),
    ) as unknown as typeof fetch;
    const client = new WcpRpcClient({
      url: "https://test/wcp/rpc",
      mode: "https",
      fetch: fetchMock,
    });
    await expect(client.call("tasks/post", {})).rejects.toMatchObject({
      code: -45001,
    });
  });
});
