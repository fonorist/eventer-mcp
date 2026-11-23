"""Builds the MCP server and registers its tools.

This is the thin MCP layer: no business logic lives here (see CLAUDE.md).
`uv run mcp dev src/eventer_mcp/app.py` finds the `mcp` object below.
"""

# MCP Python SDK v2. (v1 called this class FastMCP - don't copy v1 examples.)
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from eventer_mcp import __version__

# The server object. Clients see `name` and `version` when they connect.
# `instructions` is read by the AI model: it explains what this server is for,
# so write it for Claude, not for humans.
mcp = MCPServer(
    name="eventer",
    version=__version__,
    instructions=(
        "Plan group events with several people: guests, who brings what, "
        "a shared shopping list, Secret Santa and shared expenses. "
        "Every call acts as the signed-in user."
    ),
)


# `@mcp.tool` turns a plain function into a tool Claude can call. The SDK builds the
# tool definition automatically:
#   - function name  -> tool name ("ping")
#   - docstring      -> description the model reads to decide WHEN to call it
#   - type hints     -> input/output schema (no parameters here; returns a string)
# Annotations are hints for the client, not security:
#   - read_only_hint=True   -> changes nothing, safe to run without asking the user
#   - open_world_hint=False -> doesn't reach the internet / outside systems
@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def ping() -> str:
    """Check that the eventer server is running. Returns 'pong' and the server version."""
    return f"pong (eventer-mcp {__version__})"
