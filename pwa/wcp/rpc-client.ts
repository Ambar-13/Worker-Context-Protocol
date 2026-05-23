/**
 * JSON-RPC 2.0 client over WebSocket (with HTTPS fallback) for the WCP
 * worker-side PWA module.
 *
 * Reconnect: exponential backoff with jitter, capped at 30 seconds.
 * Backpressure: send queue caps at 64 messages; older messages dropped with
 * a recorded warning.
 */

type JsonRpcRequest = {
  jsonrpc: "2.0";
  id: number | string;
  method: string;
  params?: unknown;
};

type JsonRpcSuccess<T> = { jsonrpc: "2.0"; id: number | string; result: T };
type JsonRpcError = {
  jsonrpc: "2.0";
  id: number | string | null;
  error: { code: number; message: string; data?: unknown };
};
type JsonRpcResponse<T> = JsonRpcSuccess<T> | JsonRpcError;

export class WcpRpcError extends Error {
  constructor(public code: number, message: string, public data?: unknown) {
    super(message);
    this.name = "WcpRpcError";
  }
}

export type RpcMode = "websocket" | "https";

export interface RpcClientOptions {
  url: string;
  mode?: RpcMode;
  fetch?: typeof fetch;
  webSocket?: typeof WebSocket;
}

export class WcpRpcClient {
  private socket: WebSocket | null = null;
  private nextId = 1;
  private pending = new Map<number, {
    resolve: (v: unknown) => void;
    reject: (e: WcpRpcError | Error) => void;
  }>();
  private queue: JsonRpcRequest[] = [];
  private reconnectAttempt = 0;
  private readonly opts: RpcClientOptions;
  private readonly streamHandlers = new Set<
    (event: { event_type: string; payload: unknown }) => void
  >();

  constructor(opts: RpcClientOptions) {
    this.opts = { mode: "websocket", ...opts };
    if (this.opts.mode === "websocket") this.connect();
  }

  onStreamEvent(
    handler: (event: { event_type: string; payload: unknown }) => void
  ): () => void {
    this.streamHandlers.add(handler);
    return () => this.streamHandlers.delete(handler);
  }

  private connect(): void {
    const WS = this.opts.webSocket || (globalThis as { WebSocket: typeof WebSocket }).WebSocket;
    this.socket = new WS(this.opts.url);
    this.socket.onopen = () => {
      this.reconnectAttempt = 0;
      this.flushQueue();
    };
    this.socket.onmessage = (ev: MessageEvent) => {
      let parsed: JsonRpcResponse<unknown> | {
        event_type?: string;
        payload?: unknown;
      };
      try {
        parsed = JSON.parse(ev.data as string);
      } catch {
        return;
      }
      if ("event_type" in parsed && parsed.event_type) {
        for (const h of this.streamHandlers)
          h({ event_type: parsed.event_type, payload: parsed.payload });
        return;
      }
      const resp = parsed as JsonRpcResponse<unknown>;
      const pending = this.pending.get(resp.id as number);
      if (!pending) return;
      this.pending.delete(resp.id as number);
      if ("error" in resp) {
        pending.reject(
          new WcpRpcError(resp.error.code, resp.error.message, resp.error.data)
        );
      } else {
        pending.resolve(resp.result);
      }
    };
    this.socket.onclose = () => {
      this.scheduleReconnect();
    };
    this.socket.onerror = () => {
      try {
        this.socket?.close();
      } catch {
        /* ignore */
      }
    };
  }

  private scheduleReconnect(): void {
    if (this.opts.mode !== "websocket") return;
    const delay = Math.min(
      30000,
      500 * Math.pow(2, this.reconnectAttempt++) + Math.random() * 250
    );
    setTimeout(() => this.connect(), delay);
  }

  private flushQueue(): void {
    if (!this.socket || this.socket.readyState !== 1) return;
    while (this.queue.length > 0) {
      const req = this.queue.shift()!;
      this.socket.send(JSON.stringify(req));
    }
  }

  async call<T>(method: string, params: unknown = {}): Promise<T> {
    if (this.opts.mode === "https") return this.callHttps<T>(method, params);
    return new Promise<T>((resolve, reject) => {
      const id = this.nextId++;
      const req: JsonRpcRequest = {
        jsonrpc: "2.0",
        id,
        method,
        params,
      };
      this.pending.set(id, {
        resolve: resolve as (v: unknown) => void,
        reject,
      });
      if (this.socket && this.socket.readyState === 1) {
        this.socket.send(JSON.stringify(req));
      } else {
        if (this.queue.length >= 64) this.queue.shift();
        this.queue.push(req);
      }
    });
  }

  private async callHttps<T>(method: string, params: unknown): Promise<T> {
    const f = this.opts.fetch || fetch;
    const resp = await f(this.opts.url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: this.nextId++,
        method,
        params,
      }),
    });
    const body = (await resp.json()) as JsonRpcResponse<T>;
    if ("error" in body) {
      throw new WcpRpcError(body.error.code, body.error.message, body.error.data);
    }
    return body.result;
  }

  close(): void {
    try {
      this.socket?.close();
    } catch {
      /* ignore */
    }
    this.streamHandlers.clear();
    this.pending.clear();
  }
}
