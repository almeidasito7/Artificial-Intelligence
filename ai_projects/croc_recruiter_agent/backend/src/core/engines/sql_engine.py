from __future__ import annotations

from typing import Any, Dict

from src.utils.logger import get_logger
from src.llm.sql_generator import generate_sql
from src.security.validator import sanitize_sql, validate_sql
from src.security.rls import apply_rls
from src.database.db import execute_query
from src.core.formatters.response_formatter import format_sql_response

logger = get_logger(__name__)


class SqlEngine:
    """
    Wrapper for the SQL execution pipeline.

    Responsibilities:
    - Generate SQL from natural language (LLM)
    - Validate SQL (security guard)
    - Apply RLS (permissions enforcement)
    - Execute query against the database
    - Format response as human-readable text

    Output contract:
    {
        "answer": "...",
        "sources": []
    }

    Does NOT: manage cache, classify queries, or load user permissions.
    The Router is responsible for those concerns.
    """

    def __init__(self, llm_client: Any | None = None) -> None:
        self.llm_client = llm_client

    def run(self, question: str, user_id: str, permissions: Dict[str, Any]) -> Dict[str, Any]:
        sql = sanitize_sql(generate_sql(question, llm_client=self.llm_client))
        logger.info(
            "sql_engine.generated",
            extra={"sql_preview": (sql or "")[:200], "sql_len": len(sql or "")},
        )

        validate_sql(sql)
        logger.info("sql_engine.validated")

        secure_sql = apply_rls(sql, permissions)
        logger.info("sql_engine.rls_applied")

        rows = execute_query(secure_sql)
        logger.info("sql_engine.executed", extra={"rows": len(rows)})

        answer = format_sql_response(rows)

        return {
            "answer": answer,
            "sources": [],
        }
