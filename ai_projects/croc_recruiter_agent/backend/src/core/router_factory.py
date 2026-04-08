from __future__ import annotations

from src.router import Router
from src.core.classifier import QueryClassifier
from src.core.engines.sql_engine import SqlEngine
from src.core.engines.rag_engine import RagEngine
from src.core.engines.candidates_engine import CandidatesEngine
from src.core.llm_route_planner import LLMRoutePlanner
from src.cache.cache_repository import CacheRepository
from src.core.pipelines.llm_pipeline import LLMPipeline
from src.llm.client import OpenAILLMClient
from src.config import get_settings
from src.office.postgres_client import PostgresClient
from src.office.office_engine import OfficeEngine
from src.rag.answer_generator import AnswerGenerator
from src.rag.retriever import Retriever


def build_router() -> Router:
    """
    Assembles the full Router with all real dependencies.

    A single OpenAILLMClient instance is shared between:
    - QueryClassifier (LLM fallback for ambiguous queries)
    - AnswerGenerator (RAG answer generation)

    RAG pipeline is created with enable_cache=False because
    cache is managed centrally by the Router itself.
    """
    cache_repository = CacheRepository()

    settings = get_settings()

    llm_client = None
    try:
        llm_client = OpenAILLMClient(model="gpt-4o-mini")
    except Exception:
        llm_client = None

    if llm_client is None:
        class _DisabledLLMClient:
            def generate_chat(self, messages, temperature: float = 0.0, max_tokens: int = 700) -> str:  # type: ignore
                return ""

        llm_client = _DisabledLLMClient()

    classifier = QueryClassifier(llm_client=llm_client)

    sql_engine = SqlEngine(llm_client=llm_client)

    retriever = Retriever()
    answer_generator = AnswerGenerator(
        llm_client=llm_client,
        max_context_chunks=5,
        max_context_chars_per_chunk=1800,
    )
    rag_pipeline = LLMPipeline(
        retriever=retriever,
        answer_generator=answer_generator,
        cache_repository=None,
        enable_cache=False,
    )
    rag_engine = RagEngine(pipeline=rag_pipeline)
    candidates_engine = CandidatesEngine()
    dsn = (settings.OFFICE_DB_DSN or "").strip() or (settings.DATABASE_URL or "").strip()
    office_engine = OfficeEngine(client=PostgresClient(dsn=dsn))
    route_planner = LLMRoutePlanner(llm_client=llm_client)
    return Router(
        classifier=classifier,
        sql_engine=sql_engine,
        rag_engine=rag_engine,
        route_planner=route_planner,
        candidates_engine=candidates_engine,
        office_engine=office_engine,
        cache_repository=cache_repository,
        enable_cache=True,
    )
