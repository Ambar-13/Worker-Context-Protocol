"""`wcp register --coordinator <wss>` registers the local worker with a coordinator."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command()
@click.option(
    "--coordinator",
    required=True,
    help="Coordinator URL to register against (ws:// or wss://)",
)
@click.option(
    "--config",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("wcp.yaml"),
    show_default=True,
    help="Worker config file produced by `wcp init worker`",
)
def register(coordinator: str, config: Path) -> None:
    """Register the local worker with a coordinator (capabilities/list)."""
    if not config.exists():
        raise click.ClickException(
            f"Worker config not found at {config}. Run `wcp init worker <name>` first."
        )
    # Defer the actual network call to the SDK so this stays one-screen of code.
    from wcp_sdk.identity import WorkerIdentity
    from wcp_sdk.rpc_client import RpcClient

    asyncio.run(_register_async(coordinator, config))


async def _register_async(coordinator: str, config: Path) -> None:
    from wcp_sdk.identity import WorkerIdentity
    from wcp_sdk.rpc_client import RpcClient

    raw = config.read_text(encoding="utf-8")
    # Minimal YAML-without-PyYAML parse: handle the trivial flat shape `key: value`
    # the scaffolded templates emit. Production deployments substitute a real YAML lib.
    cfg: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")

    key_path = Path(cfg.get("key_path", "./wcp_worker.key"))
    identity = WorkerIdentity.load_or_generate(key_path)

    console.print(
        f"[cyan]register[/cyan] connecting to [bold]{coordinator}[/bold]"
        f" as [bold]{identity.did}[/bold]"
    )

    client = RpcClient(coordinator)
    await client.connect()
    try:
        # Caller's responsibility to supply the descriptor; for `register` we emit
        # a minimal CapabilityDescriptor with the values from the config.
        descriptor = _minimal_descriptor(identity.did, identity.public_key_b64url, cfg)
        result = await client.call(
            "capabilities/list",
            {"worker_id": identity.did, "capabilities": descriptor},
        )
        console.print(
            f"[green]ok[/green] registered. revision={result.get('revision')!r}"
        )
    finally:
        await client.close()


def _minimal_descriptor(worker_did: str, pubkey_b64: str, cfg: dict[str, str]) -> dict:
    return {
        "schema_version": "wcp/0.2",
        "worker_id": worker_did,
        "principal_id": cfg.get("principal_id", "did:wcp:example-principal"),
        "class": cfg.get("worker_class", "human"),
        "required": {
            "current_location": {
                "venue_id": cfg.get("venue_id", "venue-a"),
                "map_id": cfg.get("map_id", "map-a"),
            },
            "available_windows": [
                {"rrule": "FREQ=DAILY", "timezone": cfg.get("timezone", "UTC")}
            ],
            "attestation_methods_supported": [
                "sensor-witness",
                "third-party-witness",
                "cryptographic-presence",
                "owner-sign-off",
            ],
            "certifications": [],
            "policy_windows": [],
            "attestation_keys": [{"kty": "OKP", "crv": "Ed25519", "x": pubkey_b64}],
            "as_of": "2026-05-23T00:00:00Z",
        },
        "class_extension": {},
    }
