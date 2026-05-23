"""Launch file for the WCP worker reference plugin.

Usage: ros2 launch wcp_worker wcp_worker.launch.py
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode


def generate_launch_description() -> LaunchDescription:
    coord_url = LaunchConfiguration("coordinator_url")
    key_path = LaunchConfiguration("key_path")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "coordinator_url",
                default_value="ws://localhost:8000/wcp/ws",
                description="WebSocket URL of the WCP coordinator",
            ),
            DeclareLaunchArgument(
                "key_path",
                default_value="/tmp/wcp_worker_key",
                description="Path to persist the Ed25519 worker key",
            ),
            LifecycleNode(
                package="wcp_worker",
                executable="wcp_worker",
                name="wcp_worker",
                namespace="",
                output="screen",
                parameters=[{"coordinator_url": coord_url, "key_path": key_path}],
            ),
        ]
    )
