"""End-to-end: call tools the way Claude does, through an in-memory MCP client.

"In-memory" = client and server talk directly inside the test process: no subprocess,
no network, so these tests are fast and reliable, but still exercise the real
MCP protocol (tool listing, schemas, results).
"""

from collections.abc import AsyncIterator

import pytest
from mcp import Client

from eventer_mcp import __version__
from eventer_mcp.app import mcp


@pytest.fixture
async def client() -> AsyncIterator[Client]:
    """A fresh connected client for each test.

    raise_exceptions=True: show the real error if the server crashes. In production
    the SDK hides internal errors behind a generic message. Tests only!
    """
    async with Client(mcp, raise_exceptions=True) as c:
        yield c


@pytest.mark.anyio
async def test_ping_tool_is_listed_and_read_only(client: Client) -> None:
    # What Claude sees first: the list of tools and their annotations.
    tools = (await client.list_tools()).tools
    ping = next(t for t in tools if t.name == "ping")
    assert ping.annotations is not None
    assert ping.annotations.read_only_hint is True


@pytest.mark.anyio
async def test_ping_returns_pong(client: Client) -> None:
    result = await client.call_tool("ping", {})
    # is_error=True would mean the tool failed (the model would see an error message).
    assert not result.is_error
    # Return values come back as structured data too. A plain `str` is wrapped as
    # {"result": ...}. Later tools return Pydantic models with named fields.
    assert result.structured_content == {"result": f"pong (eventer-mcp {__version__})"}
