"""WCP public coordinator registry: FastAPI application.

Read-and-write registry that indexes coordinator descriptors. Inclusion
in this registry confers NO trust. See README.md.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Coordinator
from .schemas import (
    CoordinatorDescriptor,
    CoordinatorListResponse,
    ErrorResponse,
)
from .verify import verify_descriptor_signature

logger = logging.getLogger(__name__)

DB_URL = os.environ.get(
    "REGISTRY_DB_URL", "postgresql://wcp@localhost:5432/wcp_registry"
)
engine = create_engine(DB_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="WCP Public Coordinator Registry",
    version="v1.0-rc4",
    description=(
        "Read-and-write registry of WCP coordinators. Inclusion confers "
        "no trust; agents must independently verify trust anchors per "
        "RFC 0016."
    ),
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}


@app.get(
    "/coordinators",
    response_model=CoordinatorListResponse,
)
def list_coordinators(
    country: Optional[str] = Query(None, regex="^[A-Z]{2}$"),
    descriptor_type: Optional[str] = Query(None),
    worker_class: Optional[str] = Query(None),
    min_conformance: int = Query(1, ge=1, le=3),
    db: Session = Depends(get_db),
) -> CoordinatorListResponse:
    """List coordinators with optional filters."""
    rows = db.scalars(select(Coordinator)).all()
    coords: list[CoordinatorDescriptor] = []
    for r in rows:
        if r.conformance_level < min_conformance:
            continue
        if country is not None and r.operator_country != country:
            continue
        desc = r.descriptor_json
        if descriptor_type is not None:
            if descriptor_type not in desc.get(
                "descriptor_types_accepted", []
            ):
                continue
        if worker_class is not None:
            if worker_class not in desc.get(
                "worker_classes_accepted", []
            ):
                continue
        coords.append(CoordinatorDescriptor(**desc))
    return CoordinatorListResponse(coordinators=coords, total=len(coords))


@app.get(
    "/coordinators/{did}",
    response_model=CoordinatorDescriptor,
    responses={404: {"model": ErrorResponse}},
)
def get_coordinator(
    did: str,
    db: Session = Depends(get_db),
) -> CoordinatorDescriptor:
    row = db.get(Coordinator, did)
    if row is None:
        raise HTTPException(status_code=404, detail="coordinator not found")
    return CoordinatorDescriptor(**row.descriptor_json)


@app.post(
    "/coordinators",
    response_model=CoordinatorDescriptor,
    status_code=201,
    responses={400: {"model": ErrorResponse}},
)
def register_coordinator(
    descriptor: CoordinatorDescriptor,
    db: Session = Depends(get_db),
) -> CoordinatorDescriptor:
    """Register or update a coordinator descriptor.

    The descriptor MUST be signed by the key in `public_key_multibase`.
    The signature is verified before persistence.
    """
    raw = descriptor.model_dump(mode="json")
    if not verify_descriptor_signature(raw):
        raise HTTPException(
            status_code=400, detail="signature verification failed"
        )
    existing = db.get(Coordinator, descriptor.did)
    if existing is None:
        row = Coordinator(
            did=descriptor.did,
            endpoint=descriptor.endpoint,
            operator=descriptor.operator,
            operator_country=descriptor.operator_country,
            conformance_level=descriptor.conformance_level,
            descriptor_json=raw,
            public_key_multibase=descriptor.public_key_multibase,
            signed_at=descriptor.signed_at,
        )
        db.add(row)
    else:
        # Reject downgrade of public key on update: the existing entry's
        # key must match the new submission's key (rotation goes through
        # a separate DELETE + re-register flow).
        if existing.public_key_multibase != descriptor.public_key_multibase:
            raise HTTPException(
                status_code=400,
                detail=(
                    "public_key_multibase change on update is forbidden; "
                    "delete the entry and re-register"
                ),
            )
        existing.endpoint = descriptor.endpoint
        existing.operator = descriptor.operator
        existing.operator_country = descriptor.operator_country
        existing.conformance_level = descriptor.conformance_level
        existing.descriptor_json = raw
        existing.signed_at = descriptor.signed_at
    db.commit()
    return descriptor


@app.delete(
    "/coordinators/{did}",
    status_code=204,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_coordinator(
    did: str,
    descriptor: CoordinatorDescriptor,
    db: Session = Depends(get_db),
) -> None:
    """Remove a coordinator descriptor.

    Requires a signed delete request (descriptor with same DID and key).
    """
    if descriptor.did != did:
        raise HTTPException(
            status_code=400,
            detail="path DID does not match descriptor DID",
        )
    raw = descriptor.model_dump(mode="json")
    if not verify_descriptor_signature(raw):
        raise HTTPException(
            status_code=400, detail="signature verification failed"
        )
    row = db.get(Coordinator, did)
    if row is None:
        raise HTTPException(status_code=404, detail="coordinator not found")
    if row.public_key_multibase != descriptor.public_key_multibase:
        raise HTTPException(
            status_code=400,
            detail="public_key_multibase mismatch with stored descriptor",
        )
    db.delete(row)
    db.commit()
    return None


@app.get("/", response_class=HTMLResponse)
def browse_index(db: Session = Depends(get_db)) -> str:
    rows = db.scalars(select(Coordinator)).all()
    items = [
        {
            "did": r.did,
            "endpoint": r.endpoint,
            "operator": r.operator,
            "country": r.operator_country,
            "level": r.conformance_level,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]
    return templates.get_template("index.html").render(
        items=items, now=datetime.now(timezone.utc).isoformat()
    )
