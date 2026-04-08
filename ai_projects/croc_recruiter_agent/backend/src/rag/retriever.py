from __future__ import annotations

from typing import List, Dict, Any

from src.rag.embeddings import get_embedding_model
from src.rag.vector_store import query_similar_chunks
from src.utils.logger import get_logger

logger = get_logger(__name__)


# config
TOP_K = 5
DISTANCE_THRESHOLD = 0.75  
MIN_RESULTS = 2  


class Retriever:
    def __init__(
        self,
        top_k: int = TOP_K,
        distance_threshold: float = DISTANCE_THRESHOLD,
    ) -> None:
        self.top_k = top_k
        self.distance_threshold = distance_threshold
        self.embedding_model = None

    # embedding
    def _generate_query_embedding(self, question: str) -> List[float]:
        if self.embedding_model is None:
            self.embedding_model = get_embedding_model()

        embedding = self.embedding_model.encode(
            [question],
            normalize_embeddings=True,
        )[0]

        return embedding.tolist()

    # retrieve
    def retrieve(self, question: str) -> List[Dict[str, Any]]:
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        logger.info("retriever.query", extra={"query": question})

        query_embedding = self._generate_query_embedding(question)

        results = query_similar_chunks(
            query_embedding=query_embedding,
            top_k=self.top_k,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        raw_results = []
        filtered_results: List[Dict[str, Any]] = []

        for doc, meta, dist in zip(documents, metadatas, distances):
            score = 1 - dist

            item = {
                "text": doc,
                "metadata": meta or {},
                "source": (meta or {}).get("source"),
                "score": score,
                "distance": dist,
                "similarity": score,
            }

            raw_results.append(item)

            if dist <= self.distance_threshold:
                filtered_results.append(item)

        # fallback 
        if len(filtered_results) < MIN_RESULTS:
            logger.warning(
                "retriever.low_results_fallback",
                extra={
                    "filtered": len(filtered_results),
                    "using_top_k": len(raw_results),
                },
            )
            filtered_results = raw_results

        # sort final
        filtered_results.sort(key=lambda x: x["score"], reverse=True)

        logger.info(
            "retriever.results",
            extra={
                "query": question,
                "returned": len(filtered_results),
            },
        )

        if filtered_results:
            best = filtered_results[0]
            logger.info(
                "retriever.best_match",
                extra={
                    "score": round(best["score"], 4),
                    "source": best.get("source"),
                },
            )
        else:
            logger.warning("retriever.no_results")

        return filtered_results


_default_retriever: Retriever | None = None


def retrieve_chunks(question: str):
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = Retriever()
    return _default_retriever.retrieve(question)
