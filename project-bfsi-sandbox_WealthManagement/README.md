# Chronos Wealth — Module 0

A working Python wealth-management simulator for the 5-day Enterprise AI and
GenAI training. Virtual money, synthetic time, real historical prices.
Educational software only — no real trades, no financial advice, and no LLM
key required.

```text
Investor side = deterministic finance app
Advisor side = deterministic, read-only client workspace
Python calculates. AI explains, retrieves, reasons, and assists.
```

Later course labs add those AI capabilities through Chronos's deterministic
data and policy boundaries; the baseline application does not simulate them.
Three optional standalone LlamaIndex lessons now live in
[chronos/ai/](chronos/ai/README.md): portfolio chat, handbook RAG, and a read-only
portfolio exploration agent. Each is a separate runnable file using local Ollama.
The investor dashboard exposes all three in **AI Demo → Chatbot | RAG | Agent**.
See [AI demo setup](chronos/ai/README.md#demo-the-ai-tabs).

New to this repository? Start with the [repository onboarding guide](repo_onboarding_guide/README.md)
for the project goals, setup, architecture, code-reading order, workflows, lab
status, tests, and troubleshooting.

## Stack

Python 3.13 · uv · FastAPI · Pydantic v2 · SQLAlchemy · SQLite · Pandas ·
yfinance · Streamlit · pytest

## Setup

```bash
uv sync
uv run python -m scripts.load_market_data   # yfinance -> CSV -> SQLite (one-time, needs network)
```

For the optional M12 Governed MCP extension, install its local MCP dependency:

```bash
uv sync --extra m12
```

The load script downloads AAPL, MSFT, SPY, GLD, JPM daily prices
(2020-01-01 to 2021-12-31) into `data/market/prices.csv` and the SQLite
`prices` table. The app never calls yfinance at runtime; if the database is
empty it loads the CSV, and if the CSV is missing it tells you to run the
script.

## Run

```bash
uv run uvicorn chronos.app_startup:app --reload    # API at http://127.0.0.1:8000
uv run streamlit run ui/app_navigation.py              # UI  at http://localhost:8501
```

Demo logins (no passwords):

```text
Alice Investor   alice@example.com    INVESTOR
Demo Advisor     advisor@example.com  ADVISOR
```

Alice starts with $100,000 virtual cash at simulated date 2020-06-01. Demo
Advisor can review Alice's portfolio through a read-only workspace.
Reset everything back to that state with:

```bash
uv run python -m scripts.reset_demo_data    # or POST /demo/reset
```

## Test

```bash
uv run pytest
```

Tests use `tests/fixtures/prices_sample.csv` and never call yfinance or the
network.

## Layout

```text
chronos/    flat business capabilities, pure rules, and API boundaries
  business_investor_accounts.py     authorized viewer/target and investor account lookup
  business_investor_trading.py       price, preview, apply and record virtual trades
  rules_trade_eligibility_and_cost.py           affordability decisions and average-cost arithmetic
  business_portfolio_valuation.py   current holdings valued at dated prices
  business_portfolio_history.py     save and read recorded portfolio values
  market_historical_prices.py         dated single/batch queries and symbol history
  market_price_import.py   one-time preparation, validation and import
  business_simulated_time.py      calendar steps and date advancement
  storage_sqlite_tables_and_sessions.py  ORM tables and transaction lifecycle
  api_routes_*.py          portfolio/actions and system HTTP boundaries
  api_schemas_requests_and_responses.py           shared screen and action contracts
  ai/                     independent optional chatbot, RAG, and agent lessons
ui/         shared view_shared_portfolio.py plus persona screens; client_backend_api.py owns HTTP
labs/       optional M1–M15 starters; their exercise behavior is unchanged
scripts/    one-time loading and intentional demo reset
tests/     offline rules, workflows, HTTP and transaction checks
data/      generated database and market CSV
```

Key rule everywhere: every price lookup uses the latest price on or before
the account's simulated date — no feature can see the future.

The live demo intentionally has two personas only: Alice Investor and Demo
Advisor. The advisor can view Alice's portfolio but cannot trade for her.


## Read the business workflow

Start with the investor journey test, follow its trade route into
`business_investor_trading.execute_investor_trade`, then read `rules_trade_eligibility_and_cost` and dated
`market_historical_prices` queries. Workflows obtain facts and apply changes; rule functions
calculate or decide without database, HTTP, or UI dependencies.

Preview and execution share eligibility rules. Snapshot and history share missing/
invalid-price behavior. Current valuation uses at most two SELECTs; history uses
at most three on loaded account inputs. Request owners commit or roll back the
complete operation. Trade amounts must be finite/positive and history limits
must be 1..1000; invalid imports are rejected before changing stored prices.

## Two screens, one portfolio

Both personas read `GET /portfolio?user_id=<viewer>`; the advisor opens Alice
directly. The response includes summary, holdings, assets, history, and trades.
`GET /market/history` fetches selected symbols together at the investor's date.
Each normal dashboard render uses two read requests. Only investors can preview
or execute trades and advance time. Advancing refreshes the screen and clears
the previous preview.

The API now has one schema module and two routers. Fragmented account/assets/
history reads and separate advisor endpoints have been removed. See the
[current API guide](repo_onboarding_guide/05_workflows_and_api.md) for contracts.
New market CSVs contain symbol/date/close/source; existing wider CSVs and legacy
optional price columns remain usable.

Read [the five business test stories](tests/README.md) to learn the application through concrete examples. Deeper checks live in `tests/engineering/`.

Recorded Portfolio Values stores one observation per account/date. Creation and
reset save the initial value; trades update today's observation; advancing time
saves the destination date. A month jump does not fill intervening dates. Existing
accounts without observations are initialized at their current date on startup;
price corrections preserve saved history.
