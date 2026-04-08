def test_cache_repository_save_and_get(tmp_path):
    from src.cache.cache_repository import CacheRepository

    db_path = tmp_path / "cache.db"
    cache = CacheRepository(db_path=str(db_path))

    query = "test query"
    response = "test response"
    sources = ["doc1.md"]
    scope_hash = "test_scope"

    # SAVE
    cache.save_cache(
        query=query,
        response=response,
        sources=sources,
        scope_hash=scope_hash,
    )

    # GET
    result = cache.get_cache(
        query=query,
        scope_hash=scope_hash,
    )

    assert result is not None
    assert result["response"] == response
    assert result["sources"] == sources