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
@click.option(
    "--example",
    default=None,
    type=str,
    help=(
        "Run a bundled example end-to-end (e.g. 'federation-demo' for the "
        "two-coordinator federation demo). Bypasses normal dev mode; spins up "
        "the example's docker-compose stack via the example's run scripts."
    ),
)
def dev(port: int, skip_coordinator: bool, no_reload: bool, example: str | None) -> None:
    """Run a local coordinator + the worker in the current directory.

    Detects the scaffolded project by reading `wcp.yaml` or by finding
    `worker.py` / `agent.py` in the current working directory.

    When --example is provided, runs the named bundled example instead. The
    federation-demo example brings up two coordinators (coord-alpha on port
    9000, coord-beta on port 9001) plus their databases, provisions a trust
    anchor, and runs a worker + agent pair across the federation boundary.
    """
    if example is not None:
        _run_bundled_example(example)
        return

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


def _run_bundled_example(example: str) -> None:
    """Run a bundled example end-to-end via its docker-compose + verify.sh."""
    here = Path(__file__).resolve()
    # The CLI is at wcp_cli/wcp_cli/commands/dev.py; examples are at
    # ../../../examples/<example> in the repo layout.
    repo_root = here.parents[3]
    example_dir = repo_root / "examples" / example
    if not example_dir.is_dir():
        console.print(
            f"[red]error[/red] unknown example '{example}'. "
            f"available examples: {sorted([p.name for p in (repo_root / 'examples').iterdir() if p.is_dir()])}"
        )
        sys.exit(1)

    compose_file = example_dir / "docker-compose.yml"
    setup_sh = example_dir / "setup.sh"
    verify_sh = example_dir / "verify.sh"

    if compose_file.exists():
        console.print(f"[cyan]dev[/cyan] starting docker compose for example '{example}'...")
        rc = subprocess.call(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            cwd=str(example_dir),
        )
        if rc != 0:
            console.print(
                "[yellow]warn[/yellow] docker compose up returned non-zero; "
                "continuing with setup/verify in best-effort mode"
            )
    else:
        console.print(
            f"[yellow]warn[/yellow] no docker-compose.yml found in {example_dir}"
        )

    if setup_sh.exists():
        console.print(f"[cyan]dev[/cyan] running setup.sh for example '{example}'...")
        subprocess.call([str(setup_sh)], cwd=str(example_dir))

    if verify_sh.exists():
        console.print(f"[cyan]dev[/cyan] running verify.sh for example '{example}'...")
        rc = subprocess.call([str(verify_sh)], cwd=str(example_dir))
        if rc != 0:
            console.print(
                f"[yellow]warn[/yellow] verify.sh exited with code {rc}; "
                "see example README.md for known v1.1 implementation gaps"
            )
        else:
            console.print("[green]ok[/green] example verify.sh PASS")
    else:
        console.print(f"[yellow]warn[/yellow] no verify.sh in {example_dir}")

    console.print(
        f"\n[cyan]dev[/cyan] example '{example}' setup complete. To explore:\n"
        f"  cd {example_dir}\n"
        f"  cat README.md\n"
        f"  python worker_*.py    # run a worker\n"
        f"  python agent_*.py     # run an agent\n"
        f"  ./verify.sh           # re-verify\n"
        f"  docker compose down -v  # cleanup\n"
    )
