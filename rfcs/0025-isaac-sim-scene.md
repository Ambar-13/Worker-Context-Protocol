# RFC 0025: Isaac Sim Reference Scene

- Author(s): TBD
- Status: open (v1.1 deliverable)
- Type: informational
- Created: 2026-05-23
- Targets: v1.1

## Summary

A reference Isaac Sim scene for the robot-side `transport` and `scheduled_presence` flows. Lets implementers verify their plugin against a higher-fidelity simulator than Gazebo Harmonic.

## Motivation

Gazebo Harmonic is the v0.2 default for the simulator demo (cheap, Apache-licensed, no GPU required). Isaac Sim is more visually convincing and exercises NVIDIA's accelerated perception stack; an Isaac scene is useful for vendors who target real-time visual ML workloads.

## Open questions

- Scene authoring tools and license.
- USD vs OpenUSD lineage.
- Whether to ship the scene assets in this repo or in a separate `wcp-isaac-scenes` repo.

## Implementation track

v1.1; not blocking v1.0 final.
