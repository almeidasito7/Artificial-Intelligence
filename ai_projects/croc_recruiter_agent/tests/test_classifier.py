"""
QueryClassifier test suite — hybrid heuristic + LLM fallback.

All tests use fake/inline LLM clients so no real OpenAI calls are made.
"""
from src.core.classifier import QueryClassifier


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — inline fake LLM clients
# ─────────────────────────────────────────────────────────────────────────────

class FakeLLMAlwaysRag:
    def generate_chat(self, messages, temperature=0.0, max_tokens=5):
        return "rag"


class FakeLLMAlwaysSql:
    def generate_chat(self, messages, temperature=0.0, max_tokens=5):
        return "sql"


class FakeLLMReturnsGibberish:
    def generate_chat(self, messages, temperature=0.0, max_tokens=5):
        return "maybe sql i think"


class FakeLLMRaises:
    def generate_chat(self, messages, temperature=0.0, max_tokens=5):
        raise RuntimeError("LLM unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic path — clear SQL winner
# ─────────────────────────────────────────────────────────────────────────────

def test_classify_sql_for_count_query():
    c = QueryClassifier()
    assert c.classify("How many open jobs are there?") == "sql"


def test_classify_sql_for_average_query():
    c = QueryClassifier()
    assert c.classify("What is the average bill rate for placements?") == "sql"


def test_classify_sql_for_candidates_query():
    c = QueryClassifier()
    assert c.classify("List all candidates in the system") == "sql"


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic path — clear RAG winner
# ─────────────────────────────────────────────────────────────────────────────

def test_classify_rag_for_policy_query():
    c = QueryClassifier()
    assert c.classify("What is the PTO policy for contractors?") == "rag"


def test_classify_rag_for_benefits_query():
    c = QueryClassifier()
    assert c.classify("What are the health insurance benefits?") == "rag"


def test_classify_rag_for_procedure_query():
    c = QueryClassifier()
    assert c.classify("Describe the onboarding procedure in detail") == "rag"


def test_classify_rag_for_compliance_query():
    c = QueryClassifier()
    assert c.classify("What are the compliance requirements?") == "rag"


# ─────────────────────────────────────────────────────────────────────────────
# LLM fallback — ambiguous / tied queries
# ─────────────────────────────────────────────────────────────────────────────

def test_classify_ambiguous_uses_llm_fallback_rag():
    """
    Tied scores → LLM decides 'rag'.

    "What is the average bill rate for contractor compliance?"
    SQL score=2 (average + bill rate), RAG score=2 (contractor + compliance)
    → gap=0 → LLM fallback.
    """
    c = QueryClassifier(llm_client=FakeLLMAlwaysRag())
    result = c.classify("What is the average bill rate for contractor compliance?")
    assert result == "rag"


def test_classify_ambiguous_uses_llm_fallback_sql():
    """
    Tied scores → LLM decides 'sql'.

    Same question as above, but LLM is configured to return 'sql'.
    """
    c = QueryClassifier(llm_client=FakeLLMAlwaysSql())
    result = c.classify("What is the average bill rate for contractor compliance?")
    assert result == "sql"


def test_classify_unknown_question_uses_llm():
    """
    No keyword matches on either side → both scores 0 → LLM fallback.
    """
    c = QueryClassifier(llm_client=FakeLLMAlwaysRag())
    result = c.classify("Can you help me understand the general approach here?")
    assert result == "rag"


# ─────────────────────────────────────────────────────────────────────────────
# LLM fallback — error handling
# ─────────────────────────────────────────────────────────────────────────────

def test_classify_llm_gibberish_defaults_to_rag():
    """
    LLM returns something other than 'sql'/'rag' → safe fallback to 'rag'.
    """
    c = QueryClassifier(llm_client=FakeLLMReturnsGibberish())
    result = c.classify("How many onboarding steps we have?")
    assert result == "rag"


def test_classify_llm_raises_defaults_to_rag():
    """
    LLM throws an exception → safe fallback to 'rag'.
    """
    c = QueryClassifier(llm_client=FakeLLMRaises())
    result = c.classify("How many onboarding steps we have?")
    assert result == "rag"


# ─────────────────────────────────────────────────────────────────────────────
# No LLM client configured
# ─────────────────────────────────────────────────────────────────────────────

def test_classify_tied_without_llm_defaults_to_rag():
    """
    Tied scores + no LLM client → default to 'rag' (safer).
    """
    c = QueryClassifier()  # no llm_client
    result = c.classify("How many onboarding steps we have?")
    assert result == "rag"


def test_classify_empty_question_without_llm_defaults_to_rag():
    """
    No keywords match + no LLM → default 'rag'.
    """
    c = QueryClassifier()
    result = c.classify("something completely unrelated")
    assert result == "rag"
