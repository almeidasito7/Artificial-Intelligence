def test_pipeline_cache_hit_and_miss(pipeline, fake_llm):
    query = "What is onboarding process?"

    # first run → miss
    result_1 = pipeline.run(query)

    assert result_1["cache_hit"] is False
    assert fake_llm.call_count == 1
    assert "[Source:" in result_1["answer"]

    # second run → hit
    result_2 = pipeline.run(query)

    assert result_2["cache_hit"] is True
    assert fake_llm.call_count == 1  # did not call again
    assert result_2["answer"] == result_1["answer"] 

def test_pipeline_does_not_cache_empty_answer(fake_llm, fake_retriever, tmp_path):
    from src.cache.cache_repository import CacheRepository
    from src.core.pipelines.llm_pipeline import LLMPipeline
    from src.rag.answer_generator import AnswerGenerator

    class EmptyRetriever:
        def retrieve(self, query):
            return []

    db_path = tmp_path / "cache.db"

    pipeline = LLMPipeline(
        retriever=EmptyRetriever(),
        answer_generator=AnswerGenerator(fake_llm),
        cache_repository=CacheRepository(db_path=str(db_path)),
        enable_cache=True,
    )

    query = "unknown question"

    result = pipeline.run(query)

    assert result["sources"] == []

    # second call should not be cache hit
    result_2 = pipeline.run(query)

    assert result_2["cache_hit"] is False