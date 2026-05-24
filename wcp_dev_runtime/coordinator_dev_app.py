"""
Development convenience wrapper around `wcp_coordinator.router.make_app`.

Provides an ASGI `app` plus `__main__` entry so uvicorn can find it via
`uvicorn wcp_dev_runtime.coordinator_dev_app:app` and the CLI/run.sh
scripts can rely on a single launch path. Uses in-memory SQLite by
default.

Federation env vars (read at startup; absent = single-coordinator mode):
  WCP_COORDINATOR_NAME    label for log lines and the in-memory store
  WCP_COORDINATOR_DID     this coordinator's DID
  WCP_FEDERATION_PEER_NAME peer label for log lines
  WCP_FEDERATION_PEER_URL  WebSocket URL of the peer coordinator
  WCP_DATABASE_URL         SQLAlchemy URL (default: SQLite file)

When WCP_FEDERATION_PEER_URL is set, the dev runtime logs a federation
banner on startup. The actual trust-anchor exchange and forwarding are
exercised by examples/federation-demo/demo.py (in-process two-coord
script). The Docker variant in examples/federation-demo/docker-compose.yml
brings up two cross-process coordinators, each reading these env vars.

This module is developer-experience infrastructure layered on top of
the reference coordinator without modifying any coordinator file.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from wcp_coordinator.models import Base
from wcp_coordinator.router import make_app

log = logging.getLogger("wcp.dev")


def _log_federation_config() -> None:
    peer_url = os.environ.get("WCP_FEDERATION_PEER_URL")
    if not peer_url:
        return
    name = os.environ.get("WCP_COORDINATOR_NAME", "coord")
    coord_did = os.environ.get("WCP_COORDINATOR_DID", "(unset)")
    peer_name = os.environ.get("WCP_FEDERATION_PEER_NAME", "peer")
    # Print to stderr so uvicorn's default log capture surfaces this on
    # startup; also send through the logging system in case stderr is
    # being redirected.
    msg = (
        f"[{name}] federation configured: did={coord_did} peer={peer_name} "
        f"peer_url={peer_url} (audit_chain export endpoint live at "
        f"/wcp/federation/audit_chain/<claim_id>)"
    )
    import sys
    print(msg, file=sys.stderr, flush=True)
    log.info(msg)


def _build_app():
    database_url = os.environ.get(
        "WCP_DATABASE_URL", "sqlite:///./wcp_coordinator_dev.db"
    )
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def session_factory() -> Session:
        return SessionLocal()

    _log_federation_config()
    return make_app(session_factory)


app = _build_app()


if __name__ == "__main__":
    import uvicorn

    port = int(
        os.environ.get(
            "WCP_HTTP_PORT", os.environ.get("WCP_COORDINATOR_PORT", "8000")
        )
    )
    uvicorn.run(
        "wcp_dev_runtime.coordinator_dev_app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
