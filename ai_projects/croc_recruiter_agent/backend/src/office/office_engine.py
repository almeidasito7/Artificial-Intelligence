from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from src.office.postgres_client import PostgresClient
from src.office.schema import OFFICE_SCHEMA_SQL
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _looks_like_office_query(question: str) -> bool:
    q = (question or "").lower()
    return any(
        k in q
        for k in [
            "office",
            "desk",
            "table",
            "seat",
            "resource",
            "notebook",
            "mouse",
            "keyboard",
            "headset",
            "ear phone",
            "earphone",
            "monitor",
        ]
    )


def _extract_region(question: str) -> str | None:
    m = re.search(r"\b(in|at)\b\s+([a-zA-ZÀ-ÿ ]+)$", question.strip(), flags=re.IGNORECASE)
    if not m:
        return None
    region = m.group(2).strip()
    return region if region else None


class OfficeEngine:
    def __init__(self, client: PostgresClient) -> None:
        self.client = client

    def supports(self, question: str) -> bool:
        return _looks_like_office_query(question)

    def init_schema(self) -> None:
        statements = [s.strip() for s in OFFICE_SCHEMA_SQL.split(";") if s.strip()]
        for stmt in statements:
            self.client.query(stmt)

    def run(self, question: str) -> Dict[str, Any]:
        if not self.client.available:
            return {
                "answer": (
                    "Office database is not configured.\n\n"
                    "Set OFFICE_DB_DSN in your .env.\n"
                    "Example:\n"
                    "OFFICE_DB_DSN=postgresql://USER:PASSWORD@HOST:5432/DBNAME"
                ),
                "sources": [],
            }

        region = _extract_region(question)
        q = (question or "").lower()

        if any(k in q for k in ["desk", "table", "seat"]):
            sql = """
            SELECT id, table_number, area, status, business_area, office_region
            FROM office.office_sections
            WHERE (%s IS NULL OR office_region ILIKE %s)
            ORDER BY id DESC
            LIMIT 20
            """.strip()
            params: Tuple[Any, ...] = (region, f"%{region}%" if region else None)
            rows = self.client.query(sql, params)
            return {
                "answer": "Here are the latest office sections:\n\n" + json.dumps(rows, ensure_ascii=False, indent=2),
                "sources": [],
            }

        sql = """
        SELECT id, resource_name, type, status, quantity, office_region
        FROM office.office_resources
        WHERE (%s IS NULL OR office_region ILIKE %s)
        ORDER BY id DESC
        LIMIT 20
        """.strip()
        params = (region, f"%{region}%" if region else None)
        rows = self.client.query(sql, params)
        return {
            "answer": "Here are the latest office resources:\n\n" + json.dumps(rows, ensure_ascii=False, indent=2),
            "sources": [],
        }

