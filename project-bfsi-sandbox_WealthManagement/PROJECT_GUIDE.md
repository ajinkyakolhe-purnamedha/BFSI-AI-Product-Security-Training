# Chronos Wealth — Project Guide

**Trace one business request first:**
[investor journey test](tests/test_investor_journey.py) →
[trade route](chronos/api_routes_portfolio.py) →
[trading workflow](chronos/business_investor_trading.py) →
[trade rules](chronos/rules_trade_eligibility_and_cost.py).

This is the technical reference for the standalone product security sandbox.
Use the [README](README.md) for startup and the [case study](CASE_STUDY.md) for
the assessment brief. This guide describes current code, not a module sequence.

## Architecture and ownership

```text
Streamlit screen
  → ui/client_backend_api.py
  → FastAPI route
  → account lookup and business workflow
  → SQLAlchemy / SQLite

AI route
  → investor account check
  → chatbot, handbook retrieval, or agent loop
  → local model service
  → answer, retrieved passages, or executed tool results
```

| Area | Source and responsibility |
| --- | --- |
| Application lifecycle | [app_startup.py](chronos/app_startup.py): register routes, create tables, seed missing demo data, load local prices, initialize missing value observations. |
| HTTP boundary | [Portfolio/AI routes](chronos/api_routes_portfolio.py), [system routes](chronos/api_routes_system.py), [schemas](chronos/api_schemas_requests_and_responses.py), and [error translation](chronos/api_error_translation.py). |
| Identity and account access | [Account lookup](chronos/business_investor_accounts.py), [role checks](chronos/app_business_errors_and_permissions.py), and [demo identities/reset](chronos/app_demo_data_and_reset.py). |
| Financial behavior | [Trading](chronos/business_investor_trading.py), [pure rules](chronos/rules_trade_eligibility_and_cost.py), [valuation](chronos/business_portfolio_valuation.py), [time](chronos/business_simulated_time.py), and [recorded values](chronos/business_portfolio_history.py). |
| Data and presentation | [Database](chronos/storage_sqlite_tables_and_sessions.py), [dated prices](chronos/market_historical_prices.py), [price import](chronos/market_price_import.py), [UI HTTP client](ui/client_backend_api.py), and [shared portfolio view](ui/view_shared_portfolio.py). |

The investor screen adds trade/time controls and AI tabs. The advisor screen
adds peer comparison. Both reuse the same portfolio presentation. Core financial
functions do not depend on the UI or AI modules.

## Data and startup

The seven mapped tables are:

| Table | Stored facts |
| --- | --- |
| `users`, `accounts` | Demo email/name/role; account ownership, cash, initial cash, and simulated date. |
| `assets`, `prices` | Supported securities; dated close/source, unique per symbol/date. |
| `holdings` | Shares and average cost, unique per account/symbol. |
| `trades` | Executed side, amount, shares, price, simulated date, and creation timestamp. |
| `portfolio_value_snapshots` | Cash, holdings value, and total value, unique per account/date. |

Default storage is `data/chronos.db`; `CHRONOS_DATABASE_URL` overrides it.
Startup seeds Alice Investor, Demo Advisor, Alice's $100,000 account dated
2020-06-01, and five assets. It preserves existing activity.

If the price table is empty, startup imports `data/market/prices.csv`. If local
prices are absent, run the preparation command in the README. The import script
downloads AAPL, MSFT, SPY, GLD, and JPM for the configured 2020–2021 window.
Normal application requests do not download market data.

Imports validate required fields, dates, finite positive closes, and duplicate
normalized symbol/date pairs. New CSVs use `symbol/date/close/source`; wider
legacy CSVs are accepted. Valuation uses raw close prices and floating-point
arithmetic, not production settlement or corporate-action accounting.

## Identity and authority

Login looks up an email and returns a demo user. It issues no authentication
token. Requests supply `user_id`; the backend looks up that user's role. These
role checks do not establish who actually sent the request.

For portfolio and market reads, optional `investor_id` identifies the target.
Investors can target themselves. Advisors default to Alice and can target other
investor accounts through the API. There is no assigned-client relationship check.
The UI exposes only the seeded Alice review.

Trading, time advancement, and AI endpoints require the submitted user ID to
belong to an investor. The reset endpoint has no caller identity parameter or
role check. Review these facts as part of the demo's security boundary; hidden
controls in a screen are not an API access control.

## Business workflows

### Preview and execute a trade

1. Parse a supported side and a finite positive amount; look up an investor account.
2. Resolve the supported symbol and latest close on or before the simulated date.
3. Calculate fractional shares and check cash for BUY or owned shares for SELL.
4. Preview returns price, shares, eligibility, and an explanation without changing
   financial records. Execution repeats the checks using current facts.
5. Execution updates cash/holdings, records the trade, and saves today's portfolio
   value. The request commits everything together or rolls back on failure.

Preview does not reserve money or lock a quote. The UI confirms with a new trade
request; the API does not require a previously issued preview token. A buy
recalculates weighted average cost; a partial sale preserves the remaining
holding's average cost.

