# ROS 1 Compatibility Adapter for WCP

A bridge that exposes a ROS 1 (Noetic, the final ROS 1 release) robot as a WCP worker, without porting the robot's stack to ROS 2.

## Why this exists

ROS 1 reached end-of-life in May 2025 (Noetic Ninjemys), but a large installed base of research robots, legacy industrial robots, and educational platforms still runs ROS 1 and cannot be upgraded immediately. This adapter lets those robots participate in WCP-coordinated work while their owners plan or defer the ROS 2 migration.

For ROS 2 native deployments, use the `wcp_worker` ROS 2 plugin package shipped in this repository instead of this bridge.

## What this adapter does

- Connects to a ROS 1 master (typically running on the robot itself or a workstation)
- Initializes a ROS node (`wcp_ros1_bridge`)
- Translates the operator's ROS 1 capability profile (URDF, topic types, service signatures, action types) into a WCP `CapabilityDescriptor`
- For each operator-named action in the profile, registers a WCP `descriptor_type` handler that:
  1. Sends an actionlib goal with the WCP `descriptor_payload`
  2. Optionally subscribes to a per-action progress topic during goal execution
  3. Records the result and progress samples as evidence
- For each operator-named service, registers a WCP `descriptor_type` handler that calls the service and records the response

## What it does NOT do

- Auto-discover ROS topics/services/actions. ROS 1's introspection is unreliable for type discovery; the operator authors a profile dict (see `capability.py`) declaring exactly what is exposed.
- Provide ROS 2 functionality. ROS 1 lacks DDS, security (SROS 2), and the actions IDL used in ROS 2. The bridge maps only the ROS 1 surface.
- Override ROS interlocks. The robot's safety nodes (collision avoidance, joint-limit enforcement, e-stop) continue to operate. The bridge sends action goals; the robot's own controllers decide whether to accept them.
- Bridge `tf` or `tf2` transforms upstream. Operators wanting transform history in the audit chain MUST subscribe to a `/tf` snapshot via the topic-map mechanism.

## Files

- `bridge.py`: the WCP worker process and ROS-to-WCP translation
- `capability.py`: builds the `class_extension` from the operator's ROS 1 profile
- `__init__.py`: package marker

## Dependencies

The bridge speaks to ROS 1 via a `ROS1Client` Protocol. A real implementation would wrap `rospy`. Since `rospy` is a sync-style API tied to ROS 1's threading model, the recommended approach is:

1. Run the bridge in a normal Python 3 process (`rospy` works under Python 3 on Noetic)
2. Use `asyncio.to_thread` or a dedicated worker thread for each rospy call
3. Alternatively, run the bridge alongside `ros1_bridge` (the official ROS 2 -> ROS 1 bridge) and let the bridge speak ROS 2; reference impl note: a cleaner long-term path

## Example ROS 1 profile

```python
profile = {
    "robot_class": "research_mobile_manipulator",
    "urdf_base_link": "base_link",
    "footprint_m": [0.65, 0.40],
    "topic_map": [
        {"name": "joint_states",
         "topic": "/joint_states",
         "msg_type": "sensor_msgs/JointState"},
        {"name": "odom",
         "topic": "/odom",
         "msg_type": "nav_msgs/Odometry"},
    ],
    "service_map": {
        "open_gripper": {
            "service": "/gripper_controller/open",
            "srv_type": "std_srvs/Trigger",
        },
        "close_gripper": {
            "service": "/gripper_controller/close",
            "srv_type": "std_srvs/Trigger",
        },
    },
    "action_map": {
        "navigate_to_pose": {
            "action": "/move_base",
            "action_type": "move_base_msgs/MoveBase",
            "progress_topic": "/move_base/feedback",
            "progress_msg_type": "move_base_msgs/MoveBaseActionFeedback",
        },
        "execute_arm_trajectory": {
            "action": "/arm_controller/follow_joint_trajectory",
            "action_type": "control_msgs/FollowJointTrajectory",
            "progress_topic": "/arm_controller/state",
            "progress_msg_type": "control_msgs/JointTrajectoryControllerState",
        },
    },
}
```

With this profile, the bridge declares descriptor_types `navigate_to_pose`, `execute_arm_trajectory`, `open_gripper`, `close_gripper`. A WCP agent posts a task with `descriptor_type = "navigate_to_pose"` and `descriptor_payload` matching the `MoveBaseGoal` shape; the bridge dispatches the actionlib goal and records progress.

## Local testing

### Option A: full ROS 1 Noetic environment

Requires Ubuntu 20.04 (or Docker with a Noetic image), `roscore`, and a launched robot stack (real or simulated, e.g., TurtleBot 3 Gazebo).

```
# Terminal 1: roscore
roscore

# Terminal 2: robot sim
roslaunch turtlebot3_gazebo turtlebot3_world.launch

# Terminal 3: WCP coordinator
python -m wcp_coordinator

# Terminal 4: this bridge (wired with rospy-backed ROS1Client and the profile above)
```

### Option B: unit-only

`ros1_profile_to_class_extension` is pure and testable without ROS 1.

## Evidence kinds produced

| Kind | Source | Notes |
|---|---|---|
| `ros1_topic_sample_log` | accumulated samples from a per-action progress topic | shape: `{topic, msg_type, samples: [{t, msg}]}` |
| `ros1_action_result` | the actionlib result + start/finish timestamps | the full `result` is included; operators MAY truncate |
| `ros1_service_call_result` | the service response | for service-handled descriptor_types |

All three are operator-defined and need registration per RFC 0003.

## Migration note

The ROS 1 EOL means new feature work in the ROS ecosystem targets ROS 2. Operators using this adapter should treat it as a stopgap; the ROS 2 native `wcp_worker` package is the long-term path.

## See also

- `wcp_worker/` package (ROS 2 native plugin, separate directory)
- `rfcs/0003-evidence-kinds-registry.md`
- `docs/limits/real-time-boundary.md`
- `docs/limits/safety-system-boundary.md`
- ROS 1 EOL notice: https://wiki.ros.org/Distributions
