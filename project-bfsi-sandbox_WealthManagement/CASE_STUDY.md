# Chronos Wealth — Product Security Case Study

**Assess the product that exists. Support each finding with source or runtime evidence.**
Use the [README](README.md) to run it and the [project guide](PROJECT_GUIDE.md)
to trace its implementation.

## The product

Chronos Wealth helps investors inspect investments and simulate trading. An
advisor reviews the same financial information through a separate workspace.
The sandbox uses virtual cash, historical market prices, and an account-specific
simulated date. It places no real trades.

Alice starts with $100,000 on June 1, 2020. She can buy or sell fractional shares
of AAPL, MSFT, SPY, GLD, and JPM, advance time, and inspect her results. The Demo
Advisor opens Alice's portfolio and reviews holdings, history, and performance
without trading or changing time.

Three AI features extend Alice's workspace:

| Feature | Business purpose | Information used |
| --- | --- | --- |
| Chatbot | Explain the investor's current portfolio in plain language. | Python-calculated portfolio facts, a question, and bounded conversation history. |
| Handbook RAG | Explain investing concepts with supporting passages. | A shared, built-in handbook and the user's question. |
| Portfolio agent | Explore current value and recorded value changes. | Two read-only tools for portfolio facts and saved observations. |

These features are implemented. AI runtime setup will be provided separately
offline. An MCP server is planned for later; it is outside the current assessment.

## Your role

You are the Product Security engineer reviewing this application. Your work has
two parts: assess the conventional product and assess its AI integrations.
AI can help you discover, analyze, and generate test ideas. You remain responsible
for deciding whether an observation proves a security issue.

The current demo is deliberately small: two seeded identities, one investor
account, local SQLite storage, and a static handbook. Do not assume production
identity services, assigned-client management, document upload, client messaging,
or approval workflows exist. Treat a missing capability as a scope fact before
deciding whether it creates a security finding.

## Business expectations to assess

| Expectation | Why it matters |
| --- | --- |
| A caller acts only with the authority they are entitled to. | A submitted identity or a hidden UI control must not substitute for server-side authority. |
| Investors cannot read or change another investor's account. | Financial information and actions need ownership checks. |
| Advisors review portfolios without executing investor actions. | Read access must not imply trading or time-change authority. |
| A trade preserves valid cash, shares, and history. | Preview must be non-writing; execution must recheck facts and avoid partial updates. |
| AI stays within its data and tool authority. | Untrusted questions, history, passages, or model output must not grant new access or actions. |

All financial reads must use prices on or before the simulated date. A model's
explanation must not be mistaken for a new financial calculation or an executed
trade. Source citations and tool traces are evidence to inspect, not automatic
proof that an answer is correct.

## Assessment work

1. **Map one request.** Follow a portfolio read or trade from the UI through HTTP,
   account lookup, rules, and database access. Record assets and trust boundaries.
2. **Form and test an abuse hypothesis.** Examine identity, account targeting,
   role changes, invalid amounts, repeated requests, or business state. Specify
   expected behavior before testing.
3. **Trace an AI request.** Inspect portfolio context and chat history, retrieved
   handbook text, or proposed tool calls. Separate prompt instructions from
   controls enforced by Python.
4. **Reproduce or reject a finding.** Compare source analysis with responses and
   stored state. Record failed hypotheses as well as confirmed issues.
5. **Propose and verify a fix.** Define the invariant, make the smallest justified
   change, run regression checks, and report remaining uncertainty.

Use AI on the same task after establishing your own baseline. Compare coverage,
false positives, and evidence quality. No particular number of vulnerabilities
is guaranteed by the sandbox.

## Evidence to deliver

For each finding, record:

- **Location and path:** source file/function, endpoint, and required starting state.
- **Reproduction:** minimal request or input, expected result, and observed result.
- **Impact:** affected data or action, attacker prerequisites, severity rationale,
  and confidence; include CWE where appropriate.
- **Remediation:** proposed control, regression evidence, and residual risk.

End with a release recommendation: what was assessed, what was confirmed, what
was rejected, what remains untested, and what conditions must be met. Distinguish
substituted-model tests from live-model observations.

## Scope

Use the authorized local sandbox and synthetic identities. Preserve a repeatable
starting state; reset only when the scenario calls for it. Additional test
identities must be created explicitly—the shipped UI seeds only Alice and Demo
Advisor. Scanner outputs, external infrastructure, and future MCP behavior need
separate evidence if introduced into an assessment.
