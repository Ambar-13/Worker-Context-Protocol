"""
ROS 1 compatibility capability declaration for the WCP adapter.

ROS 1 has no formal "factsheet" but does expose:
- `rosnode list` / `rosservice list` / `rostopic list` for runtime introspection
- URDF descriptions for robot kinematics
- `param` server entries an operator can declare

For this adapter, capability is built from a manually authored
`ros1_capability_profile` dict that names:
- the robot's URDF base link and footprint
- topic_map (similar to the MQTT adapter, but typed by ROS message types)
- service_map (named WCP commands -> ROS service calls)
- action_map (named WCP tasks -> ROS actionlib goals)
"""
from __future__ import annotations

from typing import Any


def ros1_profile_to_class_extension(profile: dict[str, Any]) -> dict[str, Any]:
    """Translate a ROS 1 capability profile into a WCP class_extension.

    Expected profile shape:

        {
            "robot_class": "research_mobile_manipulator" | "research_arm" | "generic",
            "urdf_base_link": "base_link",
            "footprint_m": [0.6, 0.4],
            "topic_map": [
                {"name": "joint_states", "topic": "/joint_states",
                 "msg_type": "sensor_msgs/JointState"},
                ...
            ],
            "service_map": {
                "set_arm_pose": {"service": "/arm_controller/set_pose",
                                  "srv_type": "geometry_msgs/Pose"}
            },
            "action_map": {
                "navigate_to_pose": {
                    "action": "/move_base",
                    "action_type": "move_base_msgs/MoveBase"
                }
            }
        }
    """
    return {
        "platform": "ros1_robot",
        "ros_distro": "noetic",
        "bridge": "ros1_bridge",
        "robot_class": profile.get("robot_class", "generic"),
        "urdf_base_link": profile.get("urdf_base_link"),
        "footprint_m": profile.get("footprint_m"),
        "topic_subscriptions": [
            {"name": t["name"], "msg_type": t.get("msg_type")}
            for t in profile.get("topic_map", []) or []
        ],
        "services_available": sorted(
            (profile.get("service_map") or {}).keys()
        ),
        "actions_available": sorted(
            (profile.get("action_map") or {}).keys()
        ),
    }


def build_capability_descriptor(
    *,
    worker_did: str,
    coordinator_did: str,
    adapter_signer_key_id: str,
    adapter_pubkey_multibase: str,
    profile: dict[str, Any],
    trust_class: str = "software-keypair",
) -> dict[str, Any]:
    """Construct a CapabilityDescriptor for a ROS-1-bridged robot."""
    descriptor_types = sorted(
        (profile.get("action_map") or {}).keys()
        | (profile.get("service_map") or {}).keys()
    ) or ["ros1_generic_task"]
    return {
        "schema_version": "wcp/1.0-rc1",
        "did": worker_did,
        "worker_class": "autonomous_robot",
        "coordinator_did": coordinator_did,
        "descriptor_types_supported": descriptor_types,
        "class_extension": ros1_profile_to_class_extension(profile),
        "attestation_keys": [
            {
                "key_id": adapter_signer_key_id,
                "did": worker_did,
                "public_key_multibase": adapter_pubkey_multibase,
                "algorithm": "Ed25519",
                "trust_class": trust_class,
            }
        ],
        "attestation_kinds_produced": [
            "ros1_topic_sample_log",
            "ros1_action_result",
            "ros1_service_call_result",
        ],
        "connectivity_profile": "continuous",
    }
