# Modbus-PLC-Gateway-to-WCP Adapter

A gateway that exposes a Modbus TCP PLC (or any Modbus-speaking industrial device behind a TCP/IP frontend) as a WCP worker.

## What Modbus is

Modbus is a simple, mature, vendor-neutral industrial protocol. Modbus TCP is the IP-framed variant; the original Modbus RTU runs over RS-485. Most PLCs (Siemens, Allen-Bradley, Schneider, Beckhoff, Omron, Mitsubishi) speak Modbus TCP either natively or via an inexpensive serial-to-IP gateway, which makes Modbus the broadest-reach industrial protocol available.

The protocol exposes four data tables:

- Discrete Inputs (read-only bits, addresses 10001+)
- Coils (read-write bits, addresses 1+)
- Input Registers (read-only 16-bit words, addresses 30001+)
- Holding Registers (read-write 16-bit words, addresses 40001+)

Modbus has no built-in semantics for what those registers mean. The operator supplies a *register map* that names each address (`setpoint_lpm`, `main_valve_open`, `pump_running`, etc.).

## What this adapter does

- Holds a Modbus TCP connection to one PLC
- Accepts WCP `plc_command` tasks that name an operator-defined command (e.g., `open_valve_to_pct`); the gateway writes the command into the configured target register or coil
- Accepts WCP `plc_read_window` tasks that name a list of signals to sample at a fixed cadence over a fixed window; the gateway returns a sample log signed as `plc_register_read_window` evidence
- Enforces the register map's writability: any signal not marked `writable: true` cannot be written via WCP

## What it does NOT do

- Run the PLC's ladder logic, scan cycle, or safety interlocks. The PLC's existing program continues to execute unchanged. The gateway only writes to registers the operator has explicitly marked writable.
- Replace SCADA. The gateway exposes a narrow, WCP-shaped command-and-read surface; it does not replicate SCADA's HMI, alarm hierarchy, trending, historian, or operator-action logging.
- Provide IEC 62443 security controls. Modbus has no native authentication or encryption; the operator MUST run the gateway on a segmented network with a firewall in front of the PLC.
- Provide IEC 61508/IEC 61511 safety integrity. PLCs running safety-rated logic (SIL 1+) are out of scope for direct WCP command. See `docs/limits/safety-system-boundary.md`.

## Files

- `gateway.py`: the WCP worker process and the Modbus-to-WCP translation layer
- `capability.py`: builds the `class_extension` from the operator's register map
- `__init__.py`: package marker

## Dependencies

- `pymodbus` (most common; the `pymodbus.client.AsyncModbusTcpClient` matches the `ModbusTCPClient` Protocol used here)
- alternatively any Modbus client implementing the four methods in the `ModbusTCPClient` Protocol

## Example register map

```python
register_map = {
    "device_class": "valve_actuator",
    "modbus_unit_id": 1,
    "input_registers": [
        {"name": "flow_rate_lpm", "address": 30001, "scale": 0.1},
        {"name": "upstream_pressure_kpa", "address": 30002, "scale": 1.0},
    ],
    "holding_registers": [
        {"name": "setpoint_lpm", "address": 40001, "scale": 0.1, "writable": True},
    ],
    "coils": [
        {"name": "main_valve_open", "address": 1, "writable": True},
        {"name": "alarm_acknowledge", "address": 2, "writable": True},
    ],
    "commands": {
        "set_flow_setpoint": {"register": "setpoint_lpm"},
        "open_main_valve": {"coil": "main_valve_open", "value": True},
        "close_main_valve": {"coil": "main_valve_open", "value": False},
        "ack_alarm": {"coil": "alarm_acknowledge", "value": True},
    },
}
```

A `plc_command` task with `descriptor_payload = {"command": "set_flow_setpoint", "value": 12.4}` writes `124` (12.4 / 0.1 scale) to holding register 40001.

A `plc_read_window` task with `descriptor_payload = {"signals": ["flow_rate_lpm", "upstream_pressure_kpa"], "window_seconds": 300, "interval_seconds": 5}` produces 60 samples of both signals.

## Local testing

### Option A: Modbus simulator

Run a Modbus TCP simulator (e.g., `pymodbus.examples.simulator`, ModRSsim2, Diagslave) on port 502, point the gateway at it, post tasks.

### Option B: unit-only

`register_map_to_class_extension` and `_lookup_register` are pure functions; test them without any Modbus runtime.

## Evidence kinds produced

| Kind | Source | Notes |
|---|---|---|
| `plc_register_read_window` | sampled reads of named signals during a `plc_read_window` task | the operator's `plc_read_window` descriptor specifies signals, window, interval |
| `plc_command_acknowledgement` | confirmation of a written register/coil | does not include a read-back; some PLCs require a separate read to verify |

Both kinds are operator-defined and require registration per RFC 0003. The defaults shipped here are sample names; operators MAY rename.

## Security note

The gateway has no authentication of who is asking it to write. Operators MUST:

1. Run the gateway on a segregated VLAN
2. Restrict the coordinator's authorized agents to ones the deployment trusts to issue PLC writes
3. Audit `plc_command_acknowledgement` evidence in the audit chain as part of the deployment's change-control process

## See also

- `docs/limits/safety-system-boundary.md` for the safety-rated-system boundary
- `rfcs/0003-evidence-kinds-registry.md` for evidence kind registration
- IEC 62443 family for industrial network security (the operator's responsibility, not WCP's)
