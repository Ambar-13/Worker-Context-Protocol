"""
RobotAgent: convenience subclass of Agent for the robot-as-agent pattern
(an autonomous robot's onboard controller acting as a WCP agent and posting
follow-up tasks from inside its execute loop).

This is convenience code. Nothing about the wire protocol requires it; you
can do exactly the same thing with a plain ``Agent`` instance and a hand-built
``continuation_of`` block on the task descriptor. The helper just makes the
common case one line.

Spec: ``spec/0.95.md`` Sections 2 and 3 (continuation pattern), updated by
``spec/0.955.md`` (settlement removed from descriptor; ``max_attestation_attempts``
and ``marketplace_ref`` added).
Pattern doc: ``docs/patterns/robot-as-agent.md``.
Reference deployment: ``examples/agents/delivery-robot-dispatcher/``.

Example::

    from wcp_sdk.v2 import RobotAgent

    # Inside the AMR's execute loop, after attesting the transport task:
    robot = RobotAgent(
        name="amr-fleet-7-onboard-planner",
        coordinator="ws://coordinator:8000/wcp/ws",
        agent_class="embodied_agent",
    )
    async with robot:
        follow_up = robot.build_continuation(
            prior_claim_id=transport_claim_id,
            descriptor_type="place_on_shelf",
            descriptor_payload={"shelf_id": "WS-7-A", "orientation_deg": 0},
            required_evidence_kinds=["indoor_pose_track", "weight_delta"],
            constraints={"worker_class_filter": {"allowed": ["semi_autonomous"]}},
            attestation_requirement={
                "modes": ["sensor-witness"],
                "threshold": "M-of-N", "M": 1, "N": 1,
                "evidence_schema": [{"mode": "sensor-witness",
                                     "kinds": ["manipulator_pose_track"]}],
            },
        )
        await robot.post_continuation(
            prior_claim_id=transport_claim_id,
            descriptor=follow_up,
            expiry=expiry_iso,
        )
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from .agent import Agent
from ..identity import AgentIdentity

VALID_AGENT_CLASSES = (
    "llm_agent",
    "embodied_agent",
    "scheduled_agent",
    "human_supervisor",
)


class RobotAgent(Agent):
    """Agent variant that declares an ``agent_class`` and that ships a
    ``post_continuation`` shortcut for the robot-as-agent pattern.

    ``agent_class`` is informational. The coordinator does not branch on it;
    it is preserved in the audit chain entries for posted tasks and may be
    surfaced through operator-side tooling.
    """

    def __init__(
        self,
        *,
        name: str,
        coordinator: str,
        agent_class: str = "embodied_agent",
        identity: Optional[AgentIdentity] = None,
    ) -> None:
        if agent_class not in VALID_AGENT_CLASSES:
            raise ValueError(
                f"agent_class must be one of {VALID_AGENT_CLASSES}; "
                f"got {agent_class!r}"
            )
        super().__init__(name=name, coordinator=coordinator, identity=identity)
        self.agent_class = agent_class

    # --- Helpers ----------------------------------------------------------

    def build_continuation(
        self,
        *,
        prior_claim_id: str,
        descriptor_type: str,
        descriptor_payload: dict[str, Any],
        required_evidence_kinds: Optional[Iterable[str]] = None,
        constraints: Optional[dict[str, Any]] = None,
        attestation_requirement: Optional[dict[str, Any]] = None,
        max_attestation_attempts: int = 1,
        marketplace_ref: Optional[str] = None,
    ) -> dict[str, Any]:
        """Construct a task descriptor that names a prior task via
        ``continuation_of`` and otherwise leaves the application layer to
        the caller.

        The caller MUST supply ``constraints`` and ``attestation_requirement``
        (the two required blocks per the v0.955 descriptor schema). The helper
        adds ``schema_version``, ``task_id``, ``posted_by``, the descriptor
        type and payload, the ``continuation_of`` reference, and the optional
        v0.955 fields ``max_attestation_attempts`` and ``marketplace_ref``.

        Settlement is no longer a protocol concern at v0.955; the
        ``settlement`` block was removed from the descriptor.
        """
        if constraints is None:
            raise ValueError("constraints is required (see TaskDescriptor schema)")
        if attestation_requirement is None:
            raise ValueError("attestation_requirement is required")
        kinds = list(required_evidence_kinds) if required_evidence_kinds else []
        descriptor: dict[str, Any] = {
            "schema_version": "wcp/0.2",
            "task_id": str(uuid.uuid4()),
            "posted_by": self.did,
            "descriptor_type": descriptor_type,
            "descriptor_payload": descriptor_payload,
            "continuation_of": {
                "claim_id": prior_claim_id,
                "required_evidence_kinds": kinds,
            },
            "constraints": constraints,
            "attestation_requirement": attestation_requirement,
            "max_attestation_attempts": max_attestation_attempts,
        }
        if marketplace_ref is not None:
            descriptor["marketplace_ref"] = marketplace_ref
        return descriptor

    async def post_continuation(
        self,
        *,
        prior_claim_id: str,
        descriptor: dict[str, Any],
        expiry: str,
        supervision: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Post a follow-up task that continues from a prior claim.

        The ``descriptor`` MUST carry a ``continuation_of`` block referencing
        ``prior_claim_id`` (the canonical way to build it is
        ``self.build_continuation(prior_claim_id=..., ...)``). The helper
        verifies the continuation pointer matches and then posts through the
        standard ``tasks/post`` RPC.
        """
        cont = descriptor.get("continuation_of") or {}
        if cont.get("claim_id") != prior_claim_id:
            raise ValueError(
                "descriptor.continuation_of.claim_id does not match "
                "prior_claim_id passed to post_continuation"
            )
        return await self.post_task(
            descriptor,
            expiry=expiry,
            supervision=supervision,
        )

    # --- Identity surface -------------------------------------------------

    @property
    def agent_class_declaration(self) -> dict[str, Any]:
        """The agent_class metadata block this agent advertises through its
        DID document's service array. Operators use this for filtering and
        accounting; coordinators do not branch on it."""
        return {
            "type": "WCPAgentClass",
            "agent_class": self.agent_class,
            "advertised_at": datetime.now(timezone.utc).isoformat(),
        }
