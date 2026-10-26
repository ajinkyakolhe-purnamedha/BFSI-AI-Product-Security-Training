"""Lesson 1: explain a real investor portfolio with a short chat history.

Run: uv run --extra ai python -m chronos.ai.chatbot
Read top to bottom: settings -> portfolio context -> chat -> terminal input.
"""

import argparse

from llama_index.core.llms import ChatMessage, LLM
from llama_index.llms.ollama import Ollama
from sqlalchemy.orm import Session

from chronos.app_demo_data_and_reset import login_demo_user_by_email
from chronos.business_investor_accounts import get_account_for_investor_user
from chronos.business_portfolio_valuation import build_current_portfolio_snapshot
from chronos.storage_sqlite_tables_and_sessions import SessionLocal

# This lesson owns its configuration and model instance.
MODEL_NAME = "qwen3:4b"
OLLAMA_URL = "http://localhost:11434"
MAX_HISTORY_MESSAGES = 6  # Three user/assistant pairs, not permanent memory.
SYSTEM_PROMPT = """You are an educational portfolio explainer for Chronos.
Explain the supplied Python-calculated facts in plain language.
Portfolio value means total_value. holdings_value is only the invested part.
total_return_amount is dollars. total_return_percentage is already a percent:
0.02 means 0.02%, not two cents. Do not reinterpret or recalculate these fields.
Use the latest supplied facts when earlier conversation disagrees with them.
Prices belong to the account's simulated date; do not use outside market knowledge.
Do not invent numbers, calculate new financial results, or recommend trades.
If a fact is missing, say so. This conversation cannot change the portfolio.
Keep the answer under 100 words.
"""


def answer_portfolio_question(
    db: Session, llm: LLM, investor_user_id: int,
    question: str, history: list[ChatMessage],
) -> str:
    if not question.strip():
        raise ValueError("Enter a question")

    # Refresh facts every turn. The existing core enforces role and dated pricing.
    account = get_account_for_investor_user(db, investor_user_id)
    portfolio = build_current_portfolio_snapshot(db, account)
    facts = portfolio.model_dump_json()
    print("\nPORTFOLIO CONTEXT:", facts)

    # A chat request is a list of role-labelled messages, not just a string.
    user_message = ChatMessage(role="user", content=question)
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT + "\nPortfolio facts:\n" + facts),
        *history[-MAX_HISTORY_MESSAGES:],
        user_message,
    ]
    response = llm.chat(messages)
    answer = response.message.content
    if not answer or not answer.strip():
        raise RuntimeError("The model returned an empty answer")

    # Save only completed turns; connection failures do not become chat history.
    history.extend([user_message, response.message])
    del history[:-MAX_HISTORY_MESSAGES]
    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default="alice@example.com", help="Demo investor identity")
    parser.add_argument("--model", default=MODEL_NAME)
    args = parser.parse_args()
    llm = Ollama(
        model=args.model, base_url=OLLAMA_URL, temperature=0.0,
        context_window=4096, request_timeout=120.0, thinking=False,
    )
    history: list[ChatMessage] = []
    print("Portfolio chat. Try: Why is portfolio value different from cash? Type /quit to exit.")
    with SessionLocal() as db:
        investor = login_demo_user_by_email(db, args.email)
        get_account_for_investor_user(db, investor.id)
        while True:
            try:
                question = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if question == "/quit":
                break
            if not question:
                continue
            print("Assistant:", answer_portfolio_question(db, llm, investor.id, question, history))
    # Session close rolls back; this lesson never commits financial records.


if __name__ == "__main__":
    main()
