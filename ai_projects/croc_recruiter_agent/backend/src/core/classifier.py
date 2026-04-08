from __future__ import annotations

import re
from typing import Any, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ── Keyword vocabulary ────────────────────────────────────────────────────────

SQL_KEYWORDS = {
    "how many",
    "count",
    "average",
    "avg",
    "total",
    "sum",
    "list all",
    "candidates",
    "placements",
    "open jobs",
    "bill rate",
    "salary",
    "hired",
    "placement",
    "job",
    "candidate",
}

RAG_KEYWORDS = {
    "policy",
    "policies",
    "procedure",
    "guideline",
    "onboarding",
    "benefit",
    "benefits",
    "vacation",
    "pto",
    "time off",
    "time-off",
    "holiday",
    "conduct",
    "confidential",
    "compliance",
    "nda",
    "regulation",
    "contract",
    "contractor",
    "attendance",
    "discipline",
    "termination",
    "offboarding",
    "401k",
    "health insurance",
    "workers compensation",
    "disability",
    "cobra",
    "steps",
    "process",
    "rule",
    "rules",
    "requirement",
    "requirements",
}

# ── LLM fallback prompt ───────────────────────────────────────────────────────

_CLASSIFIER_PROMPT = """You are a query router for a staffing agency's BI assistant.

TASK: Decide if the question should be answered from the SQL database or from documents.

SQL DATABASE — structured records about:
- jobs: open positions, status, region, division
- candidates: applicants and their placements
- placements: active assignments, bill rate, pay rate
→ Use SQL for: counts, totals, averages, filters, specific data lookups.

DOCUMENTS (RAG) — unstructured HR content:
- HR policies (time off, attendance, conduct, confidentiality)
- SOPs (onboarding steps, offboarding, compliance procedures)
- FAQs (benefits, health insurance, 401k, disability)
→ Use RAG for: policy explanations, procedure steps, rules, guidelines, "how does X work".

QUESTION: {question}

Respond with ONLY one word (no punctuation, no explanation):
sql
rag""".strip()


# ── Classifier ────────────────────────────────────────────────────────────────


class QueryClassifier:
    """
    Hybrid query classifier — SQL vs RAG.

    Strategy (in order):
    1. Heuristic keyword scoring (fast, deterministic)
       → Clear winner (gap > 0): use the heuristic result directly.
    2. LLM fallback (flexible, context-aware)
       → Tied scores (gap == 0): ask the LLM to decide.
    3. Safe default
       → Tied + no LLM client available: return "rag" (safer for policy questions).

    Output is always strictly "sql" or "rag".
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        self.llm_client = llm_client

    def classify(self, question: str) -> str:
        sql_score, rag_score = self._score(question)
        gap = abs(sql_score - rag_score)

        if gap > 0:
            decision = "sql" if sql_score > rag_score else "rag"
            self._log(
                strategy="heuristic",
                decision=decision,
                sql_score=sql_score,
                rag_score=rag_score,
                confidence="high",
            )
            return decision

        # Scores are tied — use LLM fallback
        if self.llm_client is not None:
            decision = self._classify_with_llm(question)
            self._log(
                strategy="llm_fallback",
                decision=decision,
                sql_score=sql_score,
                rag_score=rag_score,
                confidence="medium",
            )
            return decision

        # No LLM available — default to rag (policy questions are safer)
        self._log(
            strategy="default_rag",
            decision="rag",
            sql_score=sql_score,
            rag_score=rag_score,
            confidence="low",
        )
        return "rag"

    # ── internals ────────────────────────────────────────────────────────────

    def _score(self, question: str):
        normalized = question.lower()

        def matches(keyword: str) -> bool:
            if " " in keyword or "-" in keyword:
                # Multi-word or hyphenated: substring match is precise enough.
                return keyword in normalized
            # Single word: word boundary to avoid partial matches
            # e.g. "contract" must NOT match inside "contractor"
            return bool(re.search(rf"\b{re.escape(keyword)}\b", normalized))

        sql_score = sum(1 for kw in SQL_KEYWORDS if matches(kw))
        rag_score = sum(1 for kw in RAG_KEYWORDS if matches(kw))
        return sql_score, rag_score

    def _classify_with_llm(self, question: str) -> str:
        try:
            messages = [
                {
                    "role": "user",
                    "content": _CLASSIFIER_PROMPT.format(question=question),
                }
            ]

            response = self.llm_client.generate_chat(
                messages=messages,
                temperature=0.0,
                max_tokens=5,
            )

            decision = response.strip().lower()

            if decision not in ("sql", "rag"):
                logger.warning(
                    "classifier.llm_invalid_response",
                    extra={"response": repr(response), "fallback": "rag"},
                )
                return "rag"

            return decision

        except Exception as exc:
            logger.exception(
                "classifier.llm_failed",
                extra={"error": str(exc), "fallback": "rag"},
            )
            return "rag"

    def _log(
        self,
        strategy: str,
        decision: str,
        sql_score: int,
        rag_score: int,
        confidence: str,
    ) -> None:
        logger.info(
            "classifier.decision",
            extra={
                "strategy": strategy,
                "decision": decision,
                "sql_score": sql_score,
                "rag_score": rag_score,
                "confidence": confidence,
            },
        )
