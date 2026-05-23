"""wcp CLI top-level dispatch."""
from __future__ import annotations

import sys

import click

from . import __version__
from .commands import dev, doctor, init, inspect_cmd, register, test


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="wcp")
def cli() -> None:
    """Worker Context Protocol CLI.

    Use `wcp <command> --help` for help on a specific command.
    """


cli.add_command(init.init)
cli.add_command(dev.dev)
cli.add_command(test.test)
cli.add_command(inspect_cmd.inspect)
cli.add_command(register.register)
cli.add_command(doctor.doctor)


def main() -> int:
    try:
        cli(standalone_mode=False)
        return 0
    except click.exceptions.Abort:
        return 130
    except click.exceptions.ClickException as exc:
        exc.show()
        return exc.exit_code
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0


if __name__ == "__main__":
    sys.exit(main())
