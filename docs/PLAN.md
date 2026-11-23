# eventer-mcp — Architecture, Setup & Task Plan

> Companion to `EVENT_MCP_BRIEF.md` (the *what*). This file is the *how* and the *order*.
> Put a copy in the repo as `docs/PLAN.md`. Tick tasks as you go.
> Agreed 2026-11-23. Pace: evenings ~2.5 h, ~6 evenings/week. Target: ~Dec 15.

---

## 0. Decisions (2026-11-23)

| Topic | Decision |
|---|---|
| Name | `eventer-mcp` (PyPI free). Tagline: "multi-user event planning for AI agents". Registry: `io.github.<you>/eventer-mcp` |
| Primary consumer | Project 2 backend. Secondary: you + recruiters in Claude Desktop. Guests never call MCP directly. |
| Scope | All 4 modules. Order: events → items → **Santa → expenses** |
| Identity | Per-user bearer tokens. P2 creates a user per guest (admin endpoint) and calls with that guest's token. |
| First run | Local stdio mode auto-creates a default user + SQLite file. Zero setup for recruiters. |
| Code | `D:\projects\eventer-mcp` (PyCharm project) → GitHub. You implement with Claude Code. |
| Hosting | Decide at M6 (Railway vs Render+Supabase). Until then: Dockerfile + `DATABASE_URL`, nothing host-specific. |
| Order | Finish P1 fully (incl. publish) before P2. |
| SDK | **Official MCP Python SDK v2** (`mcp>=2.3,<3`, class `MCPServer`). Not the separate `fastmcp` package. |

**Important (checked 2026-11-23):** `pip install mcp` now gives SDK **v2**. `FastMCP` was renamed `MCPServer`.
Most tutorials and Claude's training data show v1 code (`from mcp.server.fastmcp import FastMCP`) — **don't copy v1 snippets**.
Use the v2 docs: https://py.sdk.modelcontextprotocol.io/ (Tools, Structured Output, Handling errors, Testing, Authorization, Deploy).

---

## 1. Architecture

### 1.1 Layers

```
 Claude Desktop / Claude Code / Project 2 backend   (MCP clients)
        │ stdio (local)          │ Streamable HTTP + Bearer token (hosted)
        ▼                        ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ tools/  (MCP layer)   thin: arg parsing, call service,      │
 │                       map errors → ToolError, build output  │
 │ identity.py           "who is calling?" → user_id           │
 ├─────────────────────────────────────────────────────────────┤
 │ services/  (business logic)  permissions + rules            │
 │   every function: service(session, actor_id, ...)          │
 │   no MCP imports → Project 2 can import it directly         │
 ├─────────────────────────────────────────────────────────────┤
 │ algorithms/  pure functions: santa_draw, split, settle_up   │
 │   no DB, no I/O → unit + property tests                     │
 ├─────────────────────────────────────────────────────────────┤
 │ models.py + db.py   SQLModel tables; SQLite local,          │
 │                     Postgres hosted (DATABASE_URL)          │
 └─────────────────────────────────────────────────────────────┘
```

### 1.2 How one call flows ("I'll bring the wine")

1. Claude calls tool `claim_item(item_id="itm_4f9k2a", quantity=2)`.
2. `tools/items.py` asks `identity.current_user_id()` → `usr_x7…` (never from tool args).
3. Calls `services.items.claim_item(session, actor_id, item_id, 2)`.
4. Service checks: item exists, actor is a member of the event, quantity not over what's left → writes `Claim`.
5. Tool returns a Pydantic model (structured output) + a one-line summary.
6. Any `DomainError` → `ToolError` with a fix-it message ("Only 1 bottle left to claim").

### 1.3 Identity (the main interview topic)

| Mode | How the user is found |
|---|---|
| **stdio** (local) | Env `EVENTER_TOKEN` → user. If not set → get-or-create a default local user ("Me"). Demo trick: two Claude Desktop entries ("eventer-host", "eventer-dana") with different tokens = two users on one PC. |
| **HTTP** (hosted) | SDK `TokenVerifier` reads `Authorization: Bearer …`, looks up the token hash → returns `AccessToken(client_id=user_id)`. Tools read it with `get_access_token()`. The stdio fallback is **disabled** in HTTP mode. |
| **Tests** | In-memory client skips auth → `identity.override(user_id)` context manager for tests only. |

