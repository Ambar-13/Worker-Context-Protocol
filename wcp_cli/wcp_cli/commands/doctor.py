"""`wcp doctor` runs environment diagnostics."""
from __future__ import annotations

import importlib
import platform
import shutil
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()

CHECKS = [
    ("python", lambda: sys.version.split()[0]),
    ("platform", lambda: platform.platform()),
]

REQUIRED_PACKAGES = (
    "wcp_sdk",
    "click",
    "rich",
    "httpx",
    "websockets",
    "cryptography",
)

OPTIONAL_PACKAGES = (
    "fastapi",  # for `wcp dev` coordinator
    "uvicorn",  # for `wcp dev` coordinator
    "sqlalchemy",  # for the reference coordinator
    "wcp_conformance",  # for `wcp test --conformance`
)


@click.command()
def doctor() -> None:
    """Diagnose the local WCP environment."""
    table = Table(title="wcp doctor", show_lines=True)
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Status")
    table.add_column("Details")

    overall_ok = True

    for label, fn in CHECKS:
        try:
            table.add_row(label, "[green]ok[/green]", str(fn()))
        except Exception as exc:
            overall_ok = False
            table.add_row(label, "[red]fail[/red]", str(exc))

    for pkg in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "(no __version__)")
            table.add_row(pkg, "[green]ok[/green]", f"version={version}")
        except ImportError as exc:
            overall_ok = False
            table.add_row(
                pkg, "[red]missing[/red]", f"pip install {pkg.replace('_', '-')}"
            )

    for pkg in OPTIONAL_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "(no __version__)")
            table.add_row(pkg + " (optional)", "[green]ok[/green]", f"version={version}")
        except ImportError:
            table.add_row(
                pkg + " (optional)",
                "[yellow]missing[/yellow]",
                f"required for some features; pip install {pkg.replace('_', '-')}",
            )

    docker = shutil.which("docker")
    table.add_row(
        "docker",
        "[green]ok[/green]" if docker else "[yellow]missing[/yellow]",
        docker or "required for deployments/docker-compose.yml",
    )

    console.print(table)
    if not overall_ok:
        console.print("[red]some required checks failed[/red]")
        sys.exit(1)
    console.print("[green]all required checks pass[/green]")
