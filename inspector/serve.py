"""WCP visual inspector: serves a single-page UI on http://localhost:8765.

The page is HTML + Alpine.js (no build step) and connects via WebSocket to a
small relay that proxies the coordinator's audit chain and task state to the
browser. The relay queries the coordinator's HTTP endpoints; it does not
require any modification to the v1.0-rc1 coordinator.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
import httpx
import uvicorn

HERE = Path(__file__).resolve().parent
INDEX_HTML = HERE / "index.html"


def make_app(coordinator_ws: str) -> FastAPI:
    app = FastAPI(title="WCP Inspector", docs_url=None, redoc_url=None)

    coordinator_http = coordinator_ws.replace("ws://", "http://").replace(
        "wss://", "https://"
    )
    if "/wcp/ws" in coordinator_http:
        coordinator_http = coordinator_http.replace("/wcp/ws", "")
    elif "/wcp" in coordinator_http:
        coordinator_http = coordinator_http.split("/wcp")[0]

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(INDEX_HTML)

    @app.get("/api/health")
    async def health() -> JSONResponse:
        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                r = await client.get(f"{coordinator_http}/wcp/health")
                return JSONResponse({"coordinator": r.json(), "inspector": "ok"})
            except Exception as exc:
                return JSONResponse(
                    {"coordinator": None, "inspector": "ok", "error": str(exc)},
                    status_code=200,
                )

    @app.websocket("/ws")
    async def relay(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                # Poll the coordinator for tail events; emit periodic snapshots.
                snapshot = await _snapshot(coordinator_http)
                await ws.send_text(json.dumps(snapshot))
                await asyncio.sleep(1.5)
        except WebSocketDisconnect:
            return
        except Exception:
            try:
                await ws.close()
            except Exception:
                pass

    @app.get("/api/coordinator-url")
    def coordinator_url() -> JSONResponse:
        return JSONResponse(
            {"ws": coordinator_ws, "http": coordinator_http}
        )

    return app


async def _snapshot(coordinator_http: str) -> dict[str, Any]:
    """Build a minimal dashboard snapshot.

    The v1.0-rc1 coordinator exposes /wcp/health. Production inspectors will
    add /wcp/admin/* endpoints (RFC tracked); for v1.0-rc2 we render a
    health probe plus a notice that admin endpoints land in a v1.1 RFC.
    """
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            r = await client.get(f"{coordinator_http}/wcp/health")
            health = r.json()
        except Exception as exc:
            health = {"status": "unreachable", "error": str(exc)}
    return {
        "timestamp": _now_iso(),
        "health": health,
        "panels": {
            "active_tasks": [],
            "audit_chain_tail": [],
            "rpc_traffic": [],
            "capability_subscriptions": [],
        },
        "note": (
            "WCP coordinators expose /wcp/health at v1.0-rc1. The full set of "
            "/wcp/admin/* introspection endpoints (active tasks, audit chain "
            "tail, live RPC traffic) is tracked in an upcoming RFC. The "
            "inspector renders what the coordinator exposes; when admin "
            "endpoints ship, additional panels populate automatically."
        ),
    }


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wcp-inspector")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--coordinator", default="ws://localhost:8000/wcp/ws",
        help="Coordinator WebSocket URL",
    )
    args = parser.parse_args(argv)
    app = make_app(args.coordinator)
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
