from __future__ import annotations

import os
from typing import List, Dict, Any, Optional

import chromadb

from src.utils.logger import get_logger

logger = get_logger(__name__)


# config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
CHROMA_PATH = os.path.join(BASE_DIR, "data", "chroma")
COLLECTION_NAME = "documents"

UPSERT_BATCH_SIZE = 100

_client = None
_collection = None


# client
def get_chroma_client():
    global _client

    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)

        logger.info("[VECTOR STORE] Initializing Chroma client")
        logger.info(f"[VECTOR STORE] Path: {CHROMA_PATH}")

        _client = chromadb.PersistentClient(path=CHROMA_PATH)

    return _client


def get_collection():
    global _collection

    if _collection is None:
        client = get_chroma_client()

        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(f"[VECTOR STORE] Using collection: {COLLECTION_NAME}")

    return _collection


# validation
def generate_chunk_id(chunk: Dict[str, Any]) -> str:
    metadata = chunk.get("metadata") or {}

    source = metadata.get("source")
    chunk_id = metadata.get("chunk_id")

    if not source or chunk_id is None:
        raise ValueError("Metadata must contain 'source' and 'chunk_id'")

    return f"{source}_{chunk_id}"


def validate_chunk_structure(chunk: Dict[str, Any]):
    if not chunk.get("content"):
        raise ValueError("Chunk missing 'content'")

    if not chunk.get("embedding"):
        raise ValueError("Chunk missing 'embedding'")

    if not isinstance(chunk.get("metadata"), dict):
        raise ValueError("Invalid metadata")


# upsert
def upsert_embeddings(embedded_chunks: List[Dict[str, Any]]):
    if not embedded_chunks:
        logger.warning("[VECTOR STORE] No embeddings to insert")
        return

    collection = get_collection()

    logger.info(f"[VECTOR STORE] Upserting {len(embedded_chunks)} chunks")

    try:
        for i in range(0, len(embedded_chunks), UPSERT_BATCH_SIZE):
            batch = embedded_chunks[i:i + UPSERT_BATCH_SIZE]

            ids, documents, metadatas, embeddings = [], [], [], []

            for chunk in batch:
                validate_chunk_structure(chunk)

                ids.append(generate_chunk_id(chunk))
                documents.append(chunk["content"])
                metadatas.append(chunk["metadata"])
                embeddings.append(chunk["embedding"])

            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )

        count = collection.count()
        logger.info(f"[VECTOR STORE] Total documents: {count}")

        if count == 0:
            raise RuntimeError("Collection is empty after upsert")

    except Exception as e:
        logger.exception("[VECTOR STORE] Upsert failed", extra={"error": str(e)})
        raise


# query
def query_similar_chunks(
    query_embedding: List[float],
    top_k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    collection = get_collection()

    if not query_embedding:
        raise ValueError("Query embedding cannot be empty")

    logger.info(f"[VECTOR STORE] Query top_k={top_k}")

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters,
            include=["documents", "metadatas", "distances"]
        )

    except Exception as e:
        logger.exception("[VECTOR STORE] Query failed", extra={"error": str(e)})
        raise

    docs = results.get("documents", [[]])[0]
    dists = results.get("distances", [[]])[0]

    logger.info(f"[VECTOR STORE] Retrieved {len(docs)} results")

    if dists:
        logger.info(
            "[VECTOR STORE] Distance stats",
            extra={
                "min": min(dists),
                "max": max(dists),
                "avg": sum(dists) / len(dists),
            },
        )

    return results


# debug / utils
def get_collection_count() -> int:
    return get_collection().count()
