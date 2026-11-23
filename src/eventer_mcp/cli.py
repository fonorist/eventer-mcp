"""Command-line entry point: `eventer-mcp`.

`eventer-mcp` alone runs the server over stdio (what Claude Desktop launches).
Important: in stdio mode stdout carries the MCP protocol, so never print() to it.
"""

import argparse
import sys
from collections.abc import Sequence

from eventer_mcp import __version__


def build_parser() -> argparse.ArgumentParser:
    """Define the command line: `eventer-mcp [--version] [run --transport stdio|http]`.

    Kept separate from main() so tests can check parsing without starting a server.
    """
    parser = argparse.ArgumentParser(prog="eventer-mcp", description=__doc__)
    parser.add_argument("--version", action="version", version=f"eventer-mcp {__version__}")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run the MCP server (default)")
    # stdio = local, launched by Claude Desktop/Code. http = hosted server (milestone M6).
    run.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    # Later: a `user create --name ...` subcommand (task 1.3).
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI. Returns the process exit code (0 = success).

    `argv` lets tests pass arguments directly; None means "use the real command line".
    pyproject.toml maps the `eventer-mcp` command to this function ([project.scripts]).
    """
    args = build_parser().parse_args(argv)
    # No subcommand given -> behave like `run`, so the Claude Desktop config stays short.
    command = args.command or "run"
    transport = getattr(args, "transport", "stdio")

    if command == "run":
        if transport == "http":
            # Errors go to stderr. stdout must stay clean for the MCP protocol.
            print("HTTP transport arrives in milestone M6.", file=sys.stderr)
            return 2
        # Imported here, not at the top, so `--help` and `--version` don't load the
        # whole server and SDK.
        from eventer_mcp.app import mcp

        # Blocks until the client (e.g. Claude Desktop) closes the connection.
        mcp.run("stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    # Allows `python -m eventer_mcp.cli` as well as the `eventer-mcp` command.
    raise SystemExit(main())
