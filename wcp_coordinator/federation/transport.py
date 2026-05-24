"""
Pluggable cross-process transports for federation.

`WsForwarder`   - forwards JSON-RPC calls to a peer over WebSocket
                  using the SDK's RpcClient. Use as the `forwarder=`
                  argument to FederationRouter.

`HttpChainFetcher` - fetches a peer's audit chain segment from the
                  peer coordinator's HTTP federation endpoint. Use
                  as the `fetcher=` argument to AuditExport.

The in-process demo.py uses in-memory stubs for both. Production
two-host deployments wire the WebSocket / HTTPS transports below.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse


class WsForwarder:
    """Async (peer_url, method, params) -> result_dict forwarder.

    Opens a fresh WebSocket connection per call. Production deployments
    pool connections; the reference implementation prioritises simplicity.
    """

    def __init__(self, timeout_s: float = 5.0) -> None:
        self._timeout_s = timeout_s

    async def __call__(
        self, peer_url: str, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        # Lazy import so the federation module is importable without
        # the optional websockets dep installed.
        import websockets

        async with websockets.connect(peer_url) as ws:
            req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            await ws.send(json.dumps(req))
            raw = await asyncio.wait_for(ws.recv(), timeout=self._timeout_s)
            resp = json.loads(raw)
            if "error" in resp:
                raise RuntimeError(
                    f"peer error {resp['error'].get('code')}: "
                    f"{resp['error'].get('message')}"
                )
            return resp.get("result") or {}


class HttpChainFetcher:
    """Async (peer_url, claim_id) -> list[dict] audit-chain fetcher.

    Talks to the peer's `/wcp/federation/audit_chain/{claim_id}`
    endpoint. The peer URL may be a WSS URL (we rewrite to HTTPS) or
    an HTTPS URL directly.
    """

    def __init__(self, timeout_s: float = 5.0) -> None:
        self._timeout_s = timeout_s

    async def __call__(
        self, peer_url: str, claim_id: str
    ) -> list[dict[str, Any]]:
        import urllib.request

        http_url = self._to_http(peer_url) + f"/wcp/federation/audit_chain/{claim_id}"
        # urllib.request is synchronous; we offload to a thread so we
        # don't block the event loop.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync, http_url)

    def _fetch_sync(self, url: str) -> list[dict[str, Any]]:
        import urllib.request

        with urllib.request.urlopen(url, timeout=self._timeout_s) as resp:
            data = resp.read().decode("utf-8")
        body = json.loads(data)
        return body.get("entries") or []

    @staticmethod
    def _to_http(url: str) -> str:
        """ws://host:port/anything -> http://host:port  (drops the /wcp/ws path)."""
        p = urlparse(url)
        scheme = {"ws": "http", "wss": "https"}.get(p.scheme, p.scheme)
        netloc = p.netloc or p.path  # support "ws://h:p" form
        # Strip a trailing /wcp/ws if present so callers can pass the
        # WS endpoint URL verbatim from the trust anchor.
        return f"{scheme}://{netloc}"
