"""`wcp test [--conformance --level N]` runs the conformance suite against a target."""
from __future__ import annotations

import subprocess
import sys

import click
from rich.console import Console

console = Console()


@click.command()
@click.option("--conformance", is_flag=True, help="Run the conformance suite")
@click.option("--level", default=1, type=click.IntRange(1, 3), help="Conformance level")
@click.option(
    "--target",
    default="ws://localhost:8000/wcp/ws",
    help="Target coordinator URL",
)
def test(conformance: bool, level: int, target: str) -> None:
    """Run conformance or unit tests."""
    if conformance:
        console.print(
            f"[cyan]test[/cyan] running WCP conformance suite at Level {level} "
            f"against {target}"
        )
        rc = subprocess.call(
            [
                sys.executable,
                "-m",
                "wcp_conformance.cli",
                "--target",
                target,
                "--level",
                str(level),
            ]
        )
        sys.exit(rc)
    console.print(
        "[yellow]test[/yellow] no flag specified. Pass --conformance to run the suite, "
        "or run `pytest` from your project directory for unit tests."
    )
    sys.exit(0)
