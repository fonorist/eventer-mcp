# Project 1 — eventer-mcp (Event MCP Server): Agent Brief

> Starting point for any agent (Claude Code etc.) picking up Project 1.
> Read this file, `PLAN.md` (architecture, setup, step-by-step tasks) and `PROJECT_MEMORY.md` first. Keep replies to George short.
> Status: spec + plan agreed 2026-11-23, no code yet. Target ship date: ~2026-12-15 (evenings, ~2.5 h).

---

## 1. Why this project exists

George (full-stack dev, strongest in Java/C++/Python backend) is building a 6-month portfolio to get hired as a
**Full-Stack AI Engineer** (Claude API, agents, MCP). Project 1 must prove he can design, test, host and publish a
real MCP server, not a toy wrapper.

It also has a second job: **it becomes the tool layer for Project 2** — a web-based "event agent" used by real guests
at George's New Year party (Dec 31, 2026). Project 2's backend is the **primary consumer** of this server; recruiters
trying it in Claude Desktop are secondary. Guests never call the MCP server directly. So: design it as a reusable backend, not a demo.

## 2. One-line pitch

A multi-user MCP server for planning group events: guests, who-brings-what, shopping list, shared expenses with
settle-up, and a private Secret Santa — usable from Claude Desktop / Claude Code, and as the tool layer for an AI event agent.

## 3. Differentiation (checked 2026-11-23)

- Existing: "Gatherings MCP" (abutbul) — expense splitting only, single user, stdio only.
- The MCP registry has dozens of "events" servers, almost all for *discovering* events — ours is for *planning* them.
- Ours adds:
  1. **Multi-user identity + permissions** — every call acts as a specific user; e.g. a guest sees only their own Secret Santa target; only the host can run the draw. This is the main interview talking point.
  2. **Full planning** — items, claims, shopping list, Secret Santa, wishlists, expenses.
  3. **Remote hosting** (Streamable HTTP) in addition to stdio.
  4. **Engineering quality** — layered design, tested algorithms, CI, published package + registry entry.

## 4. Scope

### In scope (v1)
Events, invites, guests, items/claims, shopping list, Secret Santa (setup, exclusions, draw, private reveal, wishlists),
expenses, balances, settle-up, payments, two resources, one prompt, stdio + Streamable HTTP, admin endpoint for Project 2, publish.

