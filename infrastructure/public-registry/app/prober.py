"""Optional liveness prober for the public registry.

Periodically opens a WebSocket to each registered coordinator and
records the result in `last_seen_alive_at`. Stale entries (no successful
probe in N days) are flagged in the UI but NOT auto-removed; removal
requires a signed delete request from the operator.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Coordinator

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_S = 10.0
PROBE_INTERVAL_S = 600.0  # 10 minutes


async def probe_one(endpoint: str) -> bool:
    """Attempt a brief WebSocket handshake to the coordinator.

    Returns True if a connection succeeded, False otherwise.
    """
    try:
        import websockets
    except ImportError:
        logger.warning("websockets not installed; prober is a no-op")
        return False
    try:
        async with asyncio.timeout(PROBE_TIMEOUT_S):
            async with websockets.connect(endpoint) as ws:
                # Send a no-op JSON-RPC ping; coordinator either responds
                # or rejects. Either way the TCP+TLS handshake completed.
                await ws.send('{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}')
                try:
                    await ws.recv()
                except Exception:
                    pass
                return True
    except Exception as e:
        logger.debug("probe of %s failed: %s", endpoint, e)
        return False


async def probe_loop(session_factory) -> None:
    """Background loop: probe every coordinator on a fixed interval."""
    while True:
        db: Session = session_factory()
        try:
            rows = db.scalars(select(Coordinator)).all()
            for r in rows:
                ok = await probe_one(r.endpoint)
                if ok:
                    r.last_seen_alive_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        await asyncio.sleep(PROBE_INTERVAL_S)
