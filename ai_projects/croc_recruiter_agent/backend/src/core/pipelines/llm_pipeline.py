from __future__ import annotations

from typing import Any, Dict, List
import hashlib

from src.utils.logger import get_logger
from src.core.formatters.rag_response_formatter import format_rag_response

logger = get_logger(__name__)


class LLMPipeline:
    """
    End-to-end RAG pipeline:
    Query -> Semantic Cache -> Retriever -> Answer Generator -> Format -> Cache Save -> Response
    """

    def __init__(
        self,
        retriever: Any,
        answer_generator: Any,
        cache_repository: Any | None = None,
        enable_cache: bool = True,
        cache_empty_answers: bool = False,
    ) -> None:
        self.retriever = retriever
        self.answer_generator = answer_generator
        self.cache_repository = cache_repository
        self.enable_cache = enable_cache
        self.cache_empty_answers = cache_empty_answers

    def run(self, query: str) -> Dict[str, Any]:
        query = (query or "").strip()

        if not query:
            return {
                "answer": "Query cannot be empty.",
                "sources": [],
                "cache_hit": False,
            }

        # build scope (RLS-ready future)
        scope_hash = self._build_scope_hash()

        # cache get
        cached_response = self._try_cache_get(query, scope_hash)

        if cached_response:
            logger.info("llm_pipeline.cache_hit", extra={"query": query})

            formatted = format_rag_response(
                cached_response.get("response", ""),
                cached_response.get("sources", []),
            )

            return {
                "answer": formatted,
                "sources": cached_response.get("sources", []),
                "cache_hit": True,
            }

        logger.info("llm_pipeline.cache_miss", extra={"query": query})

        # retrieval
        retrieved_chunks = self._retrieve(query)

        # generation
        generation_result = self.answer_generator.generate(
            query=query,
            retrieved_chunks=retrieved_chunks,
        )

        raw_answer = generation_result.get("answer", "").strip()
        sources = generation_result.get("sources", [])

        # format
        formatted_answer = format_rag_response(raw_answer, sources)

        # cache save
        self._try_cache_save(
            query=query,
            answer=raw_answer,
            sources=sources,
            scope_hash=scope_hash,
        )

        return {
            "answer": formatted_answer,
            "sources": sources,
            "cache_hit": False,
        }

    # retriever
    def _retrieve(self, query: str) -> List[Dict[str, Any]]:
        chunks = self.retriever.retrieve(query)

        if not isinstance(chunks, list):
            logger.warning(
                "llm_pipeline.invalid_retriever_output",
                extra={"type": str(type(chunks))},
            )
            return []

        logger.info(
            "llm_pipeline.retrieval_completed",
            extra={"query": query, "chunks_count": len(chunks)},
        )

        return chunks
    
    # cache
    def _build_scope_hash(self) -> str:
        """
        Future-ready for:
        - user_id
        - role
        - permissions
        """
        return hashlib.md5("global_scope".encode()).hexdigest()

    def _try_cache_get(self, query: str, scope_hash: str) -> Dict[str, Any] | None:
        if not self.enable_cache or self.cache_repository is None:
            return None

        try:
            return self.cache_repository.get_cache(
                query=query,
                scope_hash=scope_hash,
            )
        except Exception as exc:
            logger.exception(
                "llm_pipeline.cache_get_failed",
                extra={"query": query, "error": str(exc)},
            )
            return None

    def _try_cache_save(
        self,
        query: str,
        answer: str,
        sources: List[str],
        scope_hash: str,
    ) -> None:
        if not self.enable_cache or self.cache_repository is None:
            return

        normalized_answer = (answer or "").strip()

        if not normalized_answer:
            return

        # avoid cache of useless answers
        if not self.cache_empty_answers and normalized_answer in {
            "No relevant documents found.",
            "The information was not found in the provided documents.",
        }:
            logger.info("llm_pipeline.cache_skip_empty_answer")
            return

        try:
            self.cache_repository.save_cache(
                query=query,
                response=normalized_answer,
                sources=sources,
                scope_hash=scope_hash,
            )

            logger.info(
                "llm_pipeline.cache_saved",
                extra={"query": query, "sources_count": len(sources)},
            )

        except Exception as exc:
            logger.exception(
                "llm_pipeline.cache_save_failed",
                extra={"query": query, "error": str(exc)},
            )