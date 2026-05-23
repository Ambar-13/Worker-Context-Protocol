"""
Development convenience wrapper around `wcp_coordinator.router.make_app`.

Provides an ASGI `app` plus `__main__` entry so uvicorn can find it via
`uvicorn wcp_dev_runtime.coordinator_dev_app:app` and the CLI/run.sh scripts can rely
on a single launch path. Uses in-memory SQLite by default.

This module is v1.0-rc2 DX infrastructure layered on top of the v1.0-rc1
coordinator without modifying any v1.0-rc1 file.
"""
from __future__ import annotations

import os
from typing import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from wcp_coordinator.models import Base
from wcp_coordinator.router import make_app


def _build_app():
    database_url = os.environ.get("WCP_DATABASE_URL", "sqlite:///./wcp_coordinator_dev.db")
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def session_factory() -> Session:
        return SessionLocal()

    return make_app(session_factory)


app = _build_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("WCP_HTTP_PORT", os.environ.get("WCP_COORDINATOR_PORT", "8000")))
    uvicorn.run(
        "wcp_dev_runtime.coordinator_dev_app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
