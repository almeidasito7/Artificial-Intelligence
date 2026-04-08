from __future__ import annotations
from src.rag.document_loader import load_documents
from src.rag.chunker import chunk_documents
from src.rag.embeddings import generate_embeddings
from src.rag.vector_store import (
    upsert_embeddings,
    get_collection,
    get_chroma_client
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


# reset collection
def reset_collection():
    logger.warning("[INDEXER] Resetting collection...")

    client = get_chroma_client()

    try:
        client.delete_collection(name="documents")
        logger.info("[INDEXER] Collection deleted")
    except Exception:
        logger.info("[INDEXER] No existing collection to delete")

    logger.info("[INDEXER] Collection reset completed")


# validations
def validate_chunks(chunks):
    for i, chunk in enumerate(chunks):
        metadata = chunk.get("metadata", {})

        if "source" not in metadata:
            raise ValueError(f"Chunk {i} missing 'source'")

        if "chunk_id" not in metadata:
            raise ValueError(f"Chunk {i} missing 'chunk_id'")


def validate_embeddings(embedded_chunks):
    for i, chunk in enumerate(embedded_chunks):
        if not chunk.get("embedding"):
            raise ValueError(f"Embedding {i} is empty")

        if not isinstance(chunk.get("metadata"), dict):
            raise ValueError(f"Embedding {i} has invalid metadata")


# pipeline
def run_indexing_pipeline(reset: bool = True):
    logger.info("Starting RAG indexing pipeline")

    # reset collection
    if reset:
        reset_collection()

    # load documents
    documents = load_documents()
    logger.info(f"[INDEXER] Loaded {len(documents)} documents")

    if not documents:
        raise ValueError("No documents found")

    # chunking
    chunks = chunk_documents(documents)
    logger.info(f"[INDEXER] Generated {len(chunks)} chunks")

    if not chunks:
        raise ValueError("No chunks generated")

    validate_chunks(chunks)

    # embeddings
    embedded_chunks = generate_embeddings(chunks)
    logger.info(f"[INDEXER] Generated {len(embedded_chunks)} embeddings")

    if not embedded_chunks:
        raise ValueError("No embeddings generated")

    validate_embeddings(embedded_chunks)

    # vector store
    upsert_embeddings(embedded_chunks)

    # final validation
    collection = get_collection()
    count = collection.count()

    logger.info(f"[INDEXER] Collection now has {count} documents")

    if count == 0:
        raise RuntimeError("Indexing failed — collection is empty")

    logger.info("Indexing completed successfully")


# entrypoint
if __name__ == "__main__":
    run_indexing_pipeline(reset=True)