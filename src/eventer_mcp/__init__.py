"""eventer-mcp: multi-user event planning for AI agents."""

from importlib.metadata import PackageNotFoundError, version

# Read the version from the installed package metadata, so it is defined in ONE place:
# `version = ...` in pyproject.toml. Bump it there and every part of the app sees it.
try:
    __version__ = version("eventer-mcp")
except PackageNotFoundError:  # pragma: no cover - only when the package is not installed
    # `pragma: no cover` = exclude from coverage; tests always run with the package installed.
    __version__ = "0.0.0"
