"""JSON-RPC 2.0 client over WebSocket for the WCP worker plugin.

Asyncio-based; reconnect with exponential backoff and jitter. Single
in-flight method call per outstanding request_id; a small queue buffers
sends during connection establishment.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Awaitable, Callable, Optional

import websockets

log = logging.getLogger("wcp.rpc_client")


class WcpRpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class RpcClient:
    """Single-connection async JSON-RPC 2.0 client."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._socket: Optional[websockets.WebSocketClientProtocol] = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._reader_task: Optional[asyncio.Task[None]] = None
        self._stream_handler: Optional[Callable[[dict[str, Any]], Awaitable[None]]] = None
        self._closed = False

    def on_stream_event(
        self, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        self._stream_handler = handler

    async def connect(self) -> None:
        attempt = 0
        while not self._closed:
            try:
                self._socket = await websockets.connect(
                    self._url,
                    ping_interval=20,
                    ping_timeout=10,
                )
                self._reader_task = asyncio.create_task(self._reader_loop())
                return
            except Exception as exc:
                log.warning("connect failed (attempt %d): %s", attempt, exc)
                attempt += 1
                delay = min(30.0, 0.5 * (2**attempt) + random.random() * 0.25)
                await asyncio.sleep(delay)

    async def _reader_loop(self) -> None:
        assert self._socket is not None
        try:
            async for message in self._socket:
                try:
                    data = json.loads(message)
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
                        WcpRpcError(err.get("code", -32603), err.get("message", ""), err.get("data"))
                    )
                else:
                    fut.set_result(data.get("result"))
        except websockets.ConnectionClosed:
            pass

    async def call(self, method: str, params: Optional[dict[str, Any]] = None) -> Any:
        assert self._socket is not None, "not connected"
        req_id = self._next_id
        self._next_id += 1
        fut: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        await self._socket.send(
            json.dumps(
                {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
            )
        )
        return await fut

    async def close(self) -> None:
        self._closed = True
        if self._reader_task is not None:
            self._reader_task.cancel()
        if self._socket is not None:
            await self._socket.close()
