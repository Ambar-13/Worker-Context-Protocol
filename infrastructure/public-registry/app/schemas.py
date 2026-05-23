"""Pydantic schemas for the registry API."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


_DID_RE = re.compile(r"^did:wcp:[A-Za-z0-9._-]+$")
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
_JURISDICTION_RE = re.compile(r"^[A-Z]{2}(-[A-Z0-9]{1,3})?$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_WS_RE = re.compile(r"^wss?://")


class CoordinatorDescriptor(BaseModel):
    """The descriptor a coordinator publishes to the registry."""

    schema_version: str = Field("wcp/1.0-rc1")
    did: str
    endpoint: str
    operator: str
    operator_country: str
    operator_legal_form: Optional[str] = None
    jurisdictions_served: list[str]
    descriptor_types_accepted: list[str]
    worker_classes_accepted: list[str]
    conformance_level: int
    conformance_attestation_url: Optional[str] = None
    settlement_currencies: list[str] = Field(default_factory=list)
    federation_peers: list[str] = Field(default_factory=list)
    public_key_multibase: str
    signed_at: datetime
    signature: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("did")
    @classmethod
    def _did_shape(cls, v: str) -> str:
        if not _DID_RE.match(v):
            raise ValueError("did must match ^did:wcp:[A-Za-z0-9._-]+$")
        return v

    @field_validator("endpoint")
    @classmethod
    def _endpoint_shape(cls, v: str) -> str:
        if not _WS_RE.match(v):
            raise ValueError("endpoint must start with ws:// or wss://")
        return v

    @field_validator("operator_country")
    @classmethod
    def _country_shape(cls, v: str) -> str:
        if not _COUNTRY_RE.match(v):
            raise ValueError("operator_country must be ISO 3166-1 alpha-2")
        return v

    @field_validator("jurisdictions_served")
    @classmethod
    def _juris(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("jurisdictions_served must be non-empty")
        for j in v:
            if not _JURISDICTION_RE.match(j):
                raise ValueError(f"invalid jurisdiction {j!r}")
        return v

    @field_validator("conformance_level")
    @classmethod
    def _level(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError("conformance_level must be 1, 2, or 3")
        return v

    @field_validator("settlement_currencies")
    @classmethod
    def _currencies(cls, v: list[str]) -> list[str]:
        for c in v:
            if not _CURRENCY_RE.match(c):
                raise ValueError(f"invalid currency code {c!r}")
        return v

    @field_validator("federation_peers")
    @classmethod
    def _peers(cls, v: list[str]) -> list[str]:
        for p in v:
            if not _DID_RE.match(p):
                raise ValueError(f"invalid federation peer DID {p!r}")
        return v

    @field_validator("worker_classes_accepted")
    @classmethod
    def _wc(cls, v: list[str]) -> list[str]:
        allowed = {
            "human",
            "autonomous_robot",
            "teleoperated_system",
            "hybrid_human_robot",
        }
        for c in v:
            if c not in allowed:
                raise ValueError(f"unknown worker_class {c!r}")
        return v


class CoordinatorListResponse(BaseModel):
    coordinators: list[CoordinatorDescriptor]
    total: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
