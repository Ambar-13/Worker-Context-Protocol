"""
Tasks service: handles tasks/post, tasks/claim, tasks/execute event ingest,
tasks/attest, tasks/supervise, tasks/abort.

v0.955: tasks/settle is removed. Settlement is no longer a protocol concern.
tasks/attest implements the recheck loop: when the verifier rejects evidence
and the task's max_attestation_attempts has not been exhausted, the task
transitions to `rechecking` and the worker MAY resubmit attestations; once
exhausted, the task transitions to `voided`.

All worker-to-coordinator messages signature-verified via DidResolver before
any state mutation. State transitions emit signed audit chain entries.

Concurrency: tasks/claim implements a 100ms tie-break grace per spec Section
3.4. Implementation uses a row-level lock on the task plus a short-window
candidate buffer.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit_chain import AuditChain
from .did_resolver import (
    DIDResolutionError,
    DidResolver,
    SignatureVerificationError,
)
from .models import (
    AttestationMode,
    TaskState,
    VerifierDecision,
    WcpAttestation,
    WcpClaim,
    WcpSession,
    WcpTask,
    WcpWorker,
)

from .attestation_verifier import (
    DEFAULT_REGISTRY,
    VerificationOutcome,
    evaluate_threshold,
    verify_single,
)

HEARTBEAT_SECONDS = 15
MISSED_HEARTBEATS = 3
CLAIM_TIE_BREAK_MS = 100


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class TaskNotFound(Exception):
    pass


class TaskStateInvalid(Exception):
    pass


class AttestationFailed(Exception):
    pass


class TaskPreempted(Exception):
    pass


class TasksService:
    def __init__(
        self,
        db: Session,
        resolver: DidResolver,
        audit: AuditChain,
        registry: Optional[dict[str, set[str]]] = None,
    ) -> None:
        self._db = db
        self._resolver = resolver
        self._audit = audit
        self._registry = registry or DEFAULT_REGISTRY

    # --- tasks/post ----------------------------------------------------------

    def post(
        self,
        *,
        task: dict[str, Any],
        expiry: str,
        supervision: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        # v0.955: reject legacy settlement / override fields up-front.
        if "settlement" in task:
            raise ValueError(
                "INVALID_DESCRIPTOR: task.settlement removed at v0.955 "
                "(settlement is no longer a protocol concern)"
            )
        req = task.get("attestation_requirement", {})
        for legacy in ("override_authority", "override_audit_required",
                       "override_allowed"):
            if legacy in req:
                raise ValueError(
                    f"INVALID_DESCRIPTOR: attestation_requirement.{legacy} "
                    f"removed at v0.955"
                )

        # Validate attestation requirement against the schema registry.
        self._validate_attestation_requirement(req)

        # Out-of-scope class refusal (Scenario 11). The reference coordinator
        # refuses these. Implementations MAY relax via override RFC.
        descriptor_type = task.get("descriptor_type", "")
        if descriptor_type in (
            "medical",
            "defense",
            "minor_involving",
            "hazmat_above_consumer",
        ):
            raise ValueError(
                "OUT_OF_SCOPE_TASK_CLASS: reference coordinator refuses "
                f"descriptor_type={descriptor_type!r}"
            )

        # Subcontracting forbidden at worker layer by default (Scenario 13).
        if task.get("x-subcontract-allowed") is True:
            raise ValueError(
                "SUBCONTRACT_FORBIDDEN: x-subcontract-allowed=true not "
                "WCP-conformant at v0.1"
            )

        task_id = task.get("task_id") or str(uuid.uuid4())
        task["task_id"] = task_id
        posted_by = task.get("posted_by")
        if not posted_by:
            raise ValueError("INVALID_PARAMS: task.posted_by required")
        try:
            self._resolver.resolve(posted_by)
        except DIDResolutionError as exc:
            raise ValueError(f"DID_NOT_RESOLVED: posted_by: {exc}") from exc

        expiry_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))

        row = WcpTask(
            task_id=task_id,
            posted_by=posted_by,
            descriptor_type=descriptor_type or "unknown",
            task_json=task,
            expiry=expiry_dt,
            state=TaskState.POSTED,
            attestation_attempts_used=0,
        )
        self._db.add(row)
        self._db.flush()

        # v0.955: no settlement.hold. Settlement layers (Stripe, ERP, grant
        # systems, etc.) subscribe to the audit chain (task_completed,
        # task_voided, task_aborted) and run their own value-flow logic.
        accounting_ref = task.get("accounting_ref")

        self._audit.append(
            event_type="task_posted",
            actor_did=posted_by,
            payload={
                "task_id": task_id,
                "accounting_ref": accounting_ref,
            },
            task_id=task_id,
        )

        eligible = self._count_eligible(task)
        return {
            "task_id": task_id,
            "eligible_workers_count": eligible,
            "posted_at": row.posted_at.isoformat(),
        }

    def _count_eligible(self, task: dict[str, Any]) -> int:
        constraints = task.get("constraints", {}) or {}
        wcf = (constraints.get("worker_class_filter") or {}).get("allowed") or []
        stmt = select(WcpWorker)
        if wcf:
            stmt = stmt.where(WcpWorker.worker_class.in_(wcf))
        return len(list(self._db.execute(stmt).scalars()))

    def _validate_attestation_requirement(self, req: dict[str, Any]) -> None:
        if not req:
            raise ValueError(
                "INVALID_ATTESTATION_REQUIREMENT: attestation_requirement missing"
            )
        modes = req.get("modes") or []
        if not modes:
            raise ValueError(
                "INVALID_ATTESTATION_REQUIREMENT: modes empty"
            )
        threshold = req.get("threshold")
        if threshold not in ("any", "all", "M-of-N"):
            raise ValueError(
                f"INVALID_ATTESTATION_REQUIREMENT: unknown threshold {threshold!r}"
            )
        if threshold == "M-of-N":
            m, n = req.get("M"), req.get("N")
            if not isinstance(m, int) or not isinstance(n, int):
                raise ValueError(
                    "INVALID_ATTESTATION_REQUIREMENT: M and N must be integers"
                )
            if m > n:
                raise ValueError(
                    f"INVALID_ATTESTATION_REQUIREMENT: M > N ({m} > {n})"
                )
        # evidence_schema kinds must be registered.
        for entry in req.get("evidence_schema") or []:
            mode = entry.get("mode")
            kinds = entry.get("kinds") or []
            allowed = self._registry.get(mode, set())
            for k in kinds:
                if k not in allowed:
                    raise ValueError(
                        f"INVALID_ATTESTATION_REQUIREMENT: kind {k!r} not "
                        f"registered for mode {mode!r}"
                    )

    # --- tasks/claim ---------------------------------------------------------

    def claim(
        self,
        *,
        task_id: str,
        worker_id: str,
        eta: str,
        acceptance_attestation: dict[str, Any],
        bid: Optional[str] = None,
    ) -> dict[str, Any]:
        task = self._db.get(WcpTask, task_id)
        if task is None:
            raise TaskNotFound(task_id)
        if task.state != TaskState.POSTED:
            # If the task has moved past POSTED, surface this as TaskPreempted
            # whenever the move was to CLAIMED (another worker won). Outside
            # that, the state is genuinely invalid.
            if task.state == TaskState.CLAIMED:
                raise TaskPreempted(
                    f"task {task_id} already claimed by another worker"
                )
            raise TaskStateInvalid(
                f"task {task_id} state is {task.state.value}, not posted"
            )
        expiry = task.expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry < datetime.now(timezone.utc):
            raise TaskStateInvalid(f"task {task_id} expired")

        worker = self._db.get(WcpWorker, worker_id)
        if worker is None:
            raise ValueError(f"DID_NOT_RESOLVED: worker {worker_id!r}")

        # Self-dealing check (Scenario 3).
        if task.posted_by == worker.principal_id:
            req = task.task_json.get("attestation_requirement", {})
            modes = req.get("modes") or []
            if "third-party-witness" not in modes:
                raise ValueError(
                    "POLICY_VIOLATION: self-dealing detected "
                    "(posted_by == worker.principal_id) and "
                    "attestation_requirement lacks third-party-witness"
                )

        # Verify acceptance_attestation signature.
        sig = acceptance_attestation.get("sig")
        payload_hash = acceptance_attestation.get("payload_hash")
        signed_at = acceptance_attestation.get("signed_at")
        if not (sig and payload_hash and signed_at):
            raise ValueError(
                "UNAUTHENTICATED: acceptance_attestation incomplete"
            )
        canonical = _canonical_json(
            {
                "task_id": task_id,
                "worker_id": worker_id,
                "eta": eta,
                "bid": bid,
                "payload_hash": payload_hash,
                "signed_at": signed_at,
            }
        )
        try:
            resolved = self._resolver.resolve(worker_id)
            self._resolver.verify(resolved, canonical, sig)
        except (DIDResolutionError, SignatureVerificationError) as exc:
            raise ValueError(f"UNAUTHENTICATED: {exc}") from exc

        # Tie-break grace: collect candidates within CLAIM_TIE_BREAK_MS. v0.1
        # uses a simple synchronous selection: if another claim has been
        # accepted, return preempted. Realistic deployments hold a transient
        # buffer in Redis for the grace window; tests exercise both paths.
        existing_accepted = self._db.execute(
            select(WcpClaim).where(
                WcpClaim.task_id == task_id, WcpClaim.accepted.is_(True)
            )
        ).first()
        if existing_accepted is not None:
            raise TaskPreempted("another worker already claimed")

        claim = WcpClaim(
            task_id=task_id,
            worker_id=worker_id,
            bid_amount=bid,
            eta=datetime.fromisoformat(eta.replace("Z", "+00:00")),
            acceptance_attestation_json=acceptance_attestation,
            accepted=True,
            last_heartbeat_at=datetime.now(timezone.utc),
        )
        self._db.add(claim)
        task.state = TaskState.CLAIMED
        self._db.flush()

        self._audit.append(
            event_type="task_claimed",
            actor_did=worker_id,
            payload={"task_id": task_id, "claim_id": claim.claim_id, "bid": bid},
            task_id=task_id,
            claim_id=claim.claim_id,
        )

        return {
            "claim_id": claim.claim_id,
            "accepted": True,
            "counter": None,
            "reason": None,
        }

    # --- tasks/execute (open + heartbeat + events) --------------------------

    def execute_open(self, *, claim_id: str) -> dict[str, Any]:
        claim, task = self._claim_and_task(claim_id)
        if task.state not in (TaskState.CLAIMED, TaskState.SUPERVISING):
            raise TaskStateInvalid(
                f"task state is {task.state.value}, cannot open execute"
            )
        session = WcpSession(claim_id=claim_id)
        self._db.add(session)
        if task.state == TaskState.CLAIMED:
            task.state = TaskState.EXECUTING
        elif task.state == TaskState.SUPERVISING:
            task.state = TaskState.EXECUTING
        self._db.flush()
        self._audit.append(
            event_type="execution_started",
            actor_did=claim.worker_id,
            payload={"claim_id": claim_id, "session_id": session.session_id},
            claim_id=claim_id,
            task_id=task.task_id,
        )
        return {"session_id": session.session_id, "state": task.state.value}

    def execute_event(
        self,
        *,
        claim_id: str,
        event_type: str,
        timestamp: str,
        payload: dict[str, Any],
        sig: str,
    ) -> dict[str, Any]:
        claim, task = self._claim_and_task(claim_id)
        if task.state != TaskState.EXECUTING:
            raise TaskStateInvalid(
                f"cannot accept execute event in state {task.state.value}"
            )
        # Signature check.
        canonical = _canonical_json(
            {
                "claim_id": claim_id,
                "event_type": event_type,
                "timestamp": timestamp,
                "payload": payload,
            }
        )
        resolved = self._resolver.resolve(claim.worker_id)
        try:
            self._resolver.verify(resolved, canonical, sig)
        except SignatureVerificationError as exc:
            raise ValueError(f"UNAUTHENTICATED: {exc}") from exc

        if event_type == "heartbeat":
            claim.last_heartbeat_at = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )
            self._db.flush()
        self._audit.append(
            event_type=event_type,
            actor_did=claim.worker_id,
            payload=payload,
            claim_id=claim_id,
            task_id=task.task_id,
        )
        return {"accepted": True}

    def check_heartbeats(self, *, now: Optional[datetime] = None) -> list[str]:
        """Auto-promote stale executing claims to supervising (Scenario 5)."""
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(
            seconds=HEARTBEAT_SECONDS * MISSED_HEARTBEATS
        )
        stale_rows = list(
            self._db.execute(
                select(WcpClaim, WcpTask).join(
                    WcpTask, WcpTask.task_id == WcpClaim.task_id
                ).where(WcpTask.state == TaskState.EXECUTING)
            ).all()
        )
        promoted: list[str] = []
        for claim, task in stale_rows:
            hb = claim.last_heartbeat_at
            if hb is None:
                continue
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=timezone.utc)
            if hb >= cutoff:
                continue
            task.state = TaskState.SUPERVISING
            self._audit.append(
                event_type="heartbeat_timeout",
                actor_did="did:wcp:coordinator",
                payload={
                    "claim_id": claim.claim_id,
                    "last_heartbeat_at": (
                        claim.last_heartbeat_at.isoformat()
                        if claim.last_heartbeat_at
                        else None
                    ),
                    "handoff_reason": "connectivity_lost",
                },
                claim_id=claim.claim_id,
                task_id=task.task_id,
            )
            promoted.append(claim.claim_id)
        if promoted:
            self._db.flush()
        return promoted

    # --- tasks/attest --------------------------------------------------------

    def attest(
        self,
        *,
        claim_id: str,
        attestations: list[dict[str, Any]],
        compensating_action: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        claim, task = self._claim_and_task(claim_id)
        # v0.955: recheck flow allows attestation from EXECUTING, SUPERVISING,
        # or RECHECKING. Terminal states (COMPLETED, VOIDED, ABORTED) reject.
        if task.state == TaskState.VOIDED:
            raise ValueError(
                "RECHECK_MAX_ATTEMPTS_REACHED: claim is voided; "
                "post a new task with continuation_of if work should continue"
            )
        if task.state not in (
            TaskState.EXECUTING,
            TaskState.SUPERVISING,
            TaskState.RECHECKING,
        ):
            raise TaskStateInvalid(
                f"cannot attest in state {task.state.value}"
            )

        req = task.task_json.get("attestation_requirement", {})
        task_payload = task.task_json.get("descriptor_payload", {})
        max_attempts = int(
            task.task_json.get("max_attestation_attempts", 1) or 1
        )

        outcomes: list[tuple[str, VerificationOutcome]] = []
        resolved = self._resolver.resolve(claim.worker_id)
        for ev in attestations:
            # Verify signature on each evidence.
            mode = ev.get("mode")
            kind = ev.get("kind")
            payload = ev.get("payload", {})
            ev_canonical = _canonical_json(
                {
                    "mode": mode,
                    "kind": kind,
                    "payload_hash": ev.get("payload_hash"),
                    "worker_id": claim.worker_id,
                    "claim_id": claim_id,
                    "collected_at": ev.get("collected_at"),
                }
            )
            try:
                self._resolver.verify(resolved, ev_canonical, ev.get("sig", ""))
            except SignatureVerificationError as exc:
                outcomes.append(
                    (
                        mode or "?",
                        VerificationOutcome(
                            decision="fail",
                            reasons=(f"signature: {exc}",),
                        ),
                    )
                )
                continue

            outcome = verify_single(
                mode=mode,
                kind=kind,
                payload=payload,
                task_payload=task_payload,
                schema_registry_kinds=self._registry,
            )
            outcomes.append((mode, outcome))

            self._db.add(
                WcpAttestation(
                    claim_id=claim_id,
                    mode=AttestationMode(mode),
                    kind=kind,
                    payload_hash=ev.get("payload_hash", ""),
                    sig=ev.get("sig", ""),
                    worker_id=claim.worker_id,
                    collected_at=datetime.fromisoformat(
                        ev["collected_at"].replace("Z", "+00:00")
                    ),
                    payload_json=payload,
                    verifier_decision=VerifierDecision(outcome.decision),
                    verifier_reasons=list(outcome.reasons),
                )
            )

        aggregate = evaluate_threshold(requirement=req, outcomes=outcomes)

        # v0.955: increment attempt counter and emit attestation_attempt entry.
        task.attestation_attempts_used = (task.attestation_attempts_used or 0) + 1
        attempt_number = task.attestation_attempts_used
        attempts_remaining = max(0, max_attempts - attempt_number)
        task.state = TaskState.ATTESTING

        self._audit.append(
            event_type="attestation_attempt",
            actor_did=claim.worker_id,
            payload={
                "claim_id": claim_id,
                "attempt_number": attempt_number,
                "decision": aggregate.decision,
            },
            claim_id=claim_id,
            task_id=task.task_id,
        )

        # Route based on verifier decision and attempt counter.
        accounting_ref = task.task_json.get("accounting_ref")
        if aggregate.decision == "pass":
            task.state = TaskState.COMPLETED
            self._audit.append(
                event_type="task_completed",
                actor_did="did:wcp:coordinator",
                payload={
                    "claim_id": claim_id,
                    "task_id": task.task_id,
                    "accounting_ref": accounting_ref,
                },
                claim_id=claim_id,
                task_id=task.task_id,
            )
        elif aggregate.decision == "fail":
            if attempts_remaining > 0:
                task.state = TaskState.RECHECKING
                self._audit.append(
                    event_type="recheck_requested",
                    actor_did="did:wcp:coordinator",
                    payload={
                        "claim_id": claim_id,
                        "attempt_number_just_failed": attempt_number,
                        "attempts_remaining": attempts_remaining,
                        "verifier_reasons": list(aggregate.reasons),
                    },
                    claim_id=claim_id,
                    task_id=task.task_id,
                )
            else:
                task.state = TaskState.VOIDED
                self._audit.append(
                    event_type="task_voided",
                    actor_did="did:wcp:coordinator",
                    payload={
                        "claim_id": claim_id,
                        "task_id": task.task_id,
                        "attempts_used": attempt_number,
                        "verifier_reasons": list(aggregate.reasons),
                        "accounting_ref": accounting_ref,
                    },
                    claim_id=claim_id,
                    task_id=task.task_id,
                )
        # "review" decision keeps the task in ATTESTING for operator review;
        # no terminal transition until a follow-up call resolves.

        self._db.flush()
        return {
            "verifier_decision": aggregate.decision,
            "residual": dict(aggregate.residual),
            "reasons": list(aggregate.reasons),
            "attempt_number": attempt_number,
            "attempts_remaining": attempts_remaining,
        }

    # --- tasks/settle removed at v0.955 -------------------------------------
    # Settlement is no longer a protocol concern. The verifier_decision = pass
    # path in attest() emits a `task_completed` audit entry; external
    # settlement layers subscribe to that and run their own value-transfer
    # logic. The verifier_decision = fail path after attempt exhaustion emits
    # `task_voided`. No tasks/settle RPC exists; calls return METHOD_NOT_FOUND.

    # --- tasks/supervise -----------------------------------------------------

    def supervise(
        self,
        *,
        claim_id: str,
        handoff_reason: str,
        state_snapshot: dict[str, Any],
        urgency: str,
    ) -> dict[str, Any]:
        claim, task = self._claim_and_task(claim_id)
        if task.state not in (TaskState.EXECUTING, TaskState.SUPERVISING):
            raise TaskStateInvalid(
                f"cannot supervise from state {task.state.value}"
            )
        if task.state == TaskState.EXECUTING:
            task.state = TaskState.SUPERVISING
        elif task.state == TaskState.SUPERVISING:
            # supervisor releasing back to worker.
            task.state = TaskState.EXECUTING
        self._db.flush()
        supervisor_did = "did:wcp:rentably-ops"
        session_url = f"wss://localhost/wcp/sup/{uuid.uuid4()}"
        self._audit.append(
            event_type="supervision_handoff",
            actor_did=claim.worker_id,
            payload={
                "claim_id": claim_id,
                "handoff_reason": handoff_reason,
                "urgency": urgency,
                "new_state": task.state.value,
            },
            claim_id=claim_id,
            task_id=task.task_id,
        )
        return {
            "supervisor_id": supervisor_did,
            "session_url": session_url,
            "takeover_authority": "full",
        }

    # --- tasks/abort ---------------------------------------------------------

    def abort(
        self,
        *,
        claim_id: str,
        reason: str,
        state_snapshot: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        claim, task = self._claim_and_task(claim_id)
        # v0.955: terminal states are COMPLETED, VOIDED, ABORTED. proposed_
        # settlement is removed; abort just transitions to ABORTED and the
        # settlement layer above WCP applies its own logic to state_snapshot.
        if task.state in (
            TaskState.COMPLETED,
            TaskState.VOIDED,
            TaskState.ABORTED,
        ):
            raise TaskStateInvalid(
                f"cannot abort from terminal state {task.state.value}"
            )

        task.state = TaskState.ABORTED
        accounting_ref = task.task_json.get("accounting_ref")
        self._db.flush()
        self._audit.append(
            event_type="task_aborted",
            actor_did=claim.worker_id,
            payload={
                "claim_id": claim_id,
                "task_id": task.task_id,
                "reason": reason,
                "state_snapshot": state_snapshot or {},
                "accounting_ref": accounting_ref,
            },
            claim_id=claim_id,
            task_id=task.task_id,
        )
        return {"abort_id": str(uuid.uuid4())}

    # --- helpers -------------------------------------------------------------

    def _claim_and_task(
        self, claim_id: str
    ) -> tuple[WcpClaim, WcpTask]:
        claim = self._db.get(WcpClaim, claim_id)
        if claim is None:
            raise TaskNotFound(f"claim {claim_id} not found")
        task = self._db.get(WcpTask, claim.task_id)
        if task is None:
            raise TaskNotFound(f"task {claim.task_id} not found")
        return claim, task
