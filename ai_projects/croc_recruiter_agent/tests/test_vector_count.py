def test_vector_count():
    from src.rag.vector_store import get_collection_count

    count = get_collection_count()

    assert isinstance(count, int)
    assert count >= 0