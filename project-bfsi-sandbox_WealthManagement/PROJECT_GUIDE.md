# Chronos Wealth: Project Guide

This guide describes the capstone **as implemented in this folder**. It separates
working application behavior from lab goals. The course may describe later AI
features, but their description alone does not make them part of this app.

## 1. Business purpose and scope

Chronos Wealth is an educational wealth-management simulator for the *AI
Application Engineering with Python* curriculum. It uses virtual money,
historical market prices, and an account-specific simulated date. It does not
place real trades or give financial advice.

The baseline application gives learners a deterministic system of record on
which later AI exercises can build. Its governing division of responsibility
is:

- **Python owns** financial facts and calculations, data access, permissions,
  trade execution, and other consequential actions.
- **AI lab targets** include explanation, retrieval, classification, drafting,
  and bounded tools. Optional investor AI Demo tabs explain portfolio facts,
  retrieve handbook passages, and explore portfolios through read-only tools.
- **Advisors read portfolios**; investor-only workflows own trades and time
  changes. Client-visible advisor drafts and approvals remain future work.

### People and the demo journey

| Persona | Demo identity | Current capabilities |
| --- | --- | --- |
| Investor | Alice Investor, `alice@example.com` | View account and portfolio, compare market performance, preview and execute virtual buys/sells, inspect trade and value history, advance simulated time. |
| Advisor | Demo Advisor, `advisor@example.com` | Open Alice's portfolio directly and inspect its history and performance. No advisor trade route exists. |

The seeded investor account starts with **$100,000 virtual cash**, no holdings,
and simulated date **2020-06-01**. A common journey is to log in as Alice, buy
an asset, advance time, inspect the resulting valuation, then log in as Demo
Advisor to view the same portfolio. `POST /demo/reset` or
`python -m scripts.reset_demo_data` restores the seeded investor account.

These are demo identities: login selects an email without a password, and API
requests carry caller-supplied user IDs. Role and viewer/target checks demonstrate
business permissions; they do not provide production authentication.

## 2. What works today

| Area | Implemented behavior |
| --- | --- |
| Market data | One-time yfinance download script normalizes symbol/date/close/source to CSV and SQLite. At runtime the app reads local data; it does not call yfinance. |
| Pricing | Single and batch lookups select the latest available close on or before the account's simulated date. Missing or invalid held-symbol prices raise an explicit error when valuing a portfolio. |
| Portfolio | Cash plus marked-to-market holdings, cost basis, unrealized gain/loss, allocation percentages, and total return relative to initial cash. |
| Trading | Dollar-based BUY/SELL requests, fractional shares, non-writing preview, cash/share checks, average-cost updates, and recorded trade history. |
| Simulated time | Advance by one week, one calendar month, or one calendar quarter; reject dates beyond available market data. |
| Account history | Read saved portfolio values from creation, trades, and time advances. One observation per account/date; no trade replay or intervening-date backfill. |
| Advisor workspace | The same portfolio screen facts as the investor, with no mutation controls. |
| User interface | Streamlit investor and advisor screens, performance charts, and visible lab starter pages. |

### The point-in-time rule

Trade pricing uses `get_latest_price_on_or_before_date()`; current snapshots use
`get_latest_prices_on_or_before_date()` to load prices in a batch. Both live in
`chronos/market_historical_prices.py`. Each lookup filters by
`Price.date <= account.simulated_date` and takes the latest matching row.
Market history and account-value history also end at the simulated date.
This rule prevents future prices from leaking into an earlier simulation.

New valuations require finite, positive prices for every held symbol. Recorded
history reads saved values without querying market prices, so missing prices or
later price corrections do not erase or recalculate existing observations.

The app values positions with the **raw `close`** field, not
`adjusted_close`. It uses floating-point amounts and shares because this is a
teaching simulator; it is not a production ledger with decimal-money,
corporate-action, or settlement accounting.

## 3. Technical architecture

```text
Streamlit screen (ui/)
    -> ui/client_backend_api.py (HTTP boundary)
    -> FastAPI route (chronos/api_routes_*.py)
    -> deterministic business function (chronos/*.py)
    -> SQLAlchemy session / SQLite tables
    -> historical prices bounded by the account's simulated date

Optional lab page (labs/)
    -> starter run() function; currently unimplemented for M1-M15
```

### Components and responsibilities

