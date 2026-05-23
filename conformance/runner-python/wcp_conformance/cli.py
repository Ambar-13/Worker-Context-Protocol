"""CLI entry point: `wcp-conformance --target <url> --level <N>`."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from .runner import run_level


@click.command()
@click.option("--target", required=True, help="Target endpoint (wss:// URL)")
@click.option("--level", type=int, default=1, help="Conformance level to run (1, 2, or 3)")
@click.option(
    "--bundle-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path(__file__).parent.parent.parent / "test-suite",
    show_default=True,
)
@click.option(
    "--report-path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Where to write the JSON report (defaults to ./conformance-report-<ts>.json)",
)
def main(target: str, level: int, bundle_dir: Path, report_path: Path | None) -> int:
    if level not in (1, 2, 3):
        click.echo("--level must be 1, 2, or 3", err=True)
        sys.exit(2)
    bundle_path = bundle_dir / f"level{level}.json"
    if not bundle_path.exists():
        click.echo(f"bundle file not found: {bundle_path}", err=True)
        sys.exit(2)
    report = asyncio.run(run_level(target, level, bundle_path))
    out_path = report_path or Path(
        f"conformance-report-{report.timestamp.replace(':', '-')}.json"
    )
    out_path.write_text(report.to_json())
    click.echo(f"WCP Conformance Report")
    click.echo(f"======================")
    click.echo(f"Target:            {target}")
    click.echo(f"Schema version:    {report.schema_version}")
    click.echo(f"Suite version:     {report.suite_version}")
    click.echo(f"Level requested:   {report.level_requested}")
    click.echo(f"Level passed:      {report.level_passed}")
    click.echo(f"Tests:             {report.passed_count}/{report.total} passed")
    click.echo(f"Report:            {out_path}")
    sys.exit(0 if report.level_passed == level else 1)


if __name__ == "__main__":
    main()
