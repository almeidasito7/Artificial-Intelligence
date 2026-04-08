from __future__ import annotations

from typing import Any, Dict

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RagEngine:
    """
    Wrapper for the RAG execution pipeline.

    Delegates to an LLMPipeline instance configured with cache disabled.
    Cache is managed by the Router — the engine only handles retrieval and generation.

    Output contract:
    {
        "answer": "...",
        "sources": ["doc1.md", ...]
    }

    Does NOT: manage cache, classify queries, or apply RLS.
    The Router is responsible for those concerns.
    """

    def __init__(self, pipeline: Any) -> None:
        self.pipeline = pipeline

    def run(self, question: str, permissions: Dict[str, Any]) -> Dict[str, Any]:
        result = self.pipeline.run(question)

        logger.info(
            "rag_engine.completed",
            extra={
                "sources_count": len(result.get("sources", [])),
            },
        )

        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
        }