| Location | Responsibility |
| --- | --- |
| `chronos/app_startup.py` | FastAPI application, route registration, startup table creation and seeding, local-price loading, and initialization of missing portfolio observations. |
| `chronos/storage_sqlite_tables_and_sessions.py` | SQLAlchemy models, SQLite engine, sessions, and configured database path. |
| `chronos/app_business_errors_and_permissions.py` | Domain errors and investor/advisor role checks, without HTTP dependencies. |
| `chronos/api_error_translation.py` | Domain-to-HTTP error translation used by both routers. |
| `chronos/app_demo_data_and_reset.py` | Demo identities and assets, idempotent seed, login lookup, account reset. |
| `chronos/market_historical_prices.py` | Dated single/batch price queries and symbol history. |
| `chronos/market_price_import.py` | Download, normalize, validate and import historical prices. |
| `chronos/business_investor_accounts.py` | Authorized viewer/target reads and investor-only account lookup. |
| `chronos/business_portfolio_valuation.py` | Batch-value current holdings, build the shared screen response, and record current values or initialize missing observations. |
| `chronos/business_portfolio_history.py` | Save and read portfolio values at recorded dates. |
| `chronos/business_simulated_time.py` | Calendar steps and permitted date advancement. |
| `chronos/business_investor_trading.py` | Trade preview, execution, holdings updates, and recorded portfolio values. |
| `chronos/rules_trade_eligibility_and_cost.py` | Immutable priced trades, shared affordability decisions, and average-cost calculations using only standard-library types. |
| `chronos/api_schemas_requests_and_responses.py` | Pydantic request and response contracts. |
| `chronos/api_routes_*.py` | Thin HTTP endpoints grouped by portfolio/actions and system. |
| `ui/client_backend_api.py` | The UI's centralized HTTP client. |
| `ui/view_shared_portfolio.py` | Shared summary, holdings, recorded-value chart, and trade-history presentation for both personas. |
| `ui/screen_*.py`, `ui/charts_asset_performance.py` | Streamlit presentation and chart construction. |
| `labs/` | Optional student-facing lab registry and starters. |
| `chronos/ai/` | Three independent LlamaIndex/Ollama lessons reused by the investor AI Demo tabs, each also runnable in the terminal. |
| `scripts/` | One-time market-data import and demo reset commands. |
| `tests/` | Five business stories, with infrastructure, API, transaction, query-count, validation, and UI checks in `tests/engineering/`. |

Business workflows obtain facts and apply changes; pure trade rules calculate
or decide without ORM, HTTP, or UI imports. Preview and execution share the same
eligibility function. Workflows flush changes; the outer request or script owns
commit and rollback for the complete operation.

### Persistence model

The current SQLAlchemy model defines seven tables:

- `users`: demo email, name, and role.
- `accounts`: user ownership, virtual cash, initial cash, and simulated date.
- `assets`: the five supported symbols and descriptive classifications.
- `prices`: symbol, date, close, and source, with a unique symbol/date pair.
- `holdings`: account/symbol shares and average cost, unique per pair.
- `trades`: the executed side, shares, price, dollar amount, simulated date,
  and creation timestamp.
- `portfolio_value_snapshots`: cash, holdings value, and total value, unique per account/date.

`CHRONOS_DATABASE_URL` can override the default SQLite URL. Otherwise the
database is `data/chronos.db`. The runtime first seeds missing demo users,
Alice's account, and supported assets. If the `prices` table is empty, it
imports `data/market/prices.csv`; if both are absent, startup fails with setup
instructions. The database and price CSV are local generated data ignored by
Git. Startup adds the snapshot table and records current values for accounts
without observations, preserving existing trades and holdings. Each such account
gets an observation at its current simulated date; startup does not reconstruct
its past values. Old local databases can contain tables no longer mapped by
current code; their presence does not imply a current feature.

### Market-data design

`scripts/load_market_data.py` downloads AAPL, MSFT, SPY, GLD, and JPM for
2020-01-01 through 2021-12-31 (the download end is exclusive), normalizes the
response, saves a portable CSV, and loads or updates SQLite price rows. This
one-time preparation needs network access. Application startup and tests use
local data. The present local full CSV contains 2,520 rows: 504 trading dates
per symbol, from 2020-01-02 through 2021-12-30. A fresh checkout needs that
CSV or a populated database before the API can start.

The test fixture is deliberately different from the full price data: it has
40 weekly rows for AAPL and MSFT. For example, its 2020-06-01 AAPL close is
`108`, while the full local market CSV has approximately `80.46`. Test
numbers therefore describe fixture behavior, not the full demo market.

