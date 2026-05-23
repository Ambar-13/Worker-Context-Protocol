"""WCP worker ROS 2 package.

Spec: ../../spec/0.1.md. Plan: ../../PLAN.md (Section 2.2).

The plugin is a single ROS 2 lifecycle node that maps WCP RPCs to
Nav2 BehaviorTree actions, lifecycle transitions, and a WebRTC bridge for
supervision handoff. Designed for ROS 2 Humble with Jazzy compatibility
declared in package.xml and exercised by the CI matrix.

INTEGRATION-GAP: per-vendor SDK adapter shims (one per closed vendor stack
target at v0.2) live alongside nav_adapter.py; v0.1 ships only the Nav2
adapter.
"""

__version__ = "0.1.0"
__schema_version__ = "wcp/0.1"
