from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, Sequence

from src.utils.logger import get_logger
from src.rag.prompt_builder import build_rag_messages

logger = get_logger(__name__)


class LLMClientProtocol(Protocol):
    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 700,
    ) -> str:
        ...


@dataclass(slots=True)
class AnswerGenerationResult:
    answer: str
    sources: List[str]


class AnswerGenerator:
    """
    Generates grounded answers strictly from retrieved RAG chunks.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        max_context_chunks: int = 5,
        max_context_chars_per_chunk: int = 1800,
    ) -> None:
        self.llm_client = llm_client
        self.max_context_chunks = max_context_chunks
        self.max_context_chars_per_chunk = max_context_chars_per_chunk

    def generate(
        self,
        query: str,
        retrieved_chunks: Sequence[Dict[str, Any]] | None,
    ) -> Dict[str, Any]:

        normalized_chunks = self._normalize_chunks(retrieved_chunks)

        if not normalized_chunks:
            logger.info("answer_generator.no_chunks", extra={"query": query})
            return {
                "answer": "No relevant documents found.",
                "sources": [],
            }

        sources = self._extract_sources(normalized_chunks)

        messages = build_rag_messages(
            query=query,
            chunks=normalized_chunks,
            max_context_chars_per_chunk=self.max_context_chars_per_chunk,
        )

        logger.info(
            "answer_generator.generating",
            extra={
                "query": query,
                "chunks_count": len(normalized_chunks),
                "sources_count": len(sources),
            },
        )

        raw_answer = self.llm_client.generate_chat(
            messages=messages,
            temperature=0.0,
            max_tokens=700,
        )

        answer = self._post_process_answer(raw_answer, sources)

        result = AnswerGenerationResult(
            answer=answer,
            sources=sources,
        )

        return {
            "answer": result.answer,
            "sources": result.sources,
        }

    def _normalize_chunks(
        self,
        retrieved_chunks: Sequence[Dict[str, Any]] | None,
    ) -> List[Dict[str, Any]]:

        if not retrieved_chunks:
            return []

        normalized: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(retrieved_chunks[: self.max_context_chunks]):
            if not isinstance(chunk, dict):
                logger.warning(
                    "answer_generator.invalid_chunk_type",
                    extra={"index": idx, "type": str(type(chunk))},
                )
                continue

            text = (
                chunk.get("text")
                or chunk.get("content")
                or chunk.get("chunk_text")
                or ""
            )
            text = str(text).strip()

            metadata = chunk.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}

            source = (
                chunk.get("source")
                or metadata.get("source")
                or metadata.get("document_name")
                or metadata.get("file_name")
                or "unknown_source"
            )

            section = (
                metadata.get("section")
                or metadata.get("heading")
                or chunk.get("section")
                or "N/A"
            )

            score = chunk.get("score")
            similarity = chunk.get("similarity")

            if not text:
                logger.warning(
                    "answer_generator.empty_chunk_text",
                    extra={"index": idx, "source": source},
                )
                continue

            normalized.append(
                {
                    "text": text,
                    "source": str(source),
                    "section": str(section),
                    "score": score,
                    "similarity": similarity,
                    "metadata": metadata,
                }
            )

        return normalized

    def _extract_sources(self, chunks: Sequence[Dict[str, Any]]) -> List[str]:
        unique_sources: List[str] = []
        seen = set()

        for chunk in chunks:
            source = str(chunk.get("source", "")).strip()
            if source and source not in seen:
                seen.add(source)
                unique_sources.append(source)

        return unique_sources

    def _post_process_answer(self, raw_answer: str, sources: List[str]) -> str:
        import re

        answer = (raw_answer or "").strip()

        if not answer:
            return "I could not generate a grounded answer from the retrieved documents."

        # Strip any source references the LLM may have appended itself.
        # format_rag_response (the single source of truth) will add [Source: X].
        answer = re.sub(r"\[Source:.*?\]", "", answer, flags=re.IGNORECASE).strip()
        answer = re.sub(r"\(Source:.*?\)", "", answer, flags=re.IGNORECASE).strip()
        answer = re.sub(r"(?im)^sources?:.*$", "", answer).strip()
        answer = re.sub(r"\n\s*-\s+\S+\.md\b.*$", "", answer, flags=re.MULTILINE).strip()

        return answer