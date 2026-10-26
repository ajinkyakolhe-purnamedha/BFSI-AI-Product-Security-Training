"""Read the portfolio as investor or advisor; only investors change it."""

import os
from dataclasses import asdict
from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from chronos.api_schemas_requests_and_responses import (
    MarketPriceHistoryPointResponse,
    PortfolioScreenResponse,
    PortfolioChatRequest,
    PortfolioChatResponse,
    InvestorAIQuestionRequest,
    HandbookRagResponse,
    PortfolioAgentResponse,
    TradePreviewResponse,
    TradeRequest,
    TradeResponse,
)
from chronos.storage_sqlite_tables_and_sessions import get_database_session
from chronos.app_business_errors_and_permissions import RecordNotFoundError
from chronos.api_error_translation import translate_domain_errors
from chronos.business_investor_accounts import (
    get_account_for_investor_user,
    get_account_for_viewer,
)
from chronos.business_investor_trading import (
    execute_investor_trade,
    preview_investor_trade,
)
from chronos.market_historical_prices import (
    get_supported_assets,
    get_symbol_price_histories,
)
from chronos.business_portfolio_valuation import build_portfolio_screen

if TYPE_CHECKING:
    from llama_index.core.llms import LLM
    from llama_index.core import VectorStoreIndex
    from llama_index.core.llms.function_calling import FunctionCallingLLM

router = APIRouter()


def get_chat_model() -> "LLM":
    # Lazy imports keep ordinary dashboards working without the optional AI extra.
    from llama_index.llms.ollama import Ollama

    return Ollama(
        model=os.environ.get("CHRONOS_CHAT_MODEL", "qwen35-2b-chronos:latest"),
        base_url=os.environ.get("CHRONOS_OLLAMA_URL", "http://localhost:11434"),
        temperature=0.0, context_window=4096, request_timeout=120.0,
        thinking=False,
        additional_kwargs={"num_predict": 512},
    )


def get_rag_model() -> "LLM":
    from llama_index.llms.ollama import Ollama

    return Ollama(
        model=os.environ.get("CHRONOS_RAG_MODEL", "qwen35-2b-chronos:latest"),
        base_url=os.environ.get("CHRONOS_OLLAMA_URL", "http://localhost:11434"),
        temperature=0.0, context_window=4096, request_timeout=120.0,
        thinking=False, additional_kwargs={"num_predict": 512},
    )


@lru_cache(maxsize=1)
def get_handbook_index() -> "VectorStoreIndex":
    # Build on the first RAG question, then reuse this process's static handbook.
    # Restart the API after changing the corpus or embedding configuration.
    from llama_index.embeddings.ollama import OllamaEmbedding
    from chronos.ai.rag import build_handbook_index

    embedding = OllamaEmbedding(
        model_name=os.environ.get("CHRONOS_EMBEDDING_MODEL", "nomic-embed-text:latest"),
        base_url=os.environ.get("CHRONOS_OLLAMA_URL", "http://localhost:11434"),
        client_kwargs={"timeout": 120.0},
    )
    return build_handbook_index(embedding)


def get_agent_model() -> "FunctionCallingLLM":
    from llama_index.llms.ollama import Ollama

    return Ollama(
        model=os.environ.get("CHRONOS_AGENT_MODEL", "qwen35-2b-chronos:latest"),
        base_url=os.environ.get("CHRONOS_OLLAMA_URL", "http://localhost:11434"),
        temperature=0.0, context_window=4096, request_timeout=120.0,
        thinking=False, additional_kwargs={"num_predict": 512},
    )


@router.post("/portfolio/rag", response_model=HandbookRagResponse)
def ask_handbook(
    request: InvestorAIQuestionRequest, db: Session = Depends(get_database_session)
) -> HandbookRagResponse:
    with translate_domain_errors():
        get_account_for_investor_user(db, request.user_id)
        try:
            from httpx import HTTPError
            from ollama import ResponseError
            from chronos.ai.rag import answer_handbook_question

            answer, sources = answer_handbook_question(
                get_rag_model(), get_handbook_index(), request.question
            )
        except ImportError as error:
            raise HTTPException(status_code=503, detail="Install the AI extra with: uv sync --extra ai") from error
        except (HTTPError, ResponseError, ConnectionError, RuntimeError) as error:
            raise HTTPException(
                status_code=503,
                detail="RAG could not get an Ollama reply. Check Ollama, CHRONOS_RAG_MODEL and CHRONOS_EMBEDDING_MODEL.",
            ) from error
        return HandbookRagResponse(answer=answer, sources=[
            {"title": source.node.metadata["title"], "passage": source.node.text, "score": source.score}
            for source in sources
        ])


