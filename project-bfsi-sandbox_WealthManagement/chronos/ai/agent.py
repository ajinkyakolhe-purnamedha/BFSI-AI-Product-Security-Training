"""Lesson 3: a model chooses read tools; Python runs a bounded tool loop.

Run: uv run --extra ai python -m chronos.ai.agent "Explain my portfolio journey"
This is independent of chatbot.py and rag.py. Read tool requests/results in the terminal.
"""

import argparse
import json
from dataclasses import dataclass

from llama_index.core.llms import ChatMessage
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.tools import FunctionTool
from llama_index.llms.ollama import Ollama
from sqlalchemy.orm import Session

from chronos.app_demo_data_and_reset import login_demo_user_by_email
from chronos.business_investor_accounts import get_account_for_investor_user
from chronos.business_portfolio_history import read_recorded_portfolio_values
from chronos.business_portfolio_valuation import build_current_portfolio_snapshot
from chronos.storage_sqlite_tables_and_sessions import SessionLocal

MODEL_NAME = "qwen3:4b"  # This model must support tool calling.
OLLAMA_URL = "http://localhost:11434"
MAX_TOOL_CALLS = 4
HISTORY_POINTS = 5
SYSTEM_PROMPT = """You are a read-only educational portfolio exploration agent.
Choose the tools needed to answer the user's question. Tools describe one investor only.
Use returned facts and Python-calculated changes; do not invent financial numbers.
Current prices stop at the simulated date. History contains saved observations, not daily prices.
Saved history may differ from current valuation after a price correction.
Explain what happened in plain language; do not recommend or execute trades.
"""


@dataclass(frozen=True)
class ToolRead:
    """One completed tool call, exposed so the UI can show what actually ran."""
    tool_name: str
    arguments: dict[str, object]
    result: str


def run_portfolio_agent(
    db: Session, llm: FunctionCallingLLM, investor_user_id: int, question: str,
    tool_reads: list[ToolRead] | None = None,
) -> str:
    if not question.strip():
        raise ValueError("Enter a question")
    account = get_account_for_investor_user(db, investor_user_id)

    # 1. Tool identity is fixed by Python, never supplied by the model.
    def read_my_portfolio() -> str:
        """Read my current dated cash, holdings, allocation and total portfolio value."""
        portfolio = build_current_portfolio_snapshot(db, account)
        return portfolio.model_dump_json()

    def read_my_value_history() -> str:
        """Read my last five saved portfolio values and their Python-calculated value change."""
        history = read_recorded_portfolio_values(db, account)[-HISTORY_POINTS:]
        recorded_value_change = history[-1].total_value - history[0].total_value if history else None
        return json.dumps({
            "observations": [point.model_dump(mode="json") for point in history],
            "change_between_first_and_last_returned_value": recorded_value_change,
        })

    # 2. LlamaIndex turns function names, types and docstrings into tool schemas.
    tools = [
        FunctionTool.from_defaults(fn=read_my_portfolio),
        FunctionTool.from_defaults(fn=read_my_value_history),
    ]
    tools_by_name = {tool.metadata.name: tool for tool in tools}
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=question),
    ]
    tool_calls_used = 0

    # 3. Each model response either answers or requests tools. Allow a final answer
    # after the fourth tool call, but never execute a fifth call.
    for step in range(MAX_TOOL_CALLS + 1):
        print(f"\nMODEL TURN {step + 1}")
        # Preserve all proposed calls for validation. Ollama's adapter otherwise
        # keeps only the first call; our Python loop still executes sequentially.
        response = llm.chat_with_tools(tools, chat_history=messages, allow_parallel_tool_calls=True)
        messages.append(response.message)
        calls = llm.get_tool_calls_from_response(response, error_on_no_tool_call=False)
        if not calls:
            answer = response.message.content
            if not answer or not answer.strip():
                raise RuntimeError("The model returned neither an answer nor a tool request")
            return answer
        if tool_calls_used + len(calls) > MAX_TOOL_CALLS:
            raise RuntimeError("Agent reached the tool call limit")

        # 4. Validate the entire batch before any tool in it is dispatched.
        for call in calls:
            if call.tool_name not in tools_by_name:
                raise ValueError(f"Tool is not allowed: {call.tool_name}")
            if call.tool_kwargs:
                raise ValueError("These tools take no arguments; investor identity is fixed")

        # 5. Python executes each allowed read and returns the result to the model.
        for call in calls:
            print("TOOL REQUEST:", call.tool_name, call.tool_kwargs)
            result = tools_by_name[call.tool_name].call()
            if result.is_error:
                raise RuntimeError(result.content)
            print("TOOL RESULT:", result.content)
            if tool_reads is not None:
                tool_reads.append(ToolRead(call.tool_name, dict(call.tool_kwargs), result.content))
            messages.append(ChatMessage(
                role="tool", content=result.content,
                additional_kwargs={"tool_call_id": call.tool_id, "name": call.tool_name},
            ))
            tool_calls_used += 1
        # Loop back: the next model request includes the tool results.
    raise RuntimeError("Agent reached the tool call limit")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default="Explain my portfolio journey using current facts and recorded values")
    parser.add_argument("--email", default="alice@example.com", help="Demo investor identity")
    parser.add_argument("--model", default=MODEL_NAME)
    args = parser.parse_args()
    llm = Ollama(
        model=args.model, base_url=OLLAMA_URL, temperature=0.0,
        context_window=4096, request_timeout=120.0, thinking=False,
    )
    with SessionLocal() as db:
        investor = login_demo_user_by_email(db, args.email)
        print("\nANSWER:", run_portfolio_agent(db, llm, investor.id, args.question))
    # No commit: the agent has only read tools.


if __name__ == "__main__":
    main()
