# Three independent AI lessons

Read each Python file from top to bottom. Each owns its settings, prompts, model
instance, and terminal entry point. They do not import each other.

| File | What to learn | Example question |
| --- | --- | --- |
| [chatbot.py](chatbot.py) | Supply current portfolio facts and keep three completed chat turns. | Why is portfolio value different from cash? |
| [rag.py](rag.py) | Split six handbook documents, embed chunks, retrieve evidence, build a prompt, and show sources. | What is unrealized gain? |
| [agent.py](agent.py) | Let a model choose tools, validate requests, execute reads, and feed results back in a bounded loop. | Explain my portfolio journey using current facts and recorded values. |

All three have terminal entry points. The investor dashboard also calls them
through the **AI Demo** section's **Chatbot**, **RAG**, and **Agent** tabs.
Existing M1–M15 starters remain exercises.

## Demo the AI tabs

Start Ollama, then run these in separate terminals from the project root:

```bash
uv run --extra ai python -m uvicorn chronos.app_startup:app --reload
uv run --extra ai python -m streamlit run ui/app_navigation.py
```

Open http://localhost:8501, log in as Alice, and find **AI Demo** below the
portfolio summary. In **Chatbot**, try “Why is portfolio value different from cash?” and then
“Explain that more simply.” **Clear chat** starts a new conversation. The panel
keeps the last three completed turns in the UI session; logout clears them.
Each question reloads current facts, so you can trade or advance time and ask again.

In **RAG**, ask “What is unrealized gain?” and click **Ask handbook**. Expand the
numbered sources to inspect retrieved passages and similarity scores. It uses the
six inline handbook documents, not your portfolio. No evidence means no generated
answer. The index is built on first use and cached in the API process; restart
after changing the handbook or embedding configuration.

In **Agent**, ask “Read my current portfolio and recorded value history; explain
what changed” and click **Run agent**. Expand each tool call to inspect its name,
arguments, and actual result. The model chooses the tools; only completed reads
appear in the trace. It can use at most four read tools and cannot trade or advance
time. RAG and Agent keep their latest successful question/result until logout;
ordinary rerenders do not rerun models.

The UI demo defaults to this machine's installed `qwen35-2b-chronos:latest` model
for generation and `nomic-embed-text:latest` for embeddings. The independent
settings are `CHRONOS_CHAT_MODEL`, `CHRONOS_RAG_MODEL`, `CHRONOS_AGENT_MODEL`, and
`CHRONOS_EMBEDDING_MODEL`. For example:

```bash
CHRONOS_CHAT_MODEL=qwen3:4b uv run --extra ai python -m uvicorn chronos.app_startup:app --reload
```

`CHRONOS_OLLAMA_URL` overrides `http://localhost:11434`. Missing optional packages,
models, or a stopped Ollama server produce a visible error; failed turns do not
replace completed history. Normal dashboard rendering makes no model request.
All tabs and their endpoints are investor-only. The API paths are
`POST /portfolio/chat`, `POST /portfolio/rag`, and `POST /portfolio/agent`.
They only read facts or the static handbook. Tool traces show executed calls,
not hidden model reasoning. Every file remains independent and runnable alone.

## Setup and run

Install the optional dependencies from the project root:

```bash
uv sync --extra ai
```

Start your local Ollama server. The default models are `qwen3:4b` for chat/tool
calling and `embeddinggemma` for embeddings. Install them if needed:

```bash
ollama pull qwen3:4b
ollama pull embeddinggemma
```

Then run each lesson separately:

```bash
uv run --extra ai python -m chronos.ai.chatbot
uv run --extra ai python -m chronos.ai.rag "What is unrealized gain?"
uv run --extra ai python -m chronos.ai.agent "Explain my portfolio journey"
```

Chat and the agent read the existing Chronos database, which must already have
demo users, an investor account, and prepared prices. They do not create tables,
seed data, download prices, or reset accounts. RAG uses only its inline handbook.

The email defaults to `alice@example.com`; `--email` selects another demo investor.
This is the same password-free demo identity convention as the core app, not
production authentication. Python fixes the agent's account before the model
can request a tool, so tools accept no investor ID or other arguments.

You can use models already installed on this machine instead of downloading:

```bash
uv run --extra ai python -m chronos.ai.chatbot --model qwen35-2b-chronos:latest
uv run --extra ai python -m chronos.ai.rag "What is unrealized gain?" --model qwen35-2b-chronos:latest --embedding-model nomic-embed-text:latest
uv run --extra ai python -m chronos.ai.agent "Explain my portfolio journey" --model qwen35-2b-chronos:latest
```

Use `ollama list` to check your installation. Change `--model`, `--embedding-model`,
or the clearly named constants inside a lesson. The agent requires a model that
supports tool calling. Missing models and connection errors propagate; there is
no generated-looking fallback answer.

## Read the important steps

The chatbot reloads dated portfolio facts for every question. Its message list
contains a system prompt, recent user/assistant turns, and the new question.
Only successful responses become history. Python supplies financial values.

RAG prints chunk/vector counts, similarity scores, and retrieved passages before
the answer. The index is in memory and rebuilt each run. `MIN_SIMILARITY` is an
illustrative cutoff, not proof of relevance; test and tune it when changing the
embedding model or corpus. If no passage passes the cutoff, generation is skipped.
Citation labels identify retrieved passages; the model still needs evaluation
for whether its answer is actually supported by them.

A live smoke run with the installed `qwen35-2b-chronos:latest` model exercised
chat, retrieved handbook evidence, and both agent tools on an isolated fixture
database without changing its financial records. The small model also mislabeled
financial values in a chat explanation. Inspect its answer against the printed
facts; a successful model call does not establish factual accuracy.

The agent exposes only `read_my_portfolio` and `read_my_value_history`. The latter
returns five observations and a Python-calculated change between the first and
last returned value. It does not reconstruct daily performance. Every proposed
tool name and argument set is checked before execution. Four tool calls are the
maximum, with one further model turn allowed to produce a final answer. All tools
read facts; neither the agent nor the chatbot commits financial records.

## Offline verification

```bash
uv run --extra ai python -m pytest -q
```

[test_ai.py](../../tests/engineering/test_ai.py) replaces Ollama's network response
and supplies controlled embedding vectors. It exercises real LlamaIndex message
conversion, retrieval, and tool parsing with fixture-backed portfolio reads.
It checks bounded history, missing evidence, investor scope, tool rejection,
loop limits, and non-mutation. It does not measure live answer quality.
Without the `ai` extra, these optional checks are skipped and core tests still run.

Reference APIs: [Ollama LLM](https://developers.llamaindex.ai/python/framework/integrations/llm/ollama/),
[Ollama embeddings](https://developers.llamaindex.ai/python/framework/integrations/embeddings/ollama_embedding/),
and [function-calling loop](https://developers.llamaindex.ai/python/examples/workflow/function_calling_agent/).
