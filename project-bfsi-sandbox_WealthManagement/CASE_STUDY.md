# Chronos Wealth: AI Application Design Case Study

## The company and its product

Chronos Wealth is a digital wealth-management company. It helps individual investors understand and manage their investments, while giving financial advisors a secure view of the clients they serve. In a production version of the business, investors would hold real investment accounts. For this learning platform, all money and trades are virtual, but the workflows reflect a real wealth-management business.

The product has two connected workspaces.

- **Investor workspace:** An investor can see available cash, investments held, portfolio value, investment return, past trades, and market-performance charts. They can compare a small list of approved securities, preview a buy or sell, and execute a virtual trade.
- **Advisor workspace:** A financial advisor can see a list of assigned clients and review each client's portfolio. The advisor can identify issues such as too much money in one security, too much uninvested cash, too little diversification, or poor performance. The advisor's workspace is read-only: advisors cannot place a trade for a client.

Chronos Wealth already has reliable application services that calculate portfolio values, returns, holdings, trade eligibility, and risk flags. These calculations use market prices that were available only on the relevant date. For example, the system must never use a future price to explain a past decision or portfolio result. This is called a **point-in-time data rule**.

The company now wants to use AI to improve service and productivity. It wants AI to help people find information, explain facts, summarize, draft, and route work. It does **not** want AI to make up financial facts, override investment policy, view data it is not allowed to see, send unapproved communications, or execute trades on its own.

## People and departments involved

- **Investors / clients:** want clear answers about their accounts and investments.
- **Financial advisors / relationship managers:** prepare for client meetings, explain portfolios, and draft follow-up communications.
- **Investment research and portfolio-management teams:** maintain approved research, investment views, and portfolio guidelines.
- **Risk management:** monitors concentration, diversification, cash allocation, and other portfolio-risk indicators.
- **Compliance and legal:** ensures client communications and recommendations follow policy and regulatory requirements.
- **Operations / trade support:** manages workflow completeness, exceptions, and record accuracy.
- **Internal audit:** investigates incidents and tests whether processes and controls were followed.
- **Technology and AI governance:** controls AI models, access, data handling, monitoring, testing, and incident response.

## Your assignment

Design five AI features for Chronos Wealth. You are not required to write code. Instead, explain how each feature should work in business and technology terms.

For each question, address:

1. **User and benefit:** Who uses it, and what business problem does it solve?
2. **AI approach:** Is it best designed as a simple chatbot, a document-search assistant (RAG), a rules-based workflow with AI drafting, or an AI agent that can use tightly controlled tools? Why?
3. **Information used:** What account data, market data, documents, or systems does it need? Who may access that information?
4. **Controls:** What must be calculated or decided by the existing deterministic system rather than AI? What requires a human approval?
5. **Risk and measurement:** What can go wrong, how will it be controlled, and how will Chronos Wealth know whether the feature is successful?

**Helpful definitions:** A *chatbot* answers questions in conversation. *RAG* (retrieval-augmented generation) finds relevant approved documents before answering, so the answer can cite its sources. An *agent* is an AI application that can plan a multi-step task and call approved software tools. A *deterministic service* produces the same calculation or decision from the same inputs, such as a portfolio-value calculation or a policy threshold check.

## Question 1 — Investor portfolio-explainer assistant

An investor signs in and asks: “Why did my portfolio fall this month? How much of the decline came from AAPL? What does my current cash balance mean for my investment plan?”

Design an investor-facing conversational assistant that explains the logged-in investor's portfolio in plain language. It may access that investor's portfolio, trade and account-value history, point-in-time market data, and approved educational content.

Recommend an AI design for this feature. Explain how the solution will use the investor's own account data only, show the source for factual claims, distinguish factual explanation from personal investment advice, avoid inventing prices or returns, and prevent the AI from placing a trade or making an unauthorized recommendation.

## Question 2 — Advisor meeting-preparation copilot

An advisor is preparing for a review with Alice. The advisor needs a concise briefing with portfolio value, cash ratio, largest holding, recent performance, trade activity, relevant risks, and suggested client discussion points. The advisor also wants a draft follow-up note after the meeting.

Design an advisor copilot that creates this briefing and draft. Explain which information must come from the platform's portfolio-calculation services, where a policy-document search assistant would be useful, and how the system should answer a question such as, “Can Alice add more AAPL under the guideline?” Describe the advisor's review and approval process before a note is sent, and how the system keeps one client's information separate from another's.

## Question 3 — Investment-policy RAG assistant

Advisors and portfolio managers need reliable answers to questions such as: “Does this portfolio breach the concentration guideline?” and “What is the approved response to a high-cash allocation?” They need answers grounded in approved investment policies, suitability rules, product guidance, and research summaries.

Design a policy-grounded document-search assistant (RAG). Describe how approved documents are stored, updated, found, and cited; how the platform's calculation services determine portfolio metrics and policy thresholds; and which tightly controlled tools the AI may use, such as current-price lookup, portfolio-allocation lookup, and guideline checking. Explain how you would test whether it finds the right policy, gives an answer supported by that policy, handles out-of-date documents, and refuses to answer when the evidence is insufficient.

## Question 4 — Compliance communications-review workflow

Compliance must review advisor emails, meeting notes, and AI-generated client drafts before they are sent. It needs to identify potentially misleading statements, unsuitable recommendations, missing disclosures, unapproved product language, promises of returns, and direct trade instructions.

Design a compliance-review workflow that uses AI to identify risks, find relevant policy, and propose edits, but never independently approves a client communication or rewrites official policy. Explain the mix of rules, AI classification, document search, and AI reasoning. Show the process from draft to review, revision, approval or rejection, and an audit record. Also describe when a high-risk item must be escalated and how the firm will measure missed risks and unnecessary alerts.

## Question 5 — Internal-audit and AI-governance investigation assistant

Internal audit receives a complaint that an AI assistant exposed information about another client and encouraged an unauthorized trade. Auditors need to investigate the complete interaction without receiving broad, unrestricted access to all client data.

Design a read-only audit and AI-governance assistant that can investigate access logs, AI inputs and outputs, documents used to answer a question, software-tool calls, approvals, policy versions, and user actions. State what evidence must be recorded for every AI interaction; how the assistant accesses only the minimum information necessary; how its findings can be traced to the AI model, instructions, documents, and tool results used; and which actions it must never be permitted to perform. Include tests for malicious instructions, client-data leakage, excessive data requests, and attempts to trade, delete records, or use an unrestricted database query.

## Design principle

AI may explain, retrieve, summarize, draft, classify, and assist. Deterministic services calculate financial facts; policy gates enforce business rules; and a suitably authorized human remains accountable for consequential advice, communications, and actions.