New CSVs and the current price model use `symbol/date/close/source`. The importer
accepts wider legacy CSVs, and existing optional OHLC, adjusted-close, and volume
columns in SQLite are left untouched. Imports strip symbol whitespace and uppercase
symbols; duplicate checks use those normalized symbols. Required fields, dates,
finite positive closes, and duplicate symbol/date keys are validated before changing prices.

## 4. Main workflows and API

### Investor trade

1. A route checks that the submitted user ID belongs to an investor and
   locates the investor's account.
2. The business function validates the supported symbol and resolves one
   close on or before the account's simulated date.
3. Dollar amount divided by price gives fractional shares. Preview returns
   price, shares, validity, and an explanation without writing rows.
4. Preview and execution use the same pure eligibility rule to check cash for
   a BUY or owned shares for a SELL. Execution updates cash and the holding,
   records the trade, and saves the date's portfolio value. The request-scoped
   database session commits on success and rolls back on an exception, including
   a failure while valuing or saving the observation.

The UI provides a preview/confirm flow, but confirmation sends a new trade
request and the server resolves price again. A preview is informational; it
does not reserve funds or lock a quote.

### Simulated time and reporting

Advancing time calculates the current value, updates the date, then values and
records the destination date. Weeks add seven days; months and quarters use calendar months
and clamp month-end days. Portfolio valuation uses the most recent prior
trading price when the simulated date falls on a non-trading day.

Total return is `(current portfolio value - initial cash) / initial cash`.
The Recorded Portfolio Values chart reads saved observations from creation, trades,
and time advances. Same-day trades update one observation; they do not create
multiple chart points. A month jump records its destination, not intervening dates. The
investor chart compares normalized symbol prices; the advisor chart compares
one symbol with an average of the other supported symbols. Chart data is
fetched through the date-bounded market-history endpoint.

Both dashboards render the same shared portfolio view. The advisor opens Alice
directly and has no client-list selector, trading controls, or time controls.
Normal dashboard renders use two read requests: one portfolio response and one
batched market-history response. Changing trade inputs clears an old preview;
advancing time clears it, retains a before/after notice, and reruns the screen.

### HTTP endpoints

| Method and path | Purpose |
| --- | --- |
| `GET /health` | Basic process health. |
| `GET /auth/demo-users`, `POST /auth/login` | List or select a demo identity. |
| `POST /demo/reset` | Reset investor accounts, holdings, trades, and recorded values. |
| `GET /portfolio` | One screen response for the viewer: summary, holdings, assets, history, and trades. |
| `GET /market/history` | Batch of requested symbols, bounded by each symbol's window and the target date. |
| `POST /trades/preview`, `POST /trades` | Preview and execute investor-only trades. |
| `POST /portfolio/chat` | Explain fresh investor portfolio facts with up to three completed conversation turns. |
| `POST /portfolio/rag` | Answer from the inline handbook and return retrieved passages and similarity scores. |
| `POST /portfolio/agent` | Explore investor facts through bounded read tools and return executed calls/results. |
| `POST /simulation/advance` | Advance time and return previous/current dates and total values. |

`GET /portfolio` uses `user_id` for the viewer and optional `investor_id` for
the target. Investors can read only themselves; advisors default to Alice and
can explicitly target another investor through the API. `GET /market/history`
uses the same viewer/target checks and accepts one to five symbols with a
`trading_days` limit of 1..1000 per symbol. It returns only available points
through the target's simulated date; a symbol without history has an empty list.

The portfolio response includes investor name, cash, holdings and total values,
returns, valued holdings, assets, recorded history, and trades. The time-advance
response contains `previous_date`, `current_date`, `previous_value`, and
`current_value`. These shared contracts replace the former fragmented reads and
separate advisor endpoints; old clients must adopt the current routes and shapes.

Pydantic rejects invalid trade sides, non-finite/nonpositive amounts, unknown
simulation steps and history limits outside 1..1000. Domain errors become
404, 403 or 400 responses. Trade and time-change lookup always requires an
investor. Missing or invalid held-symbol prices reject a new valuation; saved
history remains readable independently of current market data.

## 5. AI and lab implementation status

