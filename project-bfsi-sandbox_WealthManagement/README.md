# Chronos Wealth

**Start with [Run the app](#run-the-app).** Then try the [business workflows](#business-workflows).

A standalone wealth-management sandbox for product security training. It includes
investor and advisor screens, an API, and chatbot, RAG, and agent features.
All money and trades are virtual.

## Run the app

You need **Python 3.13** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)**.
Open a terminal in `project-bfsi-sandbox_WealthManagement`.

### 1. Install dependencies — first time only

```bash
uv sync
```

### 2. Download market data — first time only

Requires internet. After this, the core app uses local prices.

```bash
uv run python -m scripts.load_market_data
```

### 3. Start the backend — Terminal 1

```bash
uv run uvicorn chronos.app_startup:app --reload
```

Leave this running. [Check backend health](http://127.0.0.1:8000/health):
it should show `{"status":"ok"}`.

### 4. Start the UI — Terminal 2

Open a second terminal in the **same project folder**:

```bash
uv run streamlit run ui/app_navigation.py
```

Leave both terminals running. Stop each with `Ctrl+C`.

### 5. Open the app and select a user

Open **[http://localhost:8501](http://localhost:8501)**. No password is required.

| User | Email | What they can do |
| --- | --- | --- |
| Alice Investor | alice@example.com | Trade, advance time, review her portfolio, use AI |
| Demo Advisor | advisor@example.com | Review Alice's portfolio and performance |

Alice starts with **$100,000 cash on June 1, 2020**.

**App will not open?** Check that Terminal 2 is still running.
**404 at port 8000?** Open **8501** for the app.
The backend's [API documentation is at port 8000/docs](http://127.0.0.1:8000/docs).

## What the app does

### Investing and portfolio review

| Feature | What you can do |
| --- | --- |
| Portfolio dashboard | See cash, holdings, total value, and return. Inspect shares, average cost, current prices, allocation, and unrealized gains/losses. |
| Buy and sell | Enter a dollar amount, preview price/shares/eligibility, and confirm. Fractional shares are supported. Invalid amounts, insufficient cash, and insufficient shares are rejected. |
| Time and history | Advance one week, month, or quarter within available market dates. See trade history and portfolio values saved after trades and time advances. |
| Market comparison | Compare AAPL, MSFT, SPY, GLD, and JPM, including best/worst performers. Advisors can compare a symbol with its peers' average. |
| Advisor workspace | Review Alice's holdings, trades, saved values, and charts. Advisors cannot trade or advance time. |

**The rules:** Python calculates financial results. Prices never come from after
the simulated date. Preview changes no financial records; confirmation rechecks
the trade. Failed operations roll back their database changes.

Activity persists in `data/chronos.db`. Prices are prepared in
`data/market/prices.csv`. History saves observations, not a value for every day.
The API exposes portfolio reads, trading, time advancement, login, AI, and reset.

### AI features — setup will be provided offline

| Feature | What you can inspect |
| --- | --- |
| Chatbot | Answers using refreshed portfolio facts and up to three completed conversation turns. Clear chat to start again. |
| Handbook RAG | Searches six built-in handbook documents. Shows retrieved passages, similarity scores, and an answer prompted to cite its sources. Returns a no-evidence response when no passage meets the threshold. |
| Portfolio agent | Reads current portfolio facts or the last five saved values. Shows executed tools and results. Python fixes the investor identity, checks tool names/arguments, and limits execution to four tool calls. No write tools are exposed. |

**Planned:** an MCP server will be added later.

## Business workflows

1. **Make an investment:** log in as Alice → choose BUY, a symbol, and an amount →
   preview → confirm → inspect cash, holdings, and the recorded trade.
2. **Sell an investment:** choose SELL and an amount → preview available shares →
   confirm → inspect the updated position and cash.
3. **Review performance:** advance time → inspect the value change and recorded
   history → compare assets. Log in as Demo Advisor to review Alice's results.
4. **Explore with AI:** open Alice's AI Demo tabs → ask about her portfolio,
   search the handbook, or run the agent → inspect sources or tool results.
5. **Repeat the demo:** reset to $100,000, June 1, 2020, no holdings or trades,
   and one initial value observation. Downloaded prices remain.

Reset **clears existing demo investment activity**:

```bash
uv run python -m scripts.reset_demo_data
```

## AI setup

AI setup will be provided separately offline. Once configured, open Alice's
**AI Demo** section and try:

- **Chatbot:** “Why is portfolio value different from cash?”
- **RAG:** “What is unrealized gain?”
- **Agent:** “Explain my portfolio value history.”

## Security review context

- **Identity:** demo login selects a user. API requests supply user IDs; there
  is no authenticated session establishing the caller's identity.
- **Access:** role checks restrict investor/advisor actions. Advisors can read
  investor accounts without an assigned-client relationship check.
- **AI data:** RAG searches a shared static handbook. Chat history comes from
  the request. Inspect prompts, retrieved content, and tool execution separately.

## Run the tests

```bash
uv run --extra ai python -m pytest -q
```

Tests use temporary databases, fixture prices, and substituted model/network
responses. They cover financial rules, access, validation, rollback, UI behavior,
and AI boundaries. Live-model behavior needs separate assessment.
For core-only tests, omit `--extra ai`; optional AI checks may skip.

## Read more

- [Project guide](PROJECT_GUIDE.md) — architecture and business logic.
- [AI guide](chronos/ai/README.md) — prompts, retrieval, tools, and terminal commands.
- [Test guide](tests/README.md) — business examples and focused checks.
- [API routes](chronos/api_routes_portfolio.py) — portfolio, trades, and AI entry points.
- [Account access](chronos/business_investor_accounts.py) — viewer and investor checks.
