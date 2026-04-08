from __future__ import annotations
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from src.utils.logger import get_logger

logger = get_logger(__name__)

# standardized embedding model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# versioning
EMBEDDING_VERSION = "v1"

_model = None


# model
def get_embedding_model() -> SentenceTransformer:
    global _model

    if _model is None:
        logger.info(f"[EMBEDDINGS] Loading model: {EMBEDDING_MODEL_NAME}")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _model


# text preparation
def prepare_text_for_embedding(chunk: Dict[str, Any]) -> str:
    content = (chunk.get("content") or "").strip()
    metadata = chunk.get("metadata") or {}

    source = metadata.get("source", "unknown")
    section = metadata.get("section", "General")
    document_type = metadata.get("document_type", "general")

    enriched_text = (
        f"[{document_type.upper()} | {section} | {source}]\n\n"
        f"{content}"
    )

    return enriched_text


# embedding
def generate_embeddings(
    chunks: List[Dict[str, Any]],
    batch_size: int = 16
) -> List[Dict[str, Any]]:

    if not chunks:
        logger.warning("[EMBEDDINGS] Empty chunk list received")
        return []

    model = get_embedding_model()

    valid_chunks = [
        chunk for chunk in chunks
        if (chunk.get("content") or "").strip()
    ]

    if not valid_chunks:
        logger.warning("[EMBEDDINGS] No valid chunks to embed")
        return []

    texts = [prepare_text_for_embedding(chunk) for chunk in valid_chunks]

    logger.info(f"[EMBEDDINGS] Generating embeddings for {len(texts)} chunks")

    try:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True
        )
    except Exception as e:
        logger.exception("[EMBEDDINGS] Encoding failed", extra={"error": str(e)})
        raise

    embedded_chunks = []

    for chunk, vector in zip(valid_chunks, vectors):
        metadata = chunk.get("metadata") or {}

        # add versioning to metadata
        metadata["embedding_version"] = EMBEDDING_VERSION

        embedded_chunks.append({
            "content": chunk["content"],
            "text": chunk["content"], 
            "embedding": vector.tolist(),
            "metadata": metadata
        })

    logger.info(f"[EMBEDDINGS] Generated {len(embedded_chunks)} embeddings")

    return embedded_chunks