"""
JSON-RPC 2.0 client over WebSocket and HTTPS.

Async-first. WebSocket connection management with exponential-backoff reconnect.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

import websockets

log = logging.getLogger("wcp_sdk.rpc_client")


class WcpRpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def is_retryable(self) -> bool:
        if not isinstance(self.data, dict):
            return False
        retry = self.data.get("retry")
        if not isinstance(retry, dict):
            return False
        return bool(retry.get("retryable", False))


@dataclass(frozen=True)
class JsonRpcResponse:
    id: Any
    result: Any | None
    error: WcpRpcError | None


StreamHandler = Callable[[dict[str, Any]], Awaitable[None]]


class RpcClient:
    """Async JSON-RPC 2.0 client.

    Supports WebSocket transport with reconnect or HTTPS POST transport.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self._socket: Optional[websockets.WebSocketClientProtocol] = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._reader_task: Optional[asyncio.Task[None]] = None
        self._stream_handler: Optional[StreamHandler] = None
        self._closed = False
        self._connect_lock = asyncio.Lock()

    def on_stream_event(self, handler: StreamHandler) -> None:
        self._stream_handler = handler

    async def connect(self) -> None:
        async with self._connect_lock:
            if self._socket is not None:
                return
            attempt = 0
            while not self._closed:
                try:
                    self._socket = await websockets.connect(
                        self.url, ping_interval=20, ping_timeout=10
                    )
                    self._reader_task = asyncio.create_task(self._reader_loop())
                    return
                except Exception as exc:
                    log.warning("rpc connect failed attempt=%d: %s", attempt, exc)
                    attempt += 1
                    delay = min(30.0, 0.5 * (2**attempt) + random.random() * 0.25)
                    await asyncio.sleep(delay)

    async def _reader_loop(self) -> None:
        assert self._socket is not None
        try:
            async for raw in self._socket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict) and "event_type" in data:
                    if self._stream_handler is not None:
                        await self._stream_handler(data)
                    continue
                req_id = data.get("id")
                fut = self._pending.pop(int(req_id), None) if req_id is not None else None
                if fut is None:
                    continue
                if "error" in data:
                    err = data["error"]
                    fut.set_exception(
                        WcpRpcError(
                            err.get("code", -32603),
                            err.get("message", ""),
                            err.get("data"),
                        )
                    )
                else:
                    fut.set_result(data.get("result"))
        except websockets.ConnectionClosed:
            pass

    async def call(
        self, method: str, params: Optional[dict[str, Any]] = None
    ) -> Any:
        if self._socket is None:
            await self.connect()
        assert self._socket is not None
        req_id = self._next_id
        self._next_id += 1
        fut: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        await self._socket.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "method": method,
                    "params": params or {},
                }
            )
        )
        return await fut

    async def close(self) -> None:
        self._closed = True
        if self._reader_task is not None:
            self._reader_task.cancel()
        if self._socket is not None:
            await self._socket.close()
        self._socket = None
