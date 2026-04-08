from __future__ import annotations

import time
import re
import json
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger
from src.security.permissions import get_user_permissions, generate_scope_hash
from src.security.guardrails import check_message
from src.core.llm_route_planner import LLMRoutePlanner, RoutePlan

logger = get_logger(__name__)


class Router:
    """
    Central Orchestrator — single point of control for every request.

    Flow (strictly in this order):
        1. Load user permissions  → generate scope_hash  (RLS-ready)
        2. Cache check            → return immediately on hit
        3. Classify query         → 'sql' or 'rag'
        4. Route to engine        → SqlEngine or RagEngine
        5. Save to cache          → after successful response
        6. Log                    → engine_used, cache_hit, elapsed_ms

    Does NOT:
    - Execute SQL
    - Generate embeddings
    - Do retrieval
    - Apply RLS directly

    Those responsibilities belong to SqlEngine, RagEngine and CacheRepository.
    """

    def __init__(
        self,
        classifier: Any,
        sql_engine: Any,
        rag_engine: Any,
        route_planner: LLMRoutePlanner | None = None,
        candidates_engine: Any | None = None,
        office_engine: Any | None = None,
        cache_repository: Any | None = None,
        enable_cache: bool = True,
    ) -> None:
        self.classifier = classifier
        self.sql_engine = sql_engine
        self.rag_engine = rag_engine
        self.route_planner = route_planner
        self.candidates_engine = candidates_engine
        self.office_engine = office_engine
        self.cache_repository = cache_repository
        self.enable_cache = enable_cache

    def handle(self, question: str, user_id: str) -> Dict[str, Any]:
        question = (question or "").strip()
        start_time = time.monotonic()

        if not question:
            return {
                "answer": "Question cannot be empty.",
                "cache_hit": False,
                "engine_used": None,
                "sources": [],
            }

        guardrail = check_message(question)
        if not guardrail.allowed:
            return {
                "answer": guardrail.message,
                "cache_hit": False,
                "engine_used": "guardrail",
                "sources": [],
            }

        # Step 1 — Load user context (must happen before any other decision)
        permissions = get_user_permissions(user_id)
        scope_hash = generate_scope_hash(
            permissions.get("regions", []),
            permissions.get("divisions", []),
        )

        logger.info(
            "router.user_context_loaded",
            extra={"user_id": user_id, "scope_hash": scope_hash[:8]},
        )

        # Step 2 — Messages (simple conversation) should not hit cache / DB / RAG.
        if self._is_simple_message(question):
            return {
                "answer": self._message_response(question),
                "cache_hit": False,
                "engine_used": "message",
                "sources": [],
            }

        # Step 2 — Cache check (FIRST — before classification and engine calls)
        should_skip_cache = self._is_access_question(question) or self._looks_like_candidate_search(question)
        if self.enable_cache and self.cache_repository is not None and not should_skip_cache:
            cached = self._try_cache_get(question, scope_hash)

            if cached:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)

                logger.info(
                    "router.cache_hit",
                    extra={
                        "user_id": user_id,
                        "elapsed_ms": elapsed_ms,
                    },
                )

                return {
                    "answer": re.sub(r"(?i)^answer:\s*\n?", "", (cached["response"] or "").strip()),
                    "cache_hit": True,
                    "engine_used": "cache",
                    "sources": cached.get("sources", []),
                }

        logger.info("router.cache_miss", extra={"user_id": user_id})

        # Step 3 — LLM route planning (preferred)
        planned = self._plan_route(question)
        if planned is not None:
            planned = self._validate_plan(question, planned)
            handled = self._handle_planned_route(
                planned=planned,
                question=question,
                user_id=user_id,
                permissions=permissions,
                scope_hash=scope_hash,
            )
            if handled is not None:
                return handled
            if planned.route in {"sql", "rag"}:
                return self._run_engine_and_cache(
                    engine_type=planned.route,
                    question=question,
                    user_id=user_id,
                    permissions=permissions,
                    scope_hash=scope_hash,
                )

        if self._is_access_question(question):
            return {
                "answer": self._format_access_info(user_id, permissions),
                "cache_hit": False,
                "engine_used": "access_info",
                "sources": [],
            }

        # Step 3b — Candidate search (staffing.db)
        if self.candidates_engine is not None and self._looks_like_candidate_search(question):
            result = self.candidates_engine.run(
                question=question,
                user_id=user_id,
                permissions=permissions,
            )
            answer = result.get("answer", "")
            sources = result.get("sources", [])
            return {
                "answer": answer,
                "cache_hit": False,
                "engine_used": "candidates_info",
                "sources": sources,
            }

        # Step 3c — Office DB (direct Postgres) is paused for now

        # Step 3 — Classify query
        engine_type = self.classifier.classify(question)

        logger.info(
            "router.classified",
            extra={"user_id": user_id, "engine_type": engine_type},
        )

        return self._run_engine_and_cache(
            engine_type=engine_type,
            question=question,
            user_id=user_id,
            permissions=permissions,
            scope_hash=scope_hash,
        )

    # ------------------------------------------------------------------ cache

    def _run_engine_and_cache(
        self,
        engine_type: str,
        question: str,
        user_id: str,
        permissions: Dict[str, Any],
        scope_hash: str,
    ) -> Dict[str, Any]:
        try:
            if engine_type == "sql":
                result = self.sql_engine.run(
                    question=question,
                    user_id=user_id,
                    permissions=permissions,
                )
            else:
                result = self.rag_engine.run(
                    question=question,
                    permissions=permissions,
                )

            answer = result.get("answer", "") or ""
            sources = result.get("sources", []) or []

            if self.enable_cache and self.cache_repository is not None and answer:
                self._try_cache_save(
                    query=question,
                    answer=answer,
                    sources=sources,
                    scope_hash=scope_hash,
                )

            return {
                "answer": answer,
                "cache_hit": False,
                "engine_used": engine_type,
                "sources": sources,
            }

        except Exception as exc:
            logger.exception("router.engine_failed", extra={"engine_used": engine_type, "error": str(exc)})
            if engine_type == "sql":
                return {
                    "answer": (
                        "I couldn't find relevant information on that topic. "
                        "You can ask about another subject or rephrase your question."
                    ),
                    "cache_hit": False,
                    "engine_used": engine_type,
                    "sources": [],
                }
            return {
                "answer": "Something went wrong. Please try again in a few minutes.",
                "cache_hit": False,
                "engine_used": engine_type,
                "sources": [],
            }

    def _try_simple_message(self, question: str) -> str | None:
        q = (question or "").strip().lower()
        if not q:
            return None

        greetings = {"hi", "hello", "hey", "oi", "ola", "olá"}
        thanks = {"thanks", "thank you", "thx", "obrigado", "obrigada", "valeu"}

        if q in greetings:
            return "Hi! What can I help you with?"
        if q in thanks or any(t in q for t in thanks):
            return "You're welcome. What would you like to do next?"

        if q in {"help", "ajuda"}:
            return (
                "I can help with:\n"
                "- Staffing data (jobs, candidates, placements)\n"
                "- Company policies & SOPs\n"
                "- Office resources (Postgres, when configured)\n"
            )

        return None

    def _is_simple_message(self, question: str) -> bool:
        q = (question or "").strip().lower()
        if not q:
            return False
        if re.match(r"^(hi|hello|hey|oi|ola|olá)\b", q):
            return True
        if re.match(r"^(good morning|good afternoon|good evening)\b", q):
            return True
        if re.match(r"^(bom dia|boa tarde|boa noite)\b", q):
            return True
        if any(x in q for x in {"who are you", "what can you do", "help", "ajuda"}):
            return True
        if any(x in q for x in {"thanks", "thank you", "thx", "obrigado", "obrigada", "valeu"}):
            return True
        if q in {"ok", "okay", "kk", "k", "certo", "beleza", "top"}:
            return True
        return False

    def _message_response(self, question: str) -> str:
        q = (question or "").strip().lower()
        if re.match(r"^(hi|hello|hey|oi|ola|olá)\b", q) or re.match(r"^(good morning|good afternoon|good evening)\b", q) or re.match(r"^(bom dia|boa tarde|boa noite)\b", q):
            return "Hi! What can I help you with?"
        if any(x in q for x in {"thanks", "thank you", "thx", "obrigado", "obrigada", "valeu"}):
            return "You're welcome. What would you like to do next?"
        if "who are you" in q:
            return "I'm Croc. I can help with staffing data and company policies."
        if "help" in q or "ajuda" in q or "what can you do" in q:
            return (
                "I can help with:\n"
                "- Staffing database (jobs, candidates, placements)\n"
                "- Company policies & procedures\n"
                "Ask a question to get started."
            )
        if q in {"ok", "okay", "certo", "beleza"}:
            return "Got it. What would you like to check next?"
        return "How can I help?"

    def _is_access_question(self, question: str) -> bool:
        q = (question or "").lower()
        return any(
            k in q
            for k in [
                "coverage regions",
                "coverage region",
                "my access",
                "access regions",
                "access region",
                "what regions",
                "which regions",
                "what divisions",
                "which divisions",
                "my regions",
                "my divisions",
                "permiss",
                "permission",
                "permissions",
            ]
        )

    def _format_access_info(self, user_id: str, permissions: Dict[str, Any]) -> str:
        regions = permissions.get("regions", []) or []
        divisions = permissions.get("divisions", []) or []

        regions_txt = ", ".join(regions) if regions else "none"
        divisions_txt = ", ".join(divisions) if divisions else "none"

        return (
            f"Your access profile ({user_id}):\n"
            f"- Regions: {regions_txt}\n"
            f"- Divisions: {divisions_txt}"
        )

    def _plan_route(self, question: str) -> RoutePlan | None:
        if self.route_planner is None:
            return None
        return self.route_planner.plan(question)

    def _validate_plan(self, question: str, planned: RoutePlan) -> RoutePlan:
        if self._is_simple_message(question):
            return RoutePlan(route="message", tool_name=None, tool_input=None)
        if self._is_access_question(question):
            return RoutePlan(route="access_info", tool_name=None, tool_input=None)
        if self._looks_like_candidate_search(question):
            return RoutePlan(route="candidates_info", tool_name=None, tool_input=None)
        return planned

    def _handle_planned_route(
        self,
        planned: RoutePlan,
        question: str,
        user_id: str,
        permissions: Dict[str, Any],
        scope_hash: str,
    ) -> Dict[str, Any] | None:
        if planned.route == "access_info":
            return {
                "answer": self._format_access_info(user_id, permissions),
                "cache_hit": False,
                "engine_used": "access_info",
                "sources": [],
            }

        if planned.route == "message":
            return {
                "answer": self._message_response(question),
                "cache_hit": False,
                "engine_used": "message",
                "sources": [],
            }

        if planned.route == "candidates_info" and self.candidates_engine is not None:
            try:
                result = self.candidates_engine.run(
                    question=question,
                    user_id=user_id,
                    permissions=permissions,
                )
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                return {"answer": answer, "cache_hit": False, "engine_used": "candidates_info", "sources": sources}
            except Exception as exc:
                logger.exception("router.candidates_engine_failed", extra={"error": str(exc)})

        if planned.route in {"sql", "rag"}:
            return None

        return None

    def _looks_like_candidate_search(self, question: str) -> bool:
        q = (question or "").lower()
        if "candidate" in q or "candidates" in q:
            return True
        if "years of experience" in q or "years experience" in q or "skills" in q:
            return True
        if q.startswith("i want a candidate") or q.startswith("find a candidate"):
            return True
        return False

    def _try_cache_get(self, query: str, scope_hash: str) -> Optional[Dict[str, Any]]:
        try:
            return self.cache_repository.get_cache(
                query=query,
                scope_hash=scope_hash,
            )
        except Exception as exc:
            logger.exception(
                "router.cache_get_failed",
                extra={"error": str(exc)},
            )
            return None

    def _try_cache_save(
        self,
        query: str,
        answer: str,
        sources: List[str],
        scope_hash: str,
    ) -> None:
        try:
            self.cache_repository.save_cache(
                query=query,
                response=answer,
                sources=sources,
                scope_hash=scope_hash,
            )
            logger.info("router.cache_saved", extra={"query": query})
        except Exception as exc:
            logger.exception(
                "router.cache_save_failed",
                extra={"error": str(exc)},
            )