- Tokens: `secrets.token_urlsafe(32)` with prefix `etk_`; store only SHA-256 hash; show once.
- Users are created by CLI (`eventer-mcp user create --name Dana`) or, for P2, an admin HTTP endpoint protected by `EVENTER_ADMIN_KEY` (M6). `join_event` does **not** create users or tokens.
- Non-members get "Event not found" (not "Forbidden") so event IDs don't leak.
- Note from SDK docs: auth only protects HTTP; stdio security = whoever launched the process.

### 1.4 Data & conventions

- Data model: see brief §7 (unchanged).
- IDs: prefix + 6 random lowercase base32 chars: `usr_`, `evt_`, `itm_`, `exp_`, `pay_`. Invite codes: 6 chars, uppercase, no look-alikes (no 0/O/1/I).
- Money: integer agorot + currency (default `ILS`). Input accepts `"340"`, `340`, `"12.50"` → parsed with `Decimal`. Output gives both `amount_minor` and `"₪340.00"`.
- Dates: ISO `YYYY-MM-DD`; timestamps stored UTC.
- DB: sync SQLModel engine. Local default path: `%USERPROFILE%\.eventer-mcp\eventer.db` (via `platformdirs` or `Path.home()`), override with `DATABASE_URL`. Tables via `create_all` until M6, then Alembic.
- Errors (`errors.py`): `NotFound`, `Forbidden`, `Conflict`, `InvalidInput` → all subclass `DomainError`.

### 1.5 Repo layout

```
eventer-mcp/
├─ pyproject.toml          deps, [project.scripts] eventer-mcp = "eventer_mcp.cli:main", ruff/pyright/pytest config
├─ README.md  LICENSE (MIT)  CLAUDE.md  .gitignore  .env.example
├─ docs/  PLAN.md  EVENT_MCP_BRIEF.md  architecture.png (M7)
├─ server.json  Dockerfile  (M6–M7)
├─ .github/workflows/ci.yml
├─ src/eventer_mcp/
│  ├─ app.py               builds MCPServer, registers tools/resources/prompts
│  ├─ cli.py               run --transport stdio|http, user create
│  ├─ config.py            settings from env
│  ├─ db.py  models.py  schemas.py  errors.py  ids.py  money.py  tokens.py  identity.py
│  ├─ tools/      events.py  items.py  santa.py  expenses.py  resources.py  prompts.py
│  ├─ services/   users.py  events.py  items.py  santa.py  expenses.py  _perms.py
│  └─ algorithms/ santa.py  split.py  settle.py
└─ tests/
   ├─ conftest.py           in-memory SQLite session, user factory, MCP client fixture
   ├─ algorithms/  services/  e2e/
```

---

## 2. Setup & technologies

