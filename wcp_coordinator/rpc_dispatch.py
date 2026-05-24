"""
JSON-RPC method dispatch for the WCP coordinator.

Each method is wired to a service method; all errors mapped to the
normative taxonomy in `spec/error-codes.md` (companion to spec/0.955.md).
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


# spec/error-codes.md taxonomy (v0.955).
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
# Added at v0.955: legacy descriptor migration error (settlement block, or
# legacy override_authority / override_audit_required / override_allowed).
INVALID_DESCRIPTOR = -42010

HEARTBEAT_TIMEOUT = -43001

# -44xxx range removed at v0.955: settlement is no longer a protocol concern.
# (SETTLEMENT_FAILED = -44001 deleted.)

SUBCONTRACT_FORBIDDEN = -45001
OUT_OF_SCOPE_TASK_CLASS = -45002

POLICY_VIOLATION = -46001

# Added at v0.955: bounded attestation retry semantics.
RECHECK_MAX_ATTEMPTS_REACHED = -47001
RECHECK_NOT_AVAILABLE_FOR_TASK = -47002


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
    if msg.startswith("INVALID_DESCRIPTOR"):
        return JsonRpcError(INVALID_DESCRIPTOR, msg)
    if msg.startswith("RECHECK_MAX_ATTEMPTS_REACHED"):
        return JsonRpcError(RECHECK_MAX_ATTEMPTS_REACHED, msg)
    if msg.startswith("RECHECK_NOT_AVAILABLE_FOR_TASK"):
        return JsonRpcError(RECHECK_NOT_AVAILABLE_FOR_TASK, msg)
    return JsonRpcError(INVALID_PARAMS, msg)


class Dispatcher:
    """Method router. Translates ValueError into spec error codes."""

    def __init__(
        self, capabilities: CapabilitiesService, tasks: TasksService
    ) -> None:
        self._caps = capabilities
        self._tasks = tasks
        # WCP v0.955.1 wire surface: ten RPCs.
        #
        # Eight LIFECYCLE RPCs (paper Section 3.2 and spec/0.955.md
        # Section 1) carry task coordination:
        #   capabilities/list, capabilities/subscribe,
        #   tasks/post, tasks/claim, tasks/execute, tasks/attest,
        #   tasks/supervise, tasks/abort
        #
        # Two ADMINISTRATIVE RPCs (added at v0.955.1) support
        # over-the-wire administration:
        #   capabilities/upsert  - worker self-registration (a write
        #                          RPC; not the read direction of
        #                          capabilities/list — independent
        #                          method, distinct authorization
        #                          shape, distinct state effect)
        #   audit/observe        - read-only audit-chain segment fetch
        #                          by claim_id or task_id (new
        #                          `audit/` namespace)
        #
        # In-session sub-channel of tasks/execute (the only TRUE
        # sub-channel; it requires an active execute session):
        #   tasks/execute.event  - heartbeats and application events
        #                          flowing over the execute session
        #
        # `tasks/settle` was removed at v0.955; calls return -32601
        # METHOD_NOT_FOUND via the standard dispatch path.
        self._methods: dict[str, Callable[..., Any]] = {
            "capabilities/list": self._capabilities_list,
            "capabilities/upsert": self._capabilities_upsert,  # write sub-channel of capabilities/list
            "capabilities/subscribe": self._capabilities_subscribe,
            "tasks/post": self._tasks_post,
            "tasks/claim": self._tasks_claim,
            "tasks/execute": self._tasks_execute_open,
            "tasks/execute.event": self._tasks_execute_event,  # sub-channel of tasks/execute
            "tasks/attest": self._tasks_attest,
            "tasks/supervise": self._tasks_supervise,
            "tasks/abort": self._tasks_abort,
            "audit/observe": self._audit_observe,
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

    def _capabilities_upsert(
        self,
        *,
        worker_id: str,
        capabilities: dict[str, Any],
        principal_id: str,
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        return self._caps.upsert_capabilities(
            worker_id=worker_id,
            capabilities=capabilities,
            principal_id=principal_id,
            ttl_seconds=ttl_seconds,
        )

    def _audit_observe(
        self,
        *,
        claim_id: str | None = None,
        task_id: str | None = None,
        **_extras: Any,
    ) -> dict[str, Any]:
        # Read-only chain segment fetch by claim_id or task_id.
        # Returns the entries as plain dicts plus the verify_chain
        # outcome over the segment, so conformance tests can inspect
        # chain properties without privileged DB access. Extra kwargs
        # (e.g. expected_property, expected_accounting_ref) are accepted
        # for forward compatibility but ignored at the dispatch layer;
        # the runner's _check_property_holds reads them.
        return self._tasks.observe_audit(claim_id=claim_id, task_id=task_id)

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
        expiry: str,
        supervision: dict | None = None,
        **informational: Any,
    ) -> dict[str, Any]:
        # The v0.95+ spec lets agents attach informational fields alongside
        # the task (e.g. agent_class, bond_ref). The coordinator records
        # them on the audit chain entry but MUST NOT branch matching or
        # verifier behaviour on them — they are observational, not
        # semantic. Unknown extras are accepted for forward-compat.
        return self._tasks.post(
            task=task,
            expiry=expiry,
            supervision=supervision,
            informational=informational or None,
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
        state_snapshot: dict | None = None,
    ) -> dict[str, Any]:
        return self._tasks.abort(
            claim_id=claim_id,
            reason=reason,
            state_snapshot=state_snapshot,
        )
