"""`wcp dev` runs a local coordinator plus the worker in the current dir."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command()
@click.option(
    "--port", default=8000, type=int, help="Coordinator port (defaults to 8000)"
)
@click.option(
    "--skip-coordinator",
    is_flag=True,
    help="Do not spawn a local coordinator; assume one is already running",
)
@click.option(
    "--no-reload",
    is_flag=True,
    help="Disable hot reload (uvicorn --reload off)",
)
def dev(port: int, skip_coordinator: bool, no_reload: bool) -> None:
    """Run a local coordinator + the worker in the current directory.

    Detects the scaffolded project by reading `wcp.yaml` or by finding
    `worker.py` / `agent.py` in the current working directory.
    """
    cwd = Path.cwd()
    procs: list[subprocess.Popen[bytes]] = []

    coord_proc: subprocess.Popen[bytes] | None = None
    if not skip_coordinator:
        console.print(
            f"[cyan]dev[/cyan] starting local coordinator on port {port}..."
        )
        env = dict(os.environ)
        env.setdefault("WCP_COORDINATOR_PORT", str(port))
        uvicorn_args = [
            sys.executable,
            "-m",
            "uvicorn",
            "wcp_dev_runtime.coordinator_dev_app:app",
            "--port",
            str(port),
        ]
        if not no_reload:
            uvicorn_args.append("--reload")
        coord_proc = subprocess.Popen(uvicorn_args, env=env)
        procs.append(coord_proc)
        # Brief wait for the coordinator to bind. Production deployments use
        # health probes; the CLI's dev flow uses a short sleep with a retry.
        time.sleep(2.0)

    worker_py = cwd / "worker.py"
    agent_py = cwd / "agent.py"
    if worker_py.exists():
        target = worker_py
        kind = "worker"
    elif agent_py.exists():
        target = agent_py
        kind = "agent"
    else:
        _terminate_all(procs)
        raise click.ClickException(
            "No worker.py or agent.py in current directory. Run `wcp init worker <name>` first."
        )

    console.print(f"[cyan]dev[/cyan] starting {kind} from {target.name}...")
    proc = subprocess.Popen([sys.executable, str(target)])
    procs.append(proc)

    def _shutdown(signum: int, frame: object) -> None:
        console.print("\n[cyan]dev[/cyan] shutting down")
        _terminate_all(procs)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        for p in procs:
            if p.poll() is not None:
                _terminate_all(procs)
                if p.returncode != 0:
                    raise click.ClickException(
                        f"child exited unexpectedly with code {p.returncode}"
                    )
                return
        time.sleep(0.5)


def _terminate_all(procs: list[subprocess.Popen[bytes]]) -> None:
    for p in procs:
        if p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
