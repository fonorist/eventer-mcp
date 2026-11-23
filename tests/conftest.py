"""Shared pytest fixtures. pytest loads this file automatically for every test."""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    """The MCP SDK is async (built on anyio). Tests marked `@pytest.mark.anyio`
    use this fixture to know which event loop to run on: plain asyncio."""
    return "asyncio"
