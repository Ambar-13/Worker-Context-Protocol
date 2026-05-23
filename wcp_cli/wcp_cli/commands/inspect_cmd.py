"""`wcp inspect` launches the visual inspector at http://localhost:8765."""
from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command(name="inspect")
@click.option(
    "--port", default=8765, type=int, help="Port for the inspector UI (default 8765)"
)
@click.option(
    "--coordinator",
    default="ws://localhost:8000/wcp/ws",
    help="Coordinator to introspect",
)
@click.option("--no-open", is_flag=True, help="Do not open a browser")
def inspect(port: int, coordinator: str, no_open: bool) -> None:
    """Launch the WCP visual inspector."""
    # Find the inspector package; it ships alongside the CLI.
    inspector_dir = Path(__file__).resolve().parent.parent.parent.parent / "inspector"
    if not inspector_dir.exists():
        raise click.ClickException(
            f"Inspector assets not found at {inspector_dir}. "
            "Reinstall the wcp package."
        )
    serve_py = inspector_dir / "serve.py"
    if not serve_py.exists():
        raise click.ClickException(f"Inspector entry point missing: {serve_py}")
    console.print(
        f"[cyan]inspect[/cyan] starting visual inspector at "
        f"http://localhost:{port} (coordinator: {coordinator})"
    )
    if not no_open:
        try:
            webbrowser.open(f"http://localhost:{port}/")
        except Exception:
            pass
    rc = subprocess.call(
        [sys.executable, str(serve_py), "--port", str(port), "--coordinator", coordinator]
    )
    sys.exit(rc)
