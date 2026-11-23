# eventer-mcp — notes for Claude Code

Multi-user MCP server for planning group events (guests, who-brings-what, shopping list, Secret Santa, expenses).
Read `docs/PLAN.md` (architecture + task list) and `docs/EVENT_MCP_BRIEF.md` (scope, tools, data model) first.
George writes this code with you and must be able to explain every line in interviews: explain non-obvious choices briefly.

## Commands
- `uv sync` — install
- `uv run pytest` — tests (`--cov=eventer_mcp` for coverage)
- `uv run ruff check . && uv run ruff format .` — lint + format
- `uv run pyright` — types
- `uv run mcp dev src/eventer_mcp/app.py` — MCP Inspector
- `uv run eventer-mcp run --transport stdio|http` — run server

## SDK version — important
We use the official MCP Python SDK **v2** (`mcp>=2.3,<3`), class `MCPServer` from `mcp.server`.
v1 code (`from mcp.server.fastmcp import FastMCP`) is outdated — do not use it. Check https://py.sdk.modelcontextprotocol.io/ for exact syntax.

## Rules
- Layers: `tools/` (thin MCP layer) → `services/` (logic + permissions, no MCP imports) → `algorithms/` (pure functions) → `models.py`/`db.py`.
- Services take `(session, actor_id, ...)`. Identity comes from `identity.current_user_id()`, **never from a tool argument**.
- Money = integer agorot + currency. Never floats.
- Non-members get "not found", not "forbidden".
- Secret Santa pairs are never returned except giver → own receiver. Not even to the host. Not in errors.
- Errors: raise `DomainError` subclasses in services; tools turn them into actionable `ToolError` messages.
- Every new service function gets tests (happy path + permission check). Algorithms get hypothesis property tests.
- Never commit secrets, tokens or `*.db`. Use `.env` (see `.env.example`).
- Don't publish, deploy or create accounts without George's explicit OK.
- Work one task from `docs/PLAN.md` at a time; tick it when its ✅ check passes.