### Value a portfolio and advance time

Portfolio value is cash plus shares multiplied by dated prices. Return is
measured against initial cash. Allocation includes cash in the total denominator.
Missing or invalid prices for a held symbol reject a new valuation.

A week adds seven days; a month or quarter adds calendar months and clamps the
end-of-month day. The operation rejects a destination beyond available market
data, records the destination's value, and returns before/after dates and values.
On non-trading dates, the latest earlier price is used.

Recorded history reads saved observations, not replayed trades. Same-day changes
update one observation; time jumps do not fill intervening dates. Correcting a
price does not rewrite saved history. Startup creates current observations for
legacy accounts without them, without reconstructing earlier dates.

### Review and compare

`GET /portfolio` returns summary, holdings, assets, recorded values, and trades.
`GET /market/history` supplies date-bounded prices for charts. Investors compare
normalized asset performance and best/worst growth; advisors compare a focus
symbol against the other assets' average.

### Reset

The script or reset endpoint clears holdings, trades, and value observations,
restores accounts to the starting cash/date, and records an initial cash-only
value. Users, assets, and downloaded prices remain. This changes the demo database;
verification tests use a separate temporary database.

## HTTP surface

| Method and path | Behavior |
| --- | --- |
| `GET /health` | Process health; not a full dependency check. |
| `GET /auth/demo-users`, `POST /auth/login` | List/select demo identities. |
| `GET /portfolio`, `GET /market/history` | Read the target portfolio or dated prices. |
| `POST /trades/preview`, `POST /trades` | Preview or execute a trade. |
| `POST /simulation/advance`, `POST /demo/reset` | Change the simulated date or reset investment activity. |
| `POST /portfolio/chat`, `/portfolio/rag`, `/portfolio/agent` | Run the three investor AI features. |

Market history permits one to five symbols and 1–1000 points per symbol.
Pydantic validates request shapes and limits. Domain rejections map to 400
(invalid business operation), 403 (wrong role), or 404 (missing record).
Interactive contracts are at `/docs`. There is no API homepage at `/`.

## AI flows and trust boundaries

Runtime/model setup is supplied separately offline. The implementations use
LlamaIndex and a local Ollama service. The ordinary dashboard does not call a
model; optional AI imports are loaded on demand.

| Feature | Implementation and enforced bounds |
| --- | --- |
| [Chatbot](chronos/ai/chatbot.py) | Refresh portfolio facts per question, assemble system context and user-supplied conversation history, call the model, and retain three completed turns. API history must alternate user/assistant pairs. |
| [RAG](chronos/ai/rag.py) | Chunk six built-in handbook documents, embed them into an in-memory index, retrieve two candidates, and retain passages scoring at least 0.55. With no qualifying passage, return without generation. |
| [Agent](chronos/ai/agent.py) | Expose `read_my_portfolio` and `read_my_value_history`. Fix account identity in closures; reject unknown tools, nonempty arguments, and batches exceeding four total calls before dispatch. |

RAG's API index is built on the first question and cached until restart. Its
handbook is shared static content; there is no document-upload or tenant-specific
retrieval workflow. Sources include passage text and similarity scores. Prompting
asks for citations; it does not prove factual support.

The agent's history tool returns the last five observations and a Python-calculated
change. The model can choose reads but cannot select a different account through
tool arguments. Returned traces describe completed tool calls, not hidden model
reasoning or durable audit records. No trade, reset, or time-change tools exist.

Review user questions, request-supplied chat history, handbook passages, tool
results, and generated output as separate inputs/outputs. Distinguish prompt
instructions from Python-enforced authority. AI modules print context/retrieval/
tool information to the process output; consider those outputs when tracing data.

Missing optional packages and handled model-service failures return visible
503 errors. Questions have a 2,000-character limit; chat history has at most six
messages with per-message limits. Model-output quality, injection resistance,
and resource use still need runtime assessment.

**MCP is planned for later.** There is no current MCP server. Client messaging,
advisor approvals, risk classification, security-scanner ingestion, and release
approval automation are also not implemented application workflows.

## Verification and evidence

Start with the five business stories under `tests/`: trading, portfolio, time,
advisor access, and the investor journey. Engineering tests cover HTTP contracts,
validation, transactions, query counts, market import, UI rendering, and AI flows.
See the [test guide](tests/README.md) for focused commands.

```bash
uv run python -m pytest -q
```

For optional AI checks after the separately provided setup:

```bash
uv run --extra ai python -m pytest -q
```

Tests use temporary SQLite databases and fixture prices. AI tests substitute
model/network responses; they do not prove live-model safety. Query-count tests
check bounded reads, while transaction tests check actual commit/rollback behavior.
UI tests check rendered state, not a full browser security assessment.

For each review claim, preserve the relevant input, endpoint/function, expected
invariant, observed response/state, and test conditions. Record whether evidence
came from source inspection, an isolated test, or a live local request.
