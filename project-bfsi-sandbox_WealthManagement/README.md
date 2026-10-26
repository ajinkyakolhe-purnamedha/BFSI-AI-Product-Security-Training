# Chronos Wealth

**Start with [Run the app](#run-the-app), then try the [business workflows](#business-workflows).**

A standalone wealth-management sandbox for product security training. Explore
investor and advisor workflows, an API, and chatbot, RAG, and agent features.
All money and trades are virtual.

## Run the app

You need **Python 3.13** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)**.
Run commands from `project-bfsi-sandbox_WealthManagement`.

### 1. Install dependencies — first time only

```bash
uv sync
```

### 2. Download market data — first time only, requires internet

```bash
uv run python -m scripts.load_market_data
```

### 3. Start the backend — Terminal 1

```bash
uv run uvicorn chronos.app_startup:app --reload
```

Leave it running. [Check backend health](http://127.0.0.1:8000/health) should show `{"status":"ok"}`.

### 4. Start the UI — Terminal 2

Open a second terminal in the **same folder**:

```bash
uv run streamlit run ui/app_navigation.py
```

Leave both terminals running. Stop each with `Ctrl+C`.

### 5. Open the app

Open **[http://localhost:8501](http://localhost:8501)** and select a user. No password is required.

| User | Email | What they can do |
| --- | --- | --- |
| Alice Investor | alice@example.com | Trade, advance time, review her portfolio, and use AI features. |
| Demo Advisor | advisor@example.com | Review Alice’s portfolio and performance. |

Alice starts with **$100,000 on June 1, 2020**.

**Cannot open the app?** Check Terminal 2. Use **8501**, not the backend's homepage
on 8000. [API documentation](http://127.0.0.1:8000/docs) is available separately.

## What the app does

| Feature | Capability |
| --- | --- |
| Portfolio | Cash, holdings, value, return, allocation, cost, and unrealized gains/losses. |
| Trading | Preview and confirm dollar-based buys/sells, including fractional shares. |
| Time and history | Advance a week, month, or quarter; inspect trades and recorded portfolio values. |
| Market comparison | Compare AAPL, MSFT, SPY, GLD, and JPM; review a symbol against peers. |
| Advisor review | Inspect Alice's portfolio and performance without trading or advancing time. |

Python calculates financial results using prices available at the simulated date.
Activity persists locally between runs. The backend exposes the workflows through HTTP.

**AI features:** chatbot explains portfolio facts; RAG answers from the investing
handbook with sources; agent explores portfolio facts through read-only tools.
**AI setup will be provided separately offline. MCP will be added later.**

## Business workflows

1. **Invest:** Alice → choose BUY/SELL, symbol, and amount → preview → confirm →
   inspect cash, holdings, and trade history.
2. **Track performance:** advance time → inspect the value change and history →
   compare assets.
3. **Review a client:** Demo Advisor → open Alice's portfolio → inspect holdings,
   history, and peer comparison.
4. **Explore with AI:** Alice → AI Demo → ask a question → inspect the answer,
   retrieved sources, or executed tools.

## Reset or test

Reset returns to the starting cash/date and **clears demo holdings, trades, and
recorded values**. Downloaded prices remain.

```bash
uv run python -m scripts.reset_demo_data
```

Run the offline tests:

```bash
uv run python -m pytest -q
```

## Read more

- [Case study](CASE_STUDY.md) — business context and security assessment brief.
- [Project guide](PROJECT_GUIDE.md) — architecture, workflows, API, and review boundaries.
- [Test guide](tests/README.md) — business examples and verification details.
