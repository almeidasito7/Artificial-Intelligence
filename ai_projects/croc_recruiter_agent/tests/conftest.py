import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from src.cache.cache_repository import CacheRepository
from src.core.pipelines.llm_pipeline import LLMPipeline
from src.rag.answer_generator import AnswerGenerator
from src.router import Router
from tests.mocks.fake_llm_client import FakeLLMClient


class FakeRetriever:
    def retrieve(self, query: str):
        return [
            {
                "text": "Contractors must complete onboarding before access.",
                "source": "policy_contractor.md",
                "metadata": {"section": "onboarding"},
                "similarity": 0.9,
            }
        ]


class FakeClassifier:
    def __init__(self, decision: str = "rag"):
        self.decision = decision
        self.call_count = 0

    def classify(self, question: str) -> str:
        self.call_count += 1
        return self.decision


class FakeSqlEngine:
    def __init__(self):
        self.call_count = 0

    def run(self, question: str, user_id: str, permissions: dict) -> dict:
        self.call_count += 1
        return {"answer": "SQL mocked answer.", "sources": []}


class FakeRagEngine:
    def __init__(self):
        self.call_count = 0

    def run(self, question: str, permissions: dict) -> dict:
        self.call_count += 1
        return {
            "answer": "This is a mocked answer based on retrieved context.",
            "sources": ["policy_contractor.md"],
        }


@pytest.fixture
def fake_llm():
    return FakeLLMClient()


@pytest.fixture
def fake_retriever():
    return FakeRetriever()


@pytest.fixture
def temp_cache(tmp_path):
    db_path = tmp_path / "test_cache.db"
    return CacheRepository(db_path=str(db_path))


@pytest.fixture
def pipeline(fake_llm, fake_retriever, temp_cache):
    answer_generator = AnswerGenerator(llm_client=fake_llm)

    return LLMPipeline(
        retriever=fake_retriever,
        answer_generator=answer_generator,
        cache_repository=temp_cache,
        enable_cache=True,
    )


@pytest.fixture
def fake_classifier():
    return FakeClassifier(decision="rag")


@pytest.fixture
def fake_sql_engine():
    return FakeSqlEngine()


@pytest.fixture
def fake_rag_engine():
    return FakeRagEngine()


@pytest.fixture
def router(fake_classifier, fake_sql_engine, fake_rag_engine, temp_cache):
    return Router(
        classifier=fake_classifier,
        sql_engine=fake_sql_engine,
        rag_engine=fake_rag_engine,
        cache_repository=temp_cache,
        enable_cache=True,
    )