| Tool | What it's for | Notes |
|---|---|---|
| Python 3.12 | language | installed by uv |
| uv | installs packages, runs project, builds package | `winget install astral-sh.uv` |
| `mcp` (SDK v2) | the MCP server | `uv add "mcp[cli]>=2.3,<3"` |
| SQLModel | DB tables as Python classes | `uv add sqlmodel` |
| psycopg | Postgres driver | M6 only: `uv add "psycopg[binary]"` |
| pytest, anyio, hypothesis, pytest-cov | tests (SDK tests are async → anyio) | `uv add --dev …` |
| ruff | lint + format | |
| pyright | type check (basic mode) | |
| GitHub Actions | runs checks on every push | |
| Node.js LTS | needed by MCP Inspector (`npx`) | `uv run mcp dev …` opens Inspector |
| Claude Desktop | real end-to-end test | config: `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Code | your pair programmer | reads `CLAUDE.md` + `docs/PLAN.md` |
| Docker Desktop | build the hosting image | M6 only |

Exact syntax for MCP things (annotations, structured output, `ToolError`, running stdio/HTTP, `TokenVerifier`) → check the v2 docs page when you reach that task; don't trust memory.

---

## 3. Tasks

Each task ≈ 30–90 min. ✅ = done-when check. Tasks marked **[OK]** need your explicit go-ahead (they use your accounts).
After each session: commit, push, CI green, add 2 lines to `PROJECT_MEMORY.md` progress log.

### M0 — Setup & skeleton (2 sessions, → Nov 25)

- [ ] **0.1 Install tools.** Git, uv, Node LTS, Claude Desktop, Claude Code. Create GitHub repo `eventer-mcp` (public, MIT). ✅ `uv --version`, `node -v`, `git --version` work.
- [x] **0.2 Scaffold.** `uv init --package eventer-mcp` (src layout); add deps above; ruff/pyright/pytest config in `pyproject.toml`; `.gitignore` (incl. `.env`, `*.db`); `.env.example`; LICENSE; copy `CLAUDE.md` + `docs/PLAN.md` + `docs/EVENT_MCP_BRIEF.md`. ✅ `uv run pytest` runs one dummy test.
- [ ] **0.3 Hello server.** `app.py` with `MCPServer("eventer")` + a `ping` tool; `cli.py` with `run --transport stdio`. ✅ `ping` works in MCP Inspector.
- [x] **0.4 First e2e test.** `tests/e2e/test_ping.py` using the in-memory `Client` (see Testing docs). ✅ passes.
- [ ] **0.5 CI.** `.github/workflows/ci.yml`: `uv sync` → `ruff check` → `ruff format --check` → `pyright` → `pytest --cov` (fail under 80% on `services/` + `algorithms/`). Run on ubuntu + windows. Protect `main`: merge via PR only when CI is green. ✅ green on GitHub.
- [ ] **0.6 Claude Desktop.** Add `eventer` to the config (`uv --directory <repo> run eventer-mcp run`). ✅ Claude calls `ping`.

### M1 — Events, identity, invites (3 sessions, → Nov 28)

- [ ] **1.1 Foundations.** `config.py` (env settings), `db.py` (engine, session, `create_all`), `ids.py`, `money.py` (+ unit tests: `"12.5"`→1250, rejects negatives/3 decimals), `errors.py`. ✅ tests pass.
- [ ] **1.2 Models.** `User`, `Event`, `Invite`, `Membership`. ✅ tables created in a test SQLite DB.
- [ ] **1.3 Identity.** `tokens.py` (make + hash), `services/users.py` (create, find by token, get-or-create local user), `identity.py` (stdio rules + test override), CLI `user create --name`. ✅ tests: right user from token; unknown token rejected; local user auto-created once.
- [ ] **1.4 Event services.** `create_event`, `list_my_events`, `get_event`, `update_event`; `_perms.py` (`require_member`, `require_host`). ✅ tests incl. non-member → NotFound, guest can't update.
- [ ] **1.5 Invites & guests services.** `create_invite`, `join_event` (expiry, max uses, joining twice is harmless), `list_guests`, `update_my_membership`, `remove_guest`. ✅ tests.
- [ ] **1.6 Tools.** `schemas.py` outputs; `tools/events.py` with annotations + model-friendly docstrings; DomainError → ToolError. e2e test: host creates + invites, Dana joins. ✅ scenarios 1–2 in Claude Desktop with two entries (host + Dana).

### M2 — Items & shopping list (2 sessions, → Dec 1)

- [ ] **2.1 Item services.** Models `Item`, `Claim`; `add_item` (warn on same name), `claim_item` (partial, no over-claim), `unclaim_item`, `mark_item_done`, `delete_item`. ✅ tests incl. permissions.
- [ ] **2.2 Shopping list.** Group by assignee or category, `only_open`, estimated totals. ✅ tests.
- [ ] **2.3 Tools + e2e.** `tools/items.py`. ✅ scenarios 3–4 in Claude Desktop.

### M3 — Secret Santa (3 sessions, → Dec 4)

- [ ] **3.1 Draw algorithm.** `algorithms/santa.py`: `draw(participants, exclusions, rng) -> dict[giver, receiver]`, shuffle + backtracking, `NoValidAssignment` error. ✅ unit tests + hypothesis: it's a permutation, nobody draws self, no excluded pair, same seed → same result.
- [ ] **3.2 Santa services.** Models; `santa_setup`, `set_wishlist`, `santa_draw`, `santa_reset(confirm)`, `santa_status`, `my_santa_target`. ✅ tests incl. draw twice refused.
- [ ] **3.3 Privacy tests.** After a draw, call **every** read tool/service as each user (host included) and assert no other person's pair shows up anywhere, including error messages. ✅ passes. *(Never cut.)*
- [ ] **3.4 Tools + e2e.** `tools/santa.py`. ✅ scenario 6 in Claude Desktop.

### M4 — Expenses & settle-up (3 sessions, → Dec 8)

- [ ] **4.1 Algorithms.** `split.py`: even split, leftover agorot handed out in a fixed order. `settle.py`: greedy largest-debtor ↔ largest-creditor. ✅ tests + hypothesis: shares sum to amount; ≤ n−1 transfers; everyone ends at 0. *(Never cut.)*
- [ ] **4.2 Expense services.** Models `Expense`, `ExpenseShare`, `Payment`; `add_expense` (`split_among` / `exclude`, default all members), `list_expenses`, `record_payment`. ✅ tests.
- [ ] **4.3 Balances & settle-up services.** ✅ tests incl. payments reducing debts.
- [ ] **4.4 Tools + e2e.** `tools/expenses.py`. ✅ scenario 5 in Claude Desktop.

### M5 — Make it work well with Claude (2 sessions, → Dec 10)

- [ ] **5.1 Resources & prompt.** `event://{event_id}/summary`, `event://{event_id}/shopping-list`, prompt `plan_event`. ✅ visible + working in Inspector.
- [ ] **5.2 Tool review.** Every tool: clear name, docstring says when to use it, annotations right, output = structured + one-line summary, errors say how to fix. ✅ checklist done.
- [ ] **5.3 Full run.** All 6 scenarios in Claude Desktop from a fresh DB; fix what breaks; note screenshots for README. ✅ all pass; coverage ≥ 80% on services + algorithms.