### Non-goals (v1) — do NOT build
- No LLM calls inside the server (the client is the AI; the server is deterministic).
- No web UI (that's Project 2).
- No Spotify, no receipt OCR, no notifications/email, no real payments.
- No full OAuth flow unless time allows (see §8).

## 5. User scenarios (use these as end-to-end tests in Claude Desktop)

1. **Host plans:** "Create a New Year party on Dec 31 at my place, budget ₪1500, and give me an invite code."
2. **Guest joins:** "Join event with code X7K2P9 as Dana, I'm vegetarian."
3. **Who brings what:** "What's still missing? I'll bring 2 bottles of wine and the salad."
4. **Shopping:** "Show the shopping list grouped by who's buying, with estimated cost."
5. **Expenses:** "I paid ₪340 for meat, split between everyone except Dana." → "Who owes whom? Minimum transfers."
6. **Secret Santa:** Host: "Set up Secret Santa, ₪100 budget, Alex and Maya are a couple so exclude them, then draw."
   Guest: "Who's my Secret Santa target and what's on their wishlist?" — must reveal only the caller's own target.

## 6. Architecture

Full version with call flow, identity table and repo layout: `PLAN.md` §1.

```
MCP client (Claude Desktop / Claude Code / Project 2 backend)
        │  stdio  or  Streamable HTTP (+ bearer token)
        ▼
tools/      — thin MCP layer: tool/resource/prompt definitions, input parsing, identity lookup, error mapping
        ▼
services/   — pure Python business logic + permission checks (reusable directly by Project 2)
        ▼
algorithms/ — pure functions: santa_draw, split, settle_up (no DB, fully unit/property tested)
        ▼
db.py / models.py — SQLModel; SQLite locally, Postgres when hosted
```

Rules:
- MCP layer has **no business logic**; services have **no MCP imports**.
- Identity comes from the **transport/auth context, never from a tool argument** (never let the model pass "act as user X").
- Money stored as **integers in minor units (agorot)** + currency code (default ILS). Never floats.
- All IDs are short, human-friendly strings (e.g. `evt_8k2p`), safe to show to the model.

## 7. Data model (draft)

- **User**: id, display_name, token_hash, created_at
- **Event**: id, title, date, location, budget_minor, currency, notes, host_user_id, created_at
- **Invite**: code, event_id, created_by, expires_at, max_uses, uses
- **Membership**: event_id, user_id, role (host|guest), dietary, notes, joined_at
- **Item**: id, event_id, name, quantity, unit, category, est_cost_minor, created_by, status (open|claimed|done)
- **Claim**: item_id, user_id, quantity
- **Expense**: id, event_id, paid_by, amount_minor, description, created_at
- **ExpenseShare**: expense_id, user_id, share_minor (sum == amount; distribute remainder deterministically)
- **Payment**: id, event_id, from_user, to_user, amount_minor, created_at
- **SantaConfig**: event_id, budget_minor, status (setup|drawn), drawn_at
- **SantaExclusion**: event_id, user_a, user_b (symmetric)
- **SantaParticipant**: event_id, user_id, wishlist
- **SantaPair**: event_id, giver_id, receiver_id  (never returned except giver → own receiver)

## 8. Identity & auth (decided 2026-11-23)

- **Per-user bearer tokens** for everyone. Store only SHA-256 hashes; show a token once.
  - stdio: token from env `EVENTER_TOKEN`; if unset, auto-create a default local user (zero setup for recruiters).
  - HTTP: SDK v2 `TokenVerifier` resolves `Authorization: Bearer <token>` → user; tools read it via `get_access_token()`.
    The stdio fallback is disabled in HTTP mode.
  - Users created via CLI (`eventer-mcp user create --name Dana`) or, for Project 2, an admin endpoint protected by
    `EVENTER_ADMIN_KEY`. `join_event` does **not** create users or tokens.
  - Project 2 creates a user per guest at signup, stores that guest's token, and calls the server with it.
- **Stretch:** MCP-spec OAuth so guests can add it as a Claude custom connector. Verify current SDK v2 auth support and Claude connector requirements before starting — don't assume.

## 9. Tools (v1)

Annotate each tool (read-only / destructive / idempotent hints). Return structured output (Pydantic models)
plus a short human-readable summary. Errors must be actionable for the model ("Only the host can run the draw").

| Area | Tool | Who | Notes |
|---|---|---|---|
| Events | `create_event(title, date, location?, budget?, currency?, notes?)` | any user | caller becomes host |
| | `list_my_events()` | user | read-only |
| | `get_event(event_id)` | member | summary: guests, item stats, budget used, santa status |
| | `update_event(event_id, …)` | host | |
| | `create_invite(event_id, max_uses?, expires_in_days?)` | host | returns code |
| | `join_event(invite_code, display_name?, dietary?)` | any user | |
| Guests | `list_guests(event_id)` | member | includes dietary |
| | `update_my_membership(event_id, dietary?, notes?)` | member | |
| | `remove_guest(event_id, user_id)` | host | destructive |
| Items | `add_item(event_id, name, quantity, unit?, category?, est_cost?)` | member | dedupe hint if same name exists |
| | `claim_item(item_id, quantity?)` / `unclaim_item(item_id)` | member | partial claims allowed |
| | `mark_item_done(item_id)` | claimer or host | |
| | `delete_item(item_id)` | creator or host | destructive |
| | `shopping_list(event_id, group_by="assignee"\|"category", only_open?)` | member | totals of est. cost |
| Santa | `santa_setup(event_id, budget?, participants?, exclusions?)` | host | default participants = all members |
| | `santa_draw(event_id)` | host | refuses if already drawn unless `santa_reset(confirm=True)` first |
| | `santa_reset(event_id, confirm)` | host | destructive |
| | `my_santa_target(event_id)` | participant | ONLY caller's own receiver + their wishlist |
| | `set_wishlist(event_id, text)` | participant | |
| | `santa_status(event_id)` | member | drawn yes/no, participant count — never pairs |
| Expenses | `add_expense(event_id, amount, description, split_among?, exclude?)` | member | payer = caller; default split = all members |
| | `list_expenses(event_id)` | member | |
| | `balances(event_id)` | member | net per person (expenses − shares ± payments) |
| | `settle_up(event_id)` | member | minimal list of transfers |
| | `record_payment(event_id, to_user, amount)` | member | payer = caller |

**Resources:** `event://{event_id}/summary`, `event://{event_id}/shopping-list`
**Prompt:** `plan_event` — guides the model through creating an event, inviting guests, building the list, and Santa setup.

Privacy rule to test hard: no tool, resource or error message may leak another person's Santa pair — including the host's.

## 10. Algorithms

- **settle_up:** compute net balances; greedy-match largest debtor with largest creditor → at most n−1 transfers.
  (True minimum is NP-hard; document that greedy is the standard practical choice.) Deterministic ordering for tests.
- **santa_draw:** random assignment where nobody gets themselves or an excluded partner (symmetric exclusions).
  Shuffle + backtracking; seedable RNG for tests; clear error if no valid assignment exists
  (e.g. 2 people who exclude each other). Property-test with `hypothesis`: valid permutation, no self, no exclusions.
- **Split remainders:** when amount doesn't divide evenly, distribute leftover agorot deterministically (e.g. by member order).

## 11. Tech stack

- Python 3.12+, `uv` for env/packaging. Dev machine: Windows.
- **Official MCP Python SDK v2** (`mcp>=2.3,<3`, class `MCPServer` from `mcp.server`; `FastMCP` was renamed).
  v1 snippets (`mcp.server.fastmcp`) are outdated. Docs: https://py.sdk.modelcontextprotocol.io/
- SQLModel (SQLAlchemy) + SQLite; Postgres when hosted; Alembic from M6
- pytest, anyio, hypothesis, pytest-cov; ruff (lint+format); pyright (basic)
- GitHub Actions CI (ubuntu + windows); Dockerfile for hosting
- Test with MCP Inspector, then Claude Desktop

## 12. Repo layout

See `PLAN.md` §1.5. Repo/package name: `eventer-mcp` (import name `eventer_mcp`).

## 13. Plan & acceptance criteria

Milestones M0–M7 with step-by-step tasks and done-checks: `PLAN.md` §3.
M0 setup (→Nov 25) · M1 events/identity/invites (→Nov 28) · M2 items (→Dec 1) · M3 Santa (→Dec 4) ·
M4 expenses (→Dec 8) · M5 Claude polish (→Dec 10) · M6 hosting (→Dec 13) · M7 ship (→Dec 15).

If behind schedule, cut in this order: OAuth stretch → resources/prompt polish → Postgres (stay on SQLite on a volume).
Never cut tests for Santa privacy or settle-up.

## 14. Definition of done

- [ ] Published package (`uvx eventer-mcp` works) + MCP registry listing
- [ ] Hosted HTTP endpoint working for multiple users
- [ ] README: pitch, demo GIF, install for Claude Desktop/Code, tool table, architecture diagram, design decisions (identity, money, algorithms)
- [ ] CI green; ≥80% coverage on services + algorithms
- [ ] All 6 scenarios verified in Claude Desktop
- [ ] Project added to LinkedIn Projects + one post

## 15. How Project 2 will use this

Project 2 (web event agent, Dec 16–31) runs Claude via the API with this server as its tool layer — through the
Messages API MCP connector against the hosted URL, using each guest's own token. Keep the service layer
importable and the tool descriptions model-friendly; Project 2's eval suite will exercise these same tools.

## 16. Open questions

Resolved 2026-11-23: name = `eventer-mcp`; code on George's Windows PC (`D:\projects\eventer-mcp`) + GitHub,
George implements with Claude Code; users via CLI/admin endpoint only; dev OS = Windows.
Still open: hosting (Railway vs Render+Supabase) — decide at task 6.0.

## 17. Working agreements for agents

- Short replies; show progress via the task list.
- Don't publish to PyPI/registry, deploy, or create accounts without George's explicit OK (they use his accounts).
- Never commit secrets/tokens; use `.env` + `.gitignore`.
- Update `PROJECT_MEMORY.md` (progress log + decisions) at the end of each working session.
