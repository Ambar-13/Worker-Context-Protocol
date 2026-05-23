# Vendor Robot Bridge: Template

A skeleton WCP adapter you can copy and customize for any robot platform not already covered by the other adapters in `examples/adapters/`.

## When to use this template

Use this template when:

- Your robot has a proprietary SDK (Boston Dynamics SDK, KUKA KSS/iiQKA, ABB Robot Web Services, FANUC PCDK, Universal Robots URScript/RTDE, Anymal SDK, Franka FCI/franka_ros2 if not via ROS, etc.)
- Or your platform speaks a protocol not represented by the other adapters
- Or you want to build a WCP-native worker but with a vendor-specific capability shape

Do NOT use this template when:

- Your robot speaks one of the protocols already covered (MAVLink, VDA 5050, Modbus, MQTT, ROS 1/2). Use the matching adapter directly.
- Your robot is generic enough to use the default `wcp_sdk.v2.Worker` decorators without any south-bound bridge. Write a regular worker instead; see `examples/agents/*/worker.py`.

## How to use the template

1. **Copy the directory:**
   ```
   cp -r examples/adapters/vendor-robot-bridge-template \
         examples/adapters/<your-vendor>-<your-platform>
   ```

2. **Rename the package** in `__init__.py` to match your platform.

3. **Fill in the south-bound client.** In `bridge.py`, replace the `VendorRobotClient` Protocol with the actual surface of your vendor's SDK:
   - List the connect/disconnect lifecycle methods
   - List the operations you want to expose via WCP
   - List the telemetry streams you'll convert into evidence

4. **Implement the client.** Write a class implementing `VendorRobotClient` against your SDK. Keep this in a separate file (e.g., `vendor_impl.py`) so the bridge logic stays testable with a fake.

5. **Customize the capability translation.** In `capability.py`, replace the placeholder fields in `vendor_info_to_class_extension` with the real ones from your vendor's robot info call.

6. **Map descriptor types to vendor calls.** In `bridge.py`'s `_wire_handlers`, replace the generic `execute_motion(motion_id=_dt, params=...)` with per-descriptor-type dispatch to the appropriate vendor API.

7. **Shape the evidence payload.** The default `@worker.attest` returns a generic `vendor_motion_telemetry` payload. Define your own evidence kinds, register them in your coordinator per RFC 0003, and shape the payload to match.

8. **Choose connectivity profile.** Default is `continuous`. If your bridge runs on the robot itself with intermittent uplink, change to `intermittent` and reference RFC 0029 buffer-and-replay.

9. **Choose trust class.** Default is `software-keypair`. Upgrade per RFC 0033 if you back the adapter's key with a TPM, HSM, or similar.

## Files

- `bridge.py`: skeleton bridge with a `VendorRobotClient` Protocol and placeholder dispatch
- `capability.py`: skeleton capability translator
- `__init__.py`: package marker

## What this template does not do for you

- Authentication to the vendor's robot. Vendors typically require login, API tokens, or certificates; the adapter MUST handle this securely.
- Vendor-specific safety semantics. Each vendor SDK has its own safe-mode, e-stop, and protective-stop behavior. The bridge does NOT translate these into WCP; instead, the bridge MAY consume them to decide whether to accept a WCP claim or to transition to `tasks/supervise`.
- License compliance. Some vendor SDKs have restrictive license terms (academic-only, commercial license required). Read your vendor's SDK license before deployment.

## Testing strategy

Write a `FakeVendorRobotClient` that implements the Protocol in-process, returning canned responses. Use it to unit-test the bridge's:

- Descriptor-type dispatch
- Telemetry collection
- Evidence payload shaping
- Capability translation

End-to-end tests with the real vendor SDK are an integration step the operator runs in their own lab.

## Contributing back

If your adapter could plausibly be used by others (covers a common vendor or protocol), consider submitting it back to the WCP repository under `examples/adapters/`. The maintainers welcome adapter contributions; see `CONTRIBUTING.md`.

## See also

- All the concrete adapters in `examples/adapters/` for design references
- `rfcs/0003-evidence-kinds-registry.md` for evidence kind registration
- `rfcs/0029-wcp-lite.md` for intermittent-connectivity bridges
- `rfcs/0033-attestation-key-trust-classes.md` for trust class declaration
- `docs/limits/safety-system-boundary.md` for the safety-system boundary
