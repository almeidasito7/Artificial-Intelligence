"""
Router (Orchestrator) test suite.

These tests validate the routing logic, cache behaviour, and debug fields
(cache_hit, engine_used) without touching real LLM / DB / vector-store.

All engines and classifier are injected as fakes via conftest.py.
"""
import pytest

from src.cache.cache_repository import CacheRepository
from src.router import Router
from tests.conftest import FakeClassifier, FakeSqlEngine, FakeRagEngine


# ─────────────────────────────────────────────────────────────────────────────
# Cache-hit behaviour
# ─────────────────────────────────────────────────────────────────────────────

def test_router_cache_hit_does_not_call_any_engine(tmp_path):
    """
    On cache hit the router must return immediately.
    Classifier, SqlEngine and RagEngine must NOT be called.
    """
    db_path = tmp_path / "cache.db"
    cache = CacheRepository(db_path=str(db_path))

    scope_hash = "user_scope_test"
    query = "What is the onboarding process?"

    cache.save_cache(
        query=query,
        response="Cached onboarding answer.",
        sources=["sop_onboarding.md"],
        scope_hash=scope_hash,
    )

    classifier = FakeClassifier()
    sql_engine = FakeSqlEngine()
    rag_engine = FakeRagEngine()

    router = Router(
        classifier=classifier,
        sql_engine=sql_engine,
        rag_engine=rag_engine,
        cache_repository=cache,
        enable_cache=True,
    )

    # Patch scope_hash to match what we saved
    # (We bypass permissions by monkeypatching generate_scope_hash)
    import src.router as router_module
    original_fn = router_module.generate_scope_hash
    router_module.generate_scope_hash = lambda regions, divisions: scope_hash

    try:
        result = router.handle(question=query, user_id="analyst_1")
    finally:
        router_module.generate_scope_hash = original_fn

    # debug fields
    assert result["cache_hit"] is True
    assert result["engine_used"] == "cache"

    # engines must NOT have been called
    assert classifier.call_count == 0
    assert sql_engine.call_count == 0
    assert rag_engine.call_count == 0


def test_router_cache_hit_returns_stored_answer(tmp_path):
    """
    The answer returned on cache hit must be exactly what was saved.
    """
    db_path = tmp_path / "cache.db"
    cache = CacheRepository(db_path=str(db_path))

    scope_hash = "scope_abc"
    query = "What is the PTO policy?"
    saved_answer = "PTO accrues at 1 hour per 30 hours worked."

    cache.save_cache(
        query=query,
        response=saved_answer,
        sources=["policy_contractor.md"],
        scope_hash=scope_hash,
    )

    router = Router(
        classifier=FakeClassifier(),
        sql_engine=FakeSqlEngine(),
        rag_engine=FakeRagEngine(),
        cache_repository=cache,
        enable_cache=True,
    )

    import src.router as router_module
    original_fn = router_module.generate_scope_hash
    router_module.generate_scope_hash = lambda regions, divisions: scope_hash

    try:
        result = router.handle(question=query, user_id="analyst_1")
    finally:
        router_module.generate_scope_hash = original_fn

    assert result["answer"] == saved_answer
    assert result["cache_hit"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Cache-miss → correct engine routing
# ─────────────────────────────────────────────────────────────────────────────

def test_router_cache_miss_routes_to_rag_engine(router, fake_classifier, fake_sql_engine, fake_rag_engine):
    """
    On cache miss with classifier returning 'rag',
    only the RAG engine is called.
    """
    fake_classifier.decision = "rag"

    result = router.handle(question="What is the onboarding process?", user_id="analyst_1")

    assert result["cache_hit"] is False
    assert result["engine_used"] == "rag"
    assert fake_rag_engine.call_count == 1
    assert fake_sql_engine.call_count == 0


def test_router_cache_miss_routes_to_sql_engine(tmp_path):
    """
    On cache miss with classifier returning 'sql',
    only the SQL engine is called.
    """
    db_path = tmp_path / "cache.db"
    cache = CacheRepository(db_path=str(db_path))

    classifier = FakeClassifier(decision="sql")
    sql_engine = FakeSqlEngine()
    rag_engine = FakeRagEngine()

    router = Router(
        classifier=classifier,
        sql_engine=sql_engine,
        rag_engine=rag_engine,
        cache_repository=cache,
        enable_cache=True,
    )

    result = router.handle(question="How many candidates are there?", user_id="analyst_1")

    assert result["cache_hit"] is False
    assert result["engine_used"] == "sql"
    assert sql_engine.call_count == 1
    assert rag_engine.call_count == 0


# ─────────────────────────────────────────────────────────────────────────────
# cache disabled
# ─────────────────────────────────────────────────────────────────────────────

def test_router_with_cache_disabled_always_calls_engine(tmp_path):
    """
    When enable_cache=False the engine must always be called
    even if the same question is asked twice.
    """
    db_path = tmp_path / "cache.db"
    cache = CacheRepository(db_path=str(db_path))

    rag_engine = FakeRagEngine()

    router = Router(
        classifier=FakeClassifier(decision="rag"),
        sql_engine=FakeSqlEngine(),
        rag_engine=rag_engine,
        cache_repository=cache,
        enable_cache=False,
    )

    question = "What is the onboarding process?"

    router.handle(question=question, user_id="analyst_1")
    router.handle(question=question, user_id="analyst_1")

    assert rag_engine.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# Second call is a cache hit (save → get)
# ─────────────────────────────────────────────────────────────────────────────

def test_router_second_call_is_cache_hit(router, fake_rag_engine):
    """
    First call → cache miss (engine called, answer saved).
    Second identical call → cache hit (engine NOT called again).
    """
    question = "What is the onboarding process?"

    first = router.handle(question=question, user_id="analyst_1")
    assert first["cache_hit"] is False
    assert fake_rag_engine.call_count == 1

    second = router.handle(question=question, user_id="analyst_1")
    assert second["cache_hit"] is True
    assert second["engine_used"] == "cache"
    assert fake_rag_engine.call_count == 1  # engine was NOT called again


# ─────────────────────────────────────────────────────────────────────────────
# Response contract
# ─────────────────────────────────────────────────────────────────────────────

def test_router_result_always_has_required_fields(router):
    """
    Every result from the router must contain answer, cache_hit, engine_used.
    """
    result = router.handle(question="What is the onboarding process?", user_id="analyst_1")

    assert "answer" in result
    assert "cache_hit" in result
    assert "engine_used" in result
    assert isinstance(result["answer"], str)
    assert isinstance(result["cache_hit"], bool)


def test_router_empty_question_returns_gracefully(router):
    """
    Empty question must return a safe error message without calling any engine.
    """
    result = router.handle(question="   ", user_id="analyst_1")

    assert result["cache_hit"] is False
    assert result["engine_used"] is None
    assert len(result["answer"]) > 0
