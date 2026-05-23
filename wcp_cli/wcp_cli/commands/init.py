"""`wcp init {worker|agent|coordinator}` scaffolding."""
from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path
from typing import Iterable

import click
from rich.console import Console

console = Console()

# 14 domain templates covering institutional and industrial coordination
# contexts.
DOMAINS = (
    "industrial",
    "scientific",
    "emergency",
    "logistics",
    "agriculture",
    "healthcare",
    "infrastructure",
    "disaster",
    "research",
    "manufacturing",
    "smart-city",
    "maritime",
    "construction",
    "generic",
)

WORKER_CLASSES = (
    "human",
    "autonomous_robot",
    "teleoperated_robot",
    "semi_autonomous",
    "hybrid",
)

LLM_PROVIDERS = ("anthropic", "openai", "gemini", "local")


@click.group()
def init() -> None:
    """Scaffold a new WCP worker, agent, or coordinator."""


@init.command("worker")
@click.argument("name")
@click.option(
    "--class",
    "worker_class",
    type=click.Choice(WORKER_CLASSES),
    required=True,
    help="WCP worker class",
)
@click.option(
    "--domain",
    type=click.Choice(DOMAINS),
    default="generic",
    help="Domain template; selects starter capability and handler shape",
)
@click.option(
    "--coordinator",
    default="ws://localhost:8000/wcp/ws",
    help="Default coordinator URL embedded in the worker config",
)
@click.option(
    "--dir", "out_dir", default=None, help="Directory to scaffold into (default: ./<name>)"
)
def init_worker(
    name: str, worker_class: str, domain: str, coordinator: str, out_dir: str | None
) -> None:
    """Scaffold a runnable WCP worker."""
    target = Path(out_dir or name).resolve()
    _scaffold_from_template(
        template_name=f"{domain}/worker",
        target=target,
        substitutions={
            "{{NAME}}": name,
            "{{CLASS}}": worker_class,
            "{{DOMAIN}}": domain,
            "{{COORDINATOR}}": coordinator,
        },
    )
    console.print(
        f"[green]ok[/green] worker scaffolded at [bold]{target}[/bold]\n"
        f"  class:       {worker_class}\n"
        f"  domain:      {domain}\n"
        f"  coordinator: {coordinator}\n\n"
        f"Next: cd {target.name} && wcp dev"
    )


@init.command("agent")
@click.argument("name")
@click.option(
    "--llm",
    type=click.Choice(LLM_PROVIDERS),
    default="anthropic",
    help="LLM provider; selects starter integration adapter",
)
@click.option(
    "--coordinator",
    default="ws://localhost:8000/wcp/ws",
    help="Default coordinator URL embedded in the agent config",
)
@click.option(
    "--dir", "out_dir", default=None, help="Directory to scaffold into (default: ./<name>)"
)
def init_agent(name: str, llm: str, coordinator: str, out_dir: str | None) -> None:
    """Scaffold an AI-agent application that posts tasks."""
    target = Path(out_dir or name).resolve()
    _scaffold_from_template(
        template_name="agent",
        target=target,
        substitutions={
            "{{NAME}}": name,
            "{{LLM}}": llm,
            "{{COORDINATOR}}": coordinator,
        },
    )
    console.print(
        f"[green]ok[/green] agent scaffolded at [bold]{target}[/bold]\n"
        f"  llm:         {llm}\n"
        f"  coordinator: {coordinator}\n\n"
        f"Next: cd {target.name} && pip install -r requirements.txt && python agent.py"
    )


@init.command("coordinator")
@click.argument("name")
@click.option(
    "--port", default=8000, type=int, help="HTTP port the coordinator binds to"
)
@click.option(
    "--dir", "out_dir", default=None, help="Directory to scaffold into (default: ./<name>)"
)
def init_coordinator(name: str, port: int, out_dir: str | None) -> None:
    """Scaffold a runnable WCP coordinator deployment."""
    target = Path(out_dir or name).resolve()
    _scaffold_from_template(
        template_name="coordinator",
        target=target,
        substitutions={
            "{{NAME}}": name,
            "{{PORT}}": str(port),
        },
    )
    console.print(
        f"[green]ok[/green] coordinator scaffolded at [bold]{target}[/bold]\n"
        f"  port:        {port}\n\n"
        f"Next: cd {target.name} && docker compose up"
    )


def _scaffold_from_template(
    *, template_name: str, target: Path, substitutions: dict[str, str]
) -> None:
    if target.exists() and any(target.iterdir()):
        raise click.ClickException(f"Target directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    # Resolve the template directory. We support both installed-package layout
    # (importlib.resources) and editable / source-tree layout (relative to
    # this file). Editable wins when both are present.
    here = Path(__file__).resolve().parent.parent / "templates" / template_name
    if here.exists():
        src_root = here
    else:
        # Fall back to importlib.resources (installed package).
        files = resources.files("wcp_cli") / "templates" / template_name
        src_root = Path(str(files))
        if not src_root.exists():
            raise click.ClickException(
                f"Template not found: {template_name}. Run `wcp doctor` to debug."
            )

    for entry in _walk_template(src_root):
        rel = entry.relative_to(src_root)
        out_path = target / rel
        if entry.is_dir():
            out_path.mkdir(parents=True, exist_ok=True)
            continue
        text = entry.read_text(encoding="utf-8")
        for k, v in substitutions.items():
            text = text.replace(k, v)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")


def _walk_template(root: Path) -> Iterable[Path]:
    yield root
    for p in sorted(root.rglob("*")):
        if "__pycache__" in p.parts:
            continue
        yield p
