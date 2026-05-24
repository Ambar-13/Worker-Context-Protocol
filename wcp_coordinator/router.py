"""
FastAPI router exposing the WCP JSON-RPC endpoint plus a WebSocket upgrade.

POST /wcp/rpc                  -> JSON-RPC 2.0 single request/response
WebSocket /wcp/ws              -> long-lived bidirectional JSON-RPC stream
GET /wcp/health                -> liveness check
GET /.well-known/did-wcp/{id}  -> optional DID document publication (stub)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .audit_chain import AuditChain, AuditSigner
from .capabilities_service import CapabilitiesService
from .did_resolver import DidResolver
from .rpc_dispatch import Dispatcher, JsonRpcError
from .tasks_service import TasksService

log = logging.getLogger("wcp.router")


def make_app(
    session_factory: Callable[[], Session],
    *,
    signer: AuditSigner | None = None,
) -> FastAPI:
    """Construct a FastAPI app with WCP routes bound to the given session factory.

    v0.955: the ``settlement`` parameter is removed; settlement is no longer a
    protocol concern. The reference coordinator no longer ships an escrow
    adapter. External settlement layers subscribe to the audit chain.
    """
    app = FastAPI(
        title="WCP Coordinator",
        version="0.955.0",
        description="Worker Context Protocol reference backend",
    )
    router = APIRouter(prefix="/wcp")
    signer = signer or AuditSigner.ephemeral()
    resolver = DidResolver()

    def _build_dispatcher(db: Session) -> Dispatcher:
        audit = AuditChain(db, signer)
        caps = CapabilitiesService(db, resolver)
        tasks = TasksService(db, resolver, audit)
        return Dispatcher(caps, tasks)

    def _get_session() -> Session:
        s = session_factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "schema_version": "wcp/0.2"}

    @router.post("/rpc")
    def rpc(payload: dict, db: Session = Depends(_get_session)) -> JSONResponse:
        # Minimal JSON-RPC 2.0 envelope handling. Spec/0.1.md section 2 +
        # error codes section 11.
        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}
        if payload.get("jsonrpc") != "2.0" or not isinstance(method, str):
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32600, "message": "Invalid Request"},
                },
                status_code=400,
            )
        dispatcher = _build_dispatcher(db)
        try:
            result = dispatcher.dispatch(method, params)
            return JSONResponse(
                content={"jsonrpc": "2.0", "id": req_id, "result": result}
            )
        except JsonRpcError as exc:
            return JSONResponse(
                content={"jsonrpc": "2.0", "id": req_id, "error": exc.to_dict()},
                status_code=200,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("internal error during dispatch")
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": f"Internal error: {exc}"},
                },
                status_code=500,
            )

    @router.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    req = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": None,
                                "error": {"code": -32700, "message": "Parse error"},
                            }
                        )
                    )
                    continue
                req_id = req.get("id")
                method = req.get("method")
                params = req.get("params") or {}
                db = session_factory()
                try:
                    dispatcher = _build_dispatcher(db)
                    try:
                        result = dispatcher.dispatch(method, params)
                        db.commit()
                        await websocket.send_text(
                            json.dumps(
                                {"jsonrpc": "2.0", "id": req_id, "result": result}
                            )
                        )
                    except JsonRpcError as exc:
                        db.rollback()
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "error": exc.to_dict(),
                                }
                            )
                        )
                finally:
                    db.close()
        except Exception:
            await websocket.close()

    @router.get("/.well-known/did-wcp/{identifier}")
    def did_doc(identifier: str) -> dict[str, Any]:
        # Stub: production coordinator publishes a DID document here.
        return {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": f"did:wcp:{identifier}",
            "verificationMethod": [],
            "service": [
                {
                    "id": "#wcp-coordinator",
                    "type": "WcpCoordinator",
                    "serviceEndpoint": "ws://localhost/wcp/ws",
                }
            ],
        }

    app.include_router(router)
    return app