### M6 — Remote hosting (3 sessions, → Dec 13)

- [ ] **6.0 Pick host** (15 min): Railway vs Render free + Supabase. Write decision in memory. **[OK]** for account signup.
- [ ] **6.1 HTTP mode.** `TokenVerifier` → user; `AuthSettings`; `transport_security` allowed hosts from env; `run --transport http`. ✅ two tokens act as two users via Inspector locally; no token → 401.
- [ ] **6.2 Admin endpoint for P2.** `POST /admin/users` (header `X-Admin-Key`) → `{user_id, token}`. ✅ tests: wrong key refused.
- [ ] **6.3 Postgres + Alembic.** `DATABASE_URL` for Postgres; first Alembic migration; CI also runs tests against a Postgres service container. ✅ green.
- [ ] **6.4 Docker + deploy.** Dockerfile (uv, non-root, uvicorn), secrets set on host. **[OK]** before deploying. ✅ two users edit the same event through the hosted URL.

### M7 — Ship (2 sessions, → Dec 15)

- [ ] **7.1 README.** Pitch, demo GIF, install (`uvx eventer-mcp`), Claude Desktop config (Windows + macOS), tool table, architecture diagram, design decisions (identity, money, algorithms, privacy).
- [ ] **7.2 PyPI.** Release workflow with trusted publishing on git tag. **[OK]** ✅ `uvx eventer-mcp` works on a clean machine.
- [ ] **7.3 MCP registry.** `server.json` + `mcp-publisher` (follow the registry quickstart at that time). **[OK]** ✅ listed.
- [ ] **7.4 Wrap-up.** LinkedIn post draft, add to LinkedIn Projects, update `PROJECT_MEMORY.md`. ✅ done.

---

## 4. Quality plan

**Rule: tests are written in the same task as the code.** A task is done only when its tests pass. There is no "testing phase" at the end.

| Layer | What it checks | When written | How it runs |
|---|---|---|---|
| 1. Algorithm tests | santa draw, split, settle-up are correct for *any* input | **before** the code (test-first) — rules are clear | pytest + hypothesis (random inputs), milliseconds |
| 2. Service tests | business rules + permissions (guest can't draw, non-member sees "not found") | with each service task | pytest, in-memory SQLite, one fresh DB per test |
| 3. MCP tests (e2e) | tools work as Claude calls them: names, inputs, outputs, error text; multi-user flows | at the end of each milestone's tool task | SDK in-memory `Client`, `identity.override()` to switch users |
| 4. Scenario checks | the real model understands the tools and does the right thing | end of each milestone + full run at 5.3, hosted at 6.4 | manual, the 6 scenarios in Claude Desktop |

Each service function gets at least: 1 happy path, 1 permission test, 1 edge case.

**Special tests (never cut):** Santa privacy leak test (3.3); settle-up property tests (4.1).

**Automatic gate — CI on every push/PR:** ruff (lint + format) → pyright (types) → pytest → coverage ≥ 80% on `services/` + `algorithms/` (build fails below). From M6 also against Postgres.

**Workflow:** one branch + PR per milestone; merge only when CI is green. Before merging, ask Claude Code to review the diff.

**Bugs:** found a bug by hand? First write a test that fails because of it, then fix. It can never come back silently.

**Final check (before M7 publish):**
1. Fresh clone → `uv sync` → all checks green.
2. `uvx eventer-mcp` on a clean machine/venv works with zero setup.
3. All 6 scenarios in Claude Desktop, local and against the hosted URL.
4. Two users on one event through the hosted URL; Santa privacy checked by hand.
5. Follow the README word for word as a stranger would.

---

**If behind:** cut 5.1 polish → Postgres (stay SQLite on a volume) → Windows CI. **Never cut** 3.3 privacy tests or 4.1 settle-up tests.
