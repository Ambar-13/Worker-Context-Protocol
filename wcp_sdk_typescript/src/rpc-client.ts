/**
 * JSON-RPC 2.0 client over WebSocket with exponential-backoff reconnect.
 */

export class WcpRpcError extends Error {
  constructor(public code: number, message: string, public data?: unknown) {
    super(message);
    this.name = "WcpRpcError";
  }
  isRetryable(): boolean {
    const d = this.data as { retry?: { retryable?: boolean } } | undefined;
    return !!d?.retry?.retryable;
  }
}

type Pending = {
  resolve: (v: unknown) => void;
  reject: (e: Error) => void;
};

export class RpcClient {
  private socket: WebSocket | null = null;
  private nextId = 1;
  private pending = new Map<number, Pending>();
  private queue: string[] = [];
  private reconnectAttempt = 0;
  private streamHandler?: (event: { event_type: string; payload: unknown }) => void;
  private closed = false;

  constructor(public readonly url: string) {}

  onStreamEvent(h: (event: { event_type: string; payload: unknown }) => void): void {
    this.streamHandler = h;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const WS: typeof WebSocket =
        (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket;
      this.socket = new WS(this.url);
      this.socket.onopen = () => {
        this.reconnectAttempt = 0;
        this.flushQueue();
        resolve();
      };
      this.socket.onerror = (e) => reject(new Error("ws error: " + String(e)));
      this.socket.onmessage = (ev: MessageEvent) => this.handleMessage(ev);
      this.socket.onclose = () => {
        this.socket = null;
        if (!this.closed) this.scheduleReconnect();
      };
    });
  }

  private handleMessage(ev: MessageEvent): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(String(ev.data));
    } catch {
      return;
    }
    const obj = parsed as Record<string, unknown>;
    if ("event_type" in obj && this.streamHandler) {
      this.streamHandler({
        event_type: String(obj.event_type),
        payload: obj.payload,
      });
      return;
    }
    const id = obj.id as number | undefined;
    if (id === undefined) return;
    const p = this.pending.get(id);
    if (!p) return;
    this.pending.delete(id);
    if ("error" in obj) {
      const e = obj.error as { code: number; message: string; data?: unknown };
      p.reject(new WcpRpcError(e.code, e.message, e.data));
    } else {
      p.resolve(obj.result);
    }
  }

  private scheduleReconnect(): void {
    const delay = Math.min(
      30_000,
      500 * Math.pow(2, this.reconnectAttempt++) + Math.random() * 250,
    );
    setTimeout(() => {
      if (!this.closed) this.connect().catch(() => undefined);
    }, delay);
  }

  private flushQueue(): void {
    if (!this.socket || this.socket.readyState !== 1) return;
    while (this.queue.length > 0) {
      const msg = this.queue.shift()!;
      this.socket.send(msg);
    }
  }

  call<T = unknown>(method: string, params: unknown = {}): Promise<T> {
    const id = this.nextId++;
    const msg = JSON.stringify({ jsonrpc: "2.0", id, method, params });
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, {
        resolve: resolve as (v: unknown) => void,
        reject,
      });
      if (this.socket && this.socket.readyState === 1) {
        this.socket.send(msg);
      } else {
        if (this.queue.length >= 64) this.queue.shift();
        this.queue.push(msg);
      }
    });
  }

  close(): void {
    this.closed = true;
    try {
      this.socket?.close();
    } catch {
      // ignore
    }
    this.pending.clear();
  }
}
