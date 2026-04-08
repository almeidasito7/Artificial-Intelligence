from src.cache.cache_repository import CacheRepository
from src.core.pipelines.llm_pipeline import LLMPipeline
from src.llm.client import OpenAILLMClient
from src.rag.answer_generator import AnswerGenerator
from src.rag.retriever import Retriever


def build_llm_pipeline() -> LLMPipeline:
    llm_client = OpenAILLMClient(model="gpt-4o-mini")
    retriever = Retriever()
    cache_repository = CacheRepository()

    answer_generator = AnswerGenerator(
        llm_client=llm_client,
        max_context_chunks=5,
        max_context_chars_per_chunk=1800,
    )

    return LLMPipeline(
        retriever=retriever,
        answer_generator=answer_generator,
        cache_repository=cache_repository,
        enable_cache=True,
        cache_empty_answers=False,
    )