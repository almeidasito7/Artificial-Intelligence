import time


def test_cache_ttl_expiration(fake_llm, fake_retriever, tmp_path):
    from src.cache.cache_repository import CacheRepository
    from src.core.pipelines.llm_pipeline import LLMPipeline
    from src.rag.answer_generator import AnswerGenerator

    db_path = tmp_path / "ttl_cache.db"

    cache = CacheRepository(db_path=str(db_path), ttl_seconds=1)

    pipeline = LLMPipeline(
        retriever=fake_retriever,
        answer_generator=AnswerGenerator(fake_llm),
        cache_repository=cache,
        enable_cache=True,
    )

    query = "What is onboarding process?"

    # first run → miss
    pipeline.run(query)
    assert fake_llm.call_count == 1

    # second run → hit
    pipeline.run(query)
    assert fake_llm.call_count == 1

    # wait ttl expire
    time.sleep(1.5)

    # third run → miss again
    pipeline.run(query)
    assert fake_llm.call_count == 2