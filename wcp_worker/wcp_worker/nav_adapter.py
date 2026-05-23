"""Nav2 BehaviorTree adapter.

Bridges WCP `transport` descriptors to Nav2 NavigateToPose action client.
For application-layer descriptors that do not involve navigation, this
adapter is bypassed.

The plugin sees Nav2 as one of several possible drivers. v0.2 adds a second
robot stack target (one closed vendor) with its own adapter; the WCP RPC
layer is unchanged in either case.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

try:
    import rclpy  # type: ignore[import-not-found]
    from rclpy.action import ActionClient  # type: ignore[import-not-found]
    from rclpy.node import Node  # type: ignore[import-not-found]
    from geometry_msgs.msg import PoseStamped  # type: ignore[import-not-found]
    from nav2_msgs.action import NavigateToPose  # type: ignore[import-not-found]
except ImportError:  # ROS 2 not available in env (e.g., unit-test host)
    rclpy = None  # type: ignore[assignment]
    ActionClient = None  # type: ignore[assignment,misc]
    Node = object  # type: ignore[assignment,misc]
    PoseStamped = None  # type: ignore[assignment,misc]
    NavigateToPose = None  # type: ignore[assignment,misc]

log = logging.getLogger("wcp.nav_adapter")


class NavAdapter:
    """Async wrapper over Nav2 NavigateToPose for the WCP transport flow.

    When ROS 2 is unavailable (test host), `navigate_to_pose` becomes an
    in-process simulation that resolves after `simulated_duration_seconds`.
    Tests rely on this fallback.
    """

    def __init__(
        self,
        node: Optional["Node"] = None,
        *,
        simulated_duration_seconds: float = 0.1,
    ) -> None:
        self._node = node
        self._simulated_duration = simulated_duration_seconds
        self._action_client: Optional["ActionClient"] = None
        if node is not None and ActionClient is not None and NavigateToPose is not None:
            self._action_client = ActionClient(node, NavigateToPose, "navigate_to_pose")

    async def navigate_to_pose(
        self,
        *,
        x: float,
        y: float,
        yaw: float = 0.0,
        frame_id: str = "map",
    ) -> bool:
        if self._action_client is None or PoseStamped is None:
            await asyncio.sleep(self._simulated_duration)
            return True
        await asyncio.to_thread(self._action_client.wait_for_server)
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = frame_id
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        # yaw -> quaternion (z, w only); simplified for v0.1.
        import math
        goal_msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
        send_goal_future = self._action_client.send_goal_async(goal_msg)
        send_goal_handle = await asyncio.wrap_future(send_goal_future)
        if not send_goal_handle.accepted:
            log.warning("Nav2 goal rejected")
            return False
        result_future = send_goal_handle.get_result_async()
        result = await asyncio.wrap_future(result_future)
        return bool(result.status == 4)  # STATUS_SUCCEEDED
