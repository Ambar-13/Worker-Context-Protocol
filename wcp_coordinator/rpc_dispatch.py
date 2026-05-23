"""
JSON-RPC method dispatch for the WCP coordinator.

Each method is wired to a service method; all errors mapped to spec/0.1.md
Section 11 error codes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .capabilities_service import CapabilitiesService
from .tasks_service import (
    AttestationFailed,
    TaskNotFound,
    TaskPreempted,
    TaskStateInvalid,
    TasksService,
)


@dataclass(frozen=True)
class JsonRpcError(Exception):
    code: int
    message: str
    data: dict | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d


# Spec/0.1.md Section 11 error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

UNAUTHENTICATED = -40001
UNAUTHORIZED = -40002
DID_NOT_RESOLVED = -40003

INVALID_ATTESTATION_REQUIREMENT = -41001
ATTESTATION_FAILED_CODE = -41002

TASK_NOT_FOUND = -42001
TASK_PREEMPTED = -42002
TASK_EXPIRED = -42003
TASK_STATE_INVALID = -42004

HEARTBEAT_TIMEOUT = -43001

SETTLEMENT_FAILED = -44001

SUBCONTRACT_FORBIDDEN = -45001
OUT_OF_SCOPE_TASK_CLASS = -45002

POLICY_VIOLATION = -46001


def _map_value_error(exc: ValueError) -> JsonRpcError:
    msg = str(exc)
    if msg.startswith("DID_NOT_RESOLVED"):
        return JsonRpcError(DID_NOT_RESOLVED, msg)
    if msg.startswith("UNAUTHENTICATED"):
        return JsonRpcError(UNAUTHENTICATED, msg)
    if msg.startswith("UNAUTHORIZED"):
        return JsonRpcError(UNAUTHORIZED, msg)
    if msg.startswith("INVALID_ATTESTATION_REQUIREMENT"):
        return JsonRpcError(INVALID_ATTESTATION_REQUIREMENT, msg)
    if msg.startswith("ATTESTATION_FAILED"):
        return JsonRpcError(ATTESTATION_FAILED_CODE, msg)
    if msg.startswith("SUBCONTRACT_FORBIDDEN"):
        return JsonRpcError(SUBCONTRACT_FORBIDDEN, msg)
    if msg.startswith("OUT_OF_SCOPE_TASK_CLASS"):
        return JsonRpcError(OUT_OF_SCOPE_TASK_CLASS, msg)
    if msg.startswith("POLICY_VIOLATION"):
        return JsonRpcError(POLICY_VIOLATION, msg)
    return JsonRpcError(INVALID_PARAMS, msg)


class Dispatcher:
    """Method router. Translates ValueError into spec error codes."""

    def __init__(
        self, capabilities: CapabilitiesService, tasks: TasksService
    ) -> None:
        self._caps = capabilities
        self._tasks = tasks
        self._methods: dict[str, Callable[..., Any]] = {
            "capabilities/list": self._capabilities_list,
            "capabilities/subscribe": self._capabilities_subscribe,
            "tasks/post": self._tasks_post,
            "tasks/claim": self._tasks_claim,
            "tasks/execute": self._tasks_execute_open,
            "tasks/execute.event": self._tasks_execute_event,
            "tasks/attest": self._tasks_attest,
            "tasks/settle": self._tasks_settle,
            "tasks/supervise": self._tasks_supervise,
            "tasks/abort": self._tasks_abort,
        }

    def dispatch(self, method: str, params: dict | None) -> Any:
        params = params or {}
        if method not in self._methods:
            raise JsonRpcError(METHOD_NOT_FOUND, f"no such method: {method}")
        try:
            return self._methods[method](**params)
        except JsonRpcError:
            raise
        except TaskNotFound as exc:
            raise JsonRpcError(TASK_NOT_FOUND, str(exc)) from exc
        except TaskPreempted as exc:
            raise JsonRpcError(TASK_PREEMPTED, str(exc)) from exc
        except TaskStateInvalid as exc:
            raise JsonRpcError(TASK_STATE_INVALID, str(exc)) from exc
        except AttestationFailed as exc:
            raise JsonRpcError(ATTESTATION_FAILED_CODE, str(exc)) from exc
        except ValueError as exc:
            raise _map_value_error(exc) from exc

    # --- method bodies -------------------------------------------------------

    def _capabilities_list(self, *, worker_id: str) -> dict[str, Any]:
        return self._caps.list_capabilities(worker_id=worker_id)

    def _capabilities_subscribe(
        self,
        *,
        agent_did: str,
        filter: dict | None = None,
        since_revision: int | None = None,
    ) -> dict[str, Any]:
        return self._caps.create_subscription(
            agent_did=agent_did,
            filter_dict=filter,
            since_revision=since_revision,
        )

    def _tasks_post(
        self,
        *,
        task: dict,
        bond_ref: str,
        expiry: str,
        supervision: dict | None = None,
    ) -> dict[str, Any]:
        return self._tasks.post(
            task=task,
            bond_ref=bond_ref,
            expiry=expiry,
            supervision=supervision,
        )

    def _tasks_claim(
        self,
        *,
        task_id: str,
        worker_id: str,
        eta: str,
        acceptance_attestation: dict,
        bid: str | None = None,
    ) -> dict[str, Any]:
        return self._tasks.claim(
            task_id=task_id,
            worker_id=worker_id,
            eta=eta,
            acceptance_attestation=acceptance_attestation,
            bid=bid,
        )

    def _tasks_execute_open(self, *, claim_id: str) -> dict[str, Any]:
        return self._tasks.execute_open(claim_id=claim_id)

    def _tasks_execute_event(
        self,
        *,
        claim_id: str,
        event_type: str,
        timestamp: str,
        payload: dict,
        sig: str,
    ) -> dict[str, Any]:
        return self._tasks.execute_event(
            claim_id=claim_id,
            event_type=event_type,
            timestamp=timestamp,
            payload=payload,
            sig=sig,
        )

    def _tasks_attest(
        self,
        *,
        claim_id: str,
        attestations: list[dict],
        compensating_action: dict | None = None,
    ) -> dict[str, Any]:
        return self._tasks.attest(
            claim_id=claim_id,
            attestations=attestations,
            compensating_action=compensating_action,
        )

    def _tasks_settle(
        self,
        *,
        claim_id: str,
        decision: str,
        amount: str,
        party_breakdown: list[dict],
    ) -> dict[str, Any]:
        return self._tasks.settle(
            claim_id=claim_id,
            decision=decision,
            amount=amount,
            party_breakdown=party_breakdown,
        )

    def _tasks_supervise(
        self,
        *,
        claim_id: str,
        handoff_reason: str,
        state_snapshot: dict,
        urgency: str,
    ) -> dict[str, Any]:
        return self._tasks.supervise(
            claim_id=claim_id,
            handoff_reason=handoff_reason,
            state_snapshot=state_snapshot,
            urgency=urgency,
        )

    def _tasks_abort(
        self,
        *,
        claim_id: str,
        reason: str,
        state_snapshot: dict,
        proposed_settlement: str,
    ) -> dict[str, Any]:
        return self._tasks.abort(
            claim_id=claim_id,
            reason=reason,
            state_snapshot=state_snapshot,
            proposed_settlement=proposed_settlement,
        )