@router.post("/portfolio/agent", response_model=PortfolioAgentResponse)
def explore_portfolio(
    request: InvestorAIQuestionRequest, db: Session = Depends(get_database_session)
) -> PortfolioAgentResponse:
    with translate_domain_errors():
        get_account_for_investor_user(db, request.user_id)
        try:
            from httpx import HTTPError
            from ollama import ResponseError
            from chronos.ai.agent import ToolRead, run_portfolio_agent

            tool_reads: list[ToolRead] = []
            answer = run_portfolio_agent(
                db, get_agent_model(), request.user_id, request.question, tool_reads
            )
        except ImportError as error:
            raise HTTPException(status_code=503, detail="Install the AI extra with: uv sync --extra ai") from error
        except (HTTPError, ResponseError, ConnectionError, RuntimeError, ValueError) as error:
            raise HTTPException(
                status_code=503,
                detail=("Agent stopped without a completed answer. Check Ollama and CHRONOS_AGENT_MODEL; "
                        "the model must choose only the allowed read tools and finish within four tool calls."),
            ) from error
        return PortfolioAgentResponse(answer=answer, tool_calls=[asdict(read) for read in tool_reads])


@router.post("/portfolio/chat", response_model=PortfolioChatResponse)
def chat_about_portfolio(
    request: PortfolioChatRequest, db: Session = Depends(get_database_session)
) -> PortfolioChatResponse:
    with translate_domain_errors():
        get_account_for_investor_user(db, request.user_id)
        try:
            from llama_index.core.llms import ChatMessage
            from chronos.ai.chatbot import answer_portfolio_question
            from httpx import HTTPError
            from ollama import ResponseError
        except ImportError as error:
            raise HTTPException(
                status_code=503, detail="Install the AI extra with: uv sync --extra ai"
            ) from error

        history = [ChatMessage(role=message.role, content=message.content) for message in request.history]
        try:
            answer = answer_portfolio_question(
                db, get_chat_model(), request.user_id, request.question, history
            )
        except (HTTPError, ResponseError, ConnectionError, RuntimeError) as error:
            raise HTTPException(
                status_code=503,
                detail=("Chat could not get an Ollama reply. Check that Ollama is running "
                        "and CHRONOS_CHAT_MODEL names an installed model, then try again."),
            ) from error
        return PortfolioChatResponse(
            answer=answer,
            history=[{"role": message.role.value, "content": message.content} for message in history],
        )


@router.get("/portfolio", response_model=PortfolioScreenResponse)
def read_portfolio(
    user_id: int,
    investor_id: int | None = None,
    db: Session = Depends(get_database_session),
):
    with translate_domain_errors():
        account = get_account_for_viewer(db, user_id, investor_id)
        return build_portfolio_screen(db, account)


@router.get(
    "/market/history", response_model=dict[str, list[MarketPriceHistoryPointResponse]]
)
def read_market_comparison(
    user_id: int,
    symbols: list[str] = Query(min_length=1, max_length=5),
    investor_id: int | None = None,
    trading_days: int = Query(default=60, ge=1, le=1000),
    db: Session = Depends(get_database_session),
):
    with translate_domain_errors():
        account = get_account_for_viewer(db, user_id, investor_id)
        supported_symbols = {asset.symbol for asset in get_supported_assets(db)}
        symbols = [symbol.upper() for symbol in symbols]
        for symbol in symbols:
            if symbol not in supported_symbols:
                raise RecordNotFoundError(f"Unknown symbol {symbol!r}")
        return get_symbol_price_histories(
            db, symbols, account.simulated_date, trading_days
        )


@router.post("/trades/preview", response_model=TradePreviewResponse)
def preview_trade(request: TradeRequest, db: Session = Depends(get_database_session)):
    with translate_domain_errors():
        account = get_account_for_investor_user(db, request.user_id)
        return preview_investor_trade(db, account, request)


@router.post("/trades", response_model=TradeResponse)
def execute_trade(request: TradeRequest, db: Session = Depends(get_database_session)):
    with translate_domain_errors():
        account = get_account_for_investor_user(db, request.user_id)
        return execute_investor_trade(db, account, request)
