# Read the tests as business examples

Start with these five files, in this order:

| Order | File | Business question |
| --- | --- | --- |
| 1 | [test_trading.py](test_trading.py) | What happens to cash and shares when Alice buys or sells? |
| 2 | [test_portfolio.py](test_portfolio.py) | What is her investment worth, and what did she own in the past? |
| 3 | [test_time.py](test_time.py) | What changes when a week, month, or quarter passes? |
| 4 | [test_advisor_access.py](test_advisor_access.py) | Who can read a portfolio, and who can change it? |
| 5 | [test_investor_journey.py](test_investor_journey.py) | How do those rules work together through the API? |

Read the first trading example aloud: Alice starts with $100,000. She buys ten
AAPL shares at $108 each. Her cash becomes $98,920, and her holding records ten
shares with a $108 average cost. The tests call the actual application functions
and compare their results with these business facts.

## Understanding the setup

Pytest supplies a fixture when its name appears in a test's parameters. For
example, `def test_buy_reduces_cash_and_creates_holding(db, alice_account)`
asks for a database and Alice's account. You do not need to construct them in
every example. Their setup lives in [conftest.py](conftest.py).

- `db`: a fresh temporary SQLite database for each test, with offline prices.
- `alice` and `alice_account`: the investor and her $100,000 account, dated June 1, 2020.
- `advisor`: the demo advisor, who can read investor accounts.
- `bob`: a second investor, created only when an account-privacy test requests him.
- `client`: an HTTP test client using the same database as that test.

The [price fixture](fixtures/prices_sample.csv) contains AAPL and MSFT weekly
closes from May 4 through September 14, 2020. AAPL costs $108 on June 1, $110
on June 8, and $116 at the latest close available on July 1. Five assets have
metadata; only AAPL and MSFT have fixture prices. No test downloads prices or
uses the demo database.

`assert` checks a fact. `pytest.approx` compares calculated decimal values while
allowing small floating-point differences. `pytest.raises` checks a rejected
operation. `pytest.mark.parametrize` repeats an example with several inputs.

## Deeper engineering checks

After the business stories, read the relevant file in [engineering/](engineering/):

| File | Protection |
| --- | --- |
| [test_rules.py](engineering/test_rules.py) | Pure eligibility, cost basis, and infrastructure-free rule imports. |
| [test_validation.py](engineering/test_validation.py) | Invalid amounts, dates, prices, and missing historical facts. |
| [test_api.py](engineering/test_api.py) | HTTP errors, login, reset, field contracts, and dated market reads. |
| [test_market_loading.py](engineering/test_market_loading.py) | CSV normalization, minimal/legacy columns, and database upserts. |
| [test_market_queries.py](engineering/test_market_queries.py) | Exact/prior prices, future exclusion, supported symbols, and history limits. |
| [test_query_counts.py](engineering/test_query_counts.py) | Bounded SQL queries as holdings, dates, and requested symbols grow. |
| [test_transactions.py](engineering/test_transactions.py) | Real request commits, failed-write rollback, and preview non-mutation. |
| [test_ui.py](engineering/test_ui.py) | Offline Streamlit rendering, request counts, stale previews, and chat replies, clearing and connection errors. |
| [test_labs.py](engineering/test_labs.py) | Current starter registration and governed MCP helper behavior. |
| [test_ai.py](engineering/test_ai.py) | Optional LlamaIndex lessons and their HTTP endpoints: bounded chat, retrieved evidence, executed read-tool traces, limits, permission checks and visible errors, with network responses replaced. |

Business examples and boundary checks sometimes exercise the same rule for
different reasons. A direct trade check proves the calculation; an HTTP check
proves error translation; a transaction check proves failed writes leave no
partial records. Keep those distinct protections. Add an example to its existing
owner instead of repeating a complete journey in another file.

## Run the examples

```bash
# Five business stories
.venv/bin/python -m pytest tests/test_trading.py tests/test_portfolio.py tests/test_time.py tests/test_advisor_access.py tests/test_investor_journey.py -q

# Full suite, including engineering checks
.venv/bin/python -m pytest -q

# Read the names of each example as it runs
.venv/bin/python -m pytest tests/test_trading.py -v
```

Run serially in a separate process. The shared `client` fixture flushes changes;
real request commit/rollback is checked separately in `test_transactions.py`.
Streamlit tests establish rendered state, not browser layout. Live price downloads,
model outputs, and MCP transport need separate verification when changed.
Install `uv sync --extra ai` to run the standalone AI checks. Without that extra,
the optional AI test module is skipped; the baseline suite remains independent.
