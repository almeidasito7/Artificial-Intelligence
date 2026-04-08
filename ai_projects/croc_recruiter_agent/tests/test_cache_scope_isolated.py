def test_cache_scope_isolation(tmp_path):
    from src.cache.cache_repository import CacheRepository

    db_path = tmp_path / "cache.db"
    cache = CacheRepository(db_path=str(db_path))

    query = "same question"

    cache.save_cache(query, "answer A", ["doc1"], scope_hash="user_1")

    result = cache.get_cache(query, scope_hash="user_2")

    assert result is None