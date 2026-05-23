"""
Modbus TCP-to-WCP gateway.

Runs as a WCP worker that holds a Modbus TCP connection to one or more
PLCs and exposes their command surface and signal reads as WCP tasks.

The gateway accepts:
- `plc_command` tasks: write to one or more named holding registers or
  coils (subject to the operator's register-map declaration of which
  signals are writable)
- `plc_read_window` tasks: read named signals at a fixed cadence over a
  defined window and emit the read trace as evidence

A typical deployment:

    +------------------+        Modbus TCP        +--------+
    |  WCP coordinator | <--- gateway worker --->|  PLC   |
    +------------------+                          +--------+
                                                       |
                                                  serial / IO
                                                       |
                                                +-------------+
                                                | valve, pump |
                                                +-------------+

The PLC's ladder logic continues to run normally. The gateway does not
control PLC scan time, IO sequencing, or interlocks. See
`docs/limits/safety-system-boundary.md`.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol

from wcp_sdk.types import AttestationMode
from wcp_sdk.v2 import Worker

from . import capability as cap_mod


class ModbusTCPClient(Protocol):
    """Minimal async Modbus TCP client surface.

    Implementations: pymodbus.AsyncModbusTcpClient or a custom wrapper.
    """

    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def read_holding_registers(
        self, address: int, count: int, unit: int = 1
    ) -> list[int]: ...
    async def read_input_registers(
        self, address: int, count: int, unit: int = 1
    ) -> list[int]: ...
    async def read_coils(
        self, address: int, count: int, unit: int = 1
    ) -> list[bool]: ...
    async def write_register(
        self, address: int, value: int, unit: int = 1
    ) -> None: ...
    async def write_coil(
        self, address: int, value: bool, unit: int = 1
    ) -> None: ...


@dataclass
class ModbusGatewayConfig:
    coordinator_url: str = "ws://localhost:8000/wcp/ws"
    plc_host: str = "127.0.0.1"
    plc_port: int = 502
    worker_did: str = "did:wcp:example-modbus-plc-001"
    coordinator_did: str = "did:wcp:example-coordinator"
    adapter_signer_key_id: str = "k1"
    adapter_pubkey_multibase: str = "z6Mk-EXAMPLE-modbus-pubkey"


@dataclass
class _ReadWindowRecord:
    claim_id: str
    signals: list[str]
    samples: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _CommandRecord:
    claim_id: str
    command_name: str
    ack: Optional[dict[str, Any]] = None


def _lookup_register(
    register_map: dict[str, Any], name: str
) -> tuple[str, dict[str, Any]]:
    """Find a named register/coil in the map; returns (kind, entry)."""
    for kind in ("holding_registers", "input_registers", "coils"):
        for entry in register_map.get(kind, []) or []:
            if entry["name"] == name:
                return kind, entry
    raise KeyError(f"signal {name!r} not defined in register map")


class ModbusGateway:
    """The WCP worker process gating one PLC behind a register map."""

    def __init__(
        self,
        config: ModbusGatewayConfig,
        modbus: ModbusTCPClient,
        register_map: dict[str, Any],
    ) -> None:
        self.cfg = config
        self.modbus = modbus
        self.register_map = register_map
        self.unit_id = register_map.get("modbus_unit_id", 1)
        self.worker = Worker(
            name="modbus-gateway",
            worker_class="autonomous_robot",
            coordinator=config.coordinator_url,
        )
        self._reads: dict[str, _ReadWindowRecord] = {}
        self._commands: dict[str, _CommandRecord] = {}
        self._wire_handlers()

    async def _read_signal(self, name: str) -> Any:
        kind, entry = _lookup_register(self.register_map, name)
        if kind == "holding_registers":
            vals = await self.modbus.read_holding_registers(
                entry["address"], 1, unit=self.unit_id
            )
            return vals[0] * entry.get("scale", 1.0)
        if kind == "input_registers":
            vals = await self.modbus.read_input_registers(
                entry["address"], 1, unit=self.unit_id
            )
            return vals[0] * entry.get("scale", 1.0)
        if kind == "coils":
            vals = await self.modbus.read_coils(
                entry["address"], 1, unit=self.unit_id
            )
            return bool(vals[0])
        raise AssertionError(f"unknown signal kind {kind!r}")

    async def _write_signal(self, name: str, value: Any) -> None:
        kind, entry = _lookup_register(self.register_map, name)
        if not entry.get("writable"):
            raise PermissionError(f"signal {name!r} is not writable")
        if kind == "holding_registers":
            scale = entry.get("scale", 1.0)
            raw = int(round(float(value) / scale))
            await self.modbus.write_register(
                entry["address"], raw, unit=self.unit_id
            )
            return
        if kind == "coils":
            await self.modbus.write_coil(
                entry["address"], bool(value), unit=self.unit_id
            )
            return
        raise AssertionError(f"writes not supported on kind {kind!r}")

    def _wire_handlers(self) -> None:
        worker = self.worker
        gw = self

        @worker.capability(
            descriptor_types=["plc_command", "plc_read_window"],
            class_extension=cap_mod.register_map_to_class_extension(
                self.register_map
            ),
        )
        def declare() -> None:
            return None

        @worker.handle("plc_command")
        async def execute_command(task: dict) -> dict:
            claim_id = task["claim_id"]
            payload = task.get("descriptor_payload", {})
            cmd_name = payload["command"]
            cmd_def = gw.register_map.get("commands", {}).get(cmd_name)
            if cmd_def is None:
                raise KeyError(f"command {cmd_name!r} not defined")
            # Resolve target signal + value
            if "register" in cmd_def:
                target = cmd_def["register"]
                value = payload.get("value", cmd_def.get("value"))
            elif "coil" in cmd_def:
                target = cmd_def["coil"]
                value = cmd_def.get("value", payload.get("value"))
            else:
                raise KeyError(f"command {cmd_name!r} has no target")
            await gw._write_signal(target, value)
            ack = {
                "command": cmd_name,
                "target": target,
                "value": value,
                "ack_at": datetime.now(timezone.utc).isoformat(),
            }
            gw._commands[claim_id] = _CommandRecord(
                claim_id=claim_id, command_name=cmd_name, ack=ack
            )
            return ack

        @worker.handle("plc_read_window")
        async def execute_read_window(task: dict) -> dict:
            claim_id = task["claim_id"]
            payload = task.get("descriptor_payload", {})
            signals = list(payload.get("signals", []))
            window_s = float(payload.get("window_seconds", 60))
            interval_s = float(payload.get("interval_seconds", 1))
            rec = _ReadWindowRecord(claim_id=claim_id, signals=signals)
            gw._reads[claim_id] = rec
            end_at = datetime.now(timezone.utc) + timedelta(seconds=window_s)
            while datetime.now(timezone.utc) < end_at:
                sample = {"t": datetime.now(timezone.utc).isoformat()}
                for s in signals:
                    sample[s] = await gw._read_signal(s)
                rec.samples.append(sample)
                await asyncio.sleep(interval_s)
            return {
                "window_seconds": window_s,
                "sample_count": len(rec.samples),
            }

        @worker.attest(AttestationMode.SENSOR_WITNESS)
        async def attest_read_window(claim_id: str, task: dict) -> dict:
            rec = gw._reads.get(claim_id)
            if rec is not None:
                return {
                    "kind": "plc_register_read_window",
                    "payload": {
                        "signals": rec.signals,
                        "samples": rec.samples,
                    },
                }
            cmd = gw._commands.get(claim_id)
            if cmd is not None:
                return {
                    "kind": "plc_command_acknowledgement",
                    "payload": cmd.ack,
                }
            return {"kind": "plc_register_read_window", "payload": {"samples": []}}

    async def run(self) -> None:
        await self.modbus.connect()
        try:
            await asyncio.to_thread(self.worker.run)
        finally:
            await self.modbus.close()


def main() -> None:
    cfg = ModbusGatewayConfig(
        coordinator_url=os.environ.get(
            "WCP_COORDINATOR", "ws://localhost:8000/wcp/ws"
        ),
        plc_host=os.environ.get("PLC_HOST", "127.0.0.1"),
        plc_port=int(os.environ.get("PLC_PORT", "502")),
    )
    raise SystemExit(
        "Wire a ModbusTCPClient implementation (e.g., pymodbus) and a "
        "register-map dict, then run ModbusGateway(cfg, client, rm).run()."
    )


if __name__ == "__main__":
    main()
