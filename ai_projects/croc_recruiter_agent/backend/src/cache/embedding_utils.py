from typing import List
from src.rag.embeddings import get_embedding_model


def generate_query_embedding(query: str) -> List[float]:
    model = get_embedding_model()

    embedding = model.encode(
        [query.strip()],
        normalize_embeddings=True,
    )[0]

    return embedding.tolist()