The optional [AI lessons](chronos/ai/README.md) remain separate from the course lab
buttons. The investor **AI Demo → Chatbot** tab calls `chatbot.py` through
`POST /portfolio/chat`, carrying bounded history in the UI session. The endpoint
checks the investor role before loading the optional model packages and returns
clear connection errors. The RAG and Agent tabs use `POST /portfolio/rag` and
`POST /portfolio/agent`, showing retrieved handbook passages and executed tool
results. All three generation models default to `qwen35-2b-chronos:latest`;
`CHRONOS_CHAT_MODEL`, `CHRONOS_RAG_MODEL`, and `CHRONOS_AGENT_MODEL` independently
override them. `CHRONOS_EMBEDDING_MODEL` defaults to `nomic-embed-text:latest`.
`CHRONOS_OLLAMA_URL` selects the local server. The static handbook index is built
on the first RAG question and reused until the API restarts.
`chatbot.py` supplies current investor
facts and bounded chat history; `rag.py` embeds and retrieves an inline handbook;
`agent.py` explicitly validates and executes a bounded loop over current-portfolio
and recorded-value-history tools. Each file owns its own model configuration and
can be run with `uv run --extra ai python -m chronos.ai.<lesson>`. They never
trade, advance time, or commit financial records. Offline tests verify orchestration;
live model answer quality must be evaluated separately.

All fifteen lab `run()` functions remain starters that raise
`NotImplementedError`. Beyond the optional investor AI demos, the application has
no curriculum policy retriever, classifier inference, advisor agent workflow, durable advisor approval, or completed
governed MCP read. Registering a lab page does not implement its target behavior.

M12 additionally supplies a local stdio MCP client/server scaffold in
`labs/m12_governed_mcp/`. Its portfolio reader uses the real deterministic core,
but host admission, assigned-client authorization, result-bound validation, and
audit controls remain incomplete. The supplied host admits no tools, and the
progress check is expected to fail until the exercise is implemented.

See [AI labs and current gaps](repo_onboarding_guide/06_ai_labs_and_current_gaps.md)
for the module-by-module teaching targets. Core `prompt_specs` describe current
requirements; the future lab catalog does not establish implemented features.

## 6. Running and verifying

The project targets Python 3.13 and uses `uv`. From this directory:

```bash
uv sync
uv run python -m scripts.load_market_data  # only if local prices are absent; uses yfinance
uv run uvicorn chronos.app_startup:app --reload
uv run streamlit run ui/app_navigation.py
```

The API defaults to `http://127.0.0.1:8000`; the UI defaults to
`http://localhost:8501`. Set `CHRONOS_API_URL` to point the UI at another API
address. Start the API before the UI.

Run the offline capstone suite with:

```bash
uv run python -m pytest -q
```

The full suite passed **127 tests** during verification on **2026-10-05**.
Tests create an isolated temporary SQLite database and load
`tests/fixtures/prices_sample.csv`; they do not download prices, reset the demo
database, or call external APIs. The suite covers pure rules, core workflows, real request commits/rollbacks,
bounded query counts, HTTP behavior, and fixture-backed Streamlit rendering and
time refresh. This is offline UI verification, not a live browser/network
journey or evidence that future AI behavior is implemented.

Query-count checks establish at most two SELECTs for current valuation on a
loaded account, one for recorded history, and one for batched symbol histories.
Transaction tests check that cash, holdings, trades, dates, and recorded values
commit or roll back together, including snapshot failures and legacy startup.
Read [tests/README.md](tests/README.md) for the business stories and engineering
boundaries.

For the optional M12 scaffold, install the extra and run its actual local
client:

```bash
uv sync --extra m12
uv run --extra m12 python -m labs.m12_governed_mcp.client
```

The reviewed output showed `DISCOVERED` tools, `MODEL_VISIBLE: []`, and
`host_admission_not_implemented` for all scenarios. That is evidence of a
working MCP connection and an incomplete governance exercise, not evidence
of a completed portfolio read.

## 7. Design boundaries and next extensions

The small modules make intended extension points clear: add an AI capability
outside the financial calculation functions; obtain facts through read-only,
scoped tools; keep permissions and action decisions in Python; and provide
observable runtime evidence when claiming a model, retriever, tool, MCP, or
agent step. Advisor content intended for a client needs the durable human
approval workflow specified by the repository instructions before it can be
shown as approved content.

This guide is a snapshot of the capstone folder. For curriculum changes, the
applicable instructor LOD, courseware standards, delivered slides, code-alongs,
and matching tests determine the teaching contract. Recheck those sources
before turning a lab starter into a delivered module.


## Read one business journey first

Follow the investor BUY in `tests/test_investor_journey.py`, then
`api_routes_portfolio.execute_trade`, `business_investor_trading.execute_investor_trade`,
`rules_trade_eligibility_and_cost.trade_rejection_reason`, and `market_historical_prices` dated queries.
Read `business_portfolio_valuation` and `business_portfolio_history` next, with their rule and
behavior tests. Database and HTTP details support this story rather than define it.
