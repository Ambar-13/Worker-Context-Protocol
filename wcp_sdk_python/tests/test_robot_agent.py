"""Unit tests for RobotAgent (Python SDK).

These exercise the helper without standing up a coordinator. They cover the
informational contract (agent_class accepted values, continuation_of block
construction, mismatched-claim-id rejection on post_continuation) and the
absence of any verifier or coordinator branching on agent_class.
"""
from __future__ import annotations

import pytest

from wcp_sdk.v2 import RobotAgent


COORD = "ws://localhost:8000/wcp/ws"


def _required_blocks() -> dict:
    """Minimal valid constraints/attestation_requirement/settlement blocks
    suitable for build_continuation."""
    return {
        "constraints": {"worker_class_filter": {"allowed": ["semi_autonomous"]}},
        "attestation_requirement": {
            "modes": ["sensor-witness"],
            "threshold": "M-of-N",
            "M": 1,
            "N": 1,
            "evidence_schema": [
                {"mode": "sensor-witness", "kinds": ["manipulator_pose_track"]}
            ],
            "override_authority": "did:wcp:operator-ops",
            "override_audit_required": True,
        },
        "settlement": {
            "currency": "USD",
            "amount": "0.00",
            "escrow_provider": "internal-cost-allocation",
            "split": [{"party": "did:wcp:cost-center-ops", "pct": 100}],
        },
    }


def test_default_agent_class_is_embodied():
    robot = RobotAgent(name="amr", coordinator=COORD)
    assert robot.agent_class == "embodied_agent"


def test_all_four_agent_classes_accepted():
    for cls in ("llm_agent", "embodied_agent", "scheduled_agent", "human_supervisor"):
        robot = RobotAgent(name=f"agent-{cls}", coordinator=COORD, agent_class=cls)
        assert robot.agent_class == cls


def test_unknown_agent_class_rejected():
    with pytest.raises(ValueError):
        RobotAgent(name="bad", coordinator=COORD, agent_class="quantum_agent")


def test_build_continuation_emits_continuation_of_block():
    robot = RobotAgent(name="amr", coordinator=COORD)
    descriptor = robot.build_continuation(
        prior_claim_id="prior-claim-abc-123",
        descriptor_type="place_on_shelf",
        descriptor_payload={"shelf_id": "WS-7-A"},
        required_evidence_kinds=["indoor_pose_track", "weight_delta"],
        **_required_blocks(),
    )
    assert descriptor["continuation_of"]["claim_id"] == "prior-claim-abc-123"
    assert descriptor["continuation_of"]["required_evidence_kinds"] == [
        "indoor_pose_track",
        "weight_delta",
    ]
    assert descriptor["descriptor_type"] == "place_on_shelf"
    assert descriptor["posted_by"] == robot.did
    assert descriptor["schema_version"] == "wcp/1.0-rc1"


def test_build_continuation_requires_all_three_blocks():
    robot = RobotAgent(name="amr", coordinator=COORD)
    # Missing constraints
    with pytest.raises(ValueError):
        robot.build_continuation(
            prior_claim_id="claim-1",
            descriptor_type="place_on_shelf",
            descriptor_payload={},
            attestation_requirement=_required_blocks()["attestation_requirement"],
            settlement=_required_blocks()["settlement"],
        )
    # Missing attestation_requirement
    with pytest.raises(ValueError):
        robot.build_continuation(
            prior_claim_id="claim-1",
            descriptor_type="place_on_shelf",
            descriptor_payload={},
            constraints=_required_blocks()["constraints"],
            settlement=_required_blocks()["settlement"],
        )
    # Missing settlement
    with pytest.raises(ValueError):
        robot.build_continuation(
            prior_claim_id="claim-1",
            descriptor_type="place_on_shelf",
            descriptor_payload={},
            constraints=_required_blocks()["constraints"],
            attestation_requirement=_required_blocks()["attestation_requirement"],
        )


def test_required_evidence_kinds_defaults_to_empty_list():
    robot = RobotAgent(name="amr", coordinator=COORD)
    descriptor = robot.build_continuation(
        prior_claim_id="claim-1",
        descriptor_type="x",
        descriptor_payload={},
        **_required_blocks(),
    )
    assert descriptor["continuation_of"]["required_evidence_kinds"] == []


def test_agent_class_declaration_shape():
    robot = RobotAgent(
        name="amr",
        coordinator=COORD,
        agent_class="embodied_agent",
    )
    decl = robot.agent_class_declaration
    assert decl["type"] == "WCPAgentClass"
    assert decl["agent_class"] == "embodied_agent"
    assert "advertised_at" in decl


@pytest.mark.asyncio
async def test_post_continuation_rejects_mismatched_prior_claim_id():
    robot = RobotAgent(name="amr", coordinator=COORD)
    # Build a descriptor that references claim_X
    descriptor = robot.build_continuation(
        prior_claim_id="claim-X",
        descriptor_type="place_on_shelf",
        descriptor_payload={},
        **_required_blocks(),
    )
    # Posting with a different prior_claim_id must raise. Coordinator
    # connection is not attempted because the guard runs first.
    with pytest.raises(ValueError):
        await robot.post_continuation(
            prior_claim_id="claim-Y",
            descriptor=descriptor,
            bond_ref="bond-1",
            expiry="2099-12-31T00:00:00Z",
        )
