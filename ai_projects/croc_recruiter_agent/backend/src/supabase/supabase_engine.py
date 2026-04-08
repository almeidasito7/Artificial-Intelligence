from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.supabase.postgrest_client import SupabasePostgrestClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SupabasePlan:
    table: str
    filters: Dict[str, str]


_PLAN_PROMPT = """
You translate a user request into a Supabase PostgREST query for the office schema.

Return ONLY JSON:
{
  "table": "office_sections|office_resources",
  "filters": {
    "status": "eq.available|eq.occupied|eq.maintenance|eq.in_use",
    "office_region": "ilike.*Sao Paulo*",
    "area": "ilike.*Cafeteria*",
    "business_area": "ilike.*TI*",
    "resource_name": "ilike.*Notebook*",
    "type": "ilike.*Eletrônico*"
  }
}

Rules:
- Use only filters that make sense.
- Prefer ilike.*...* for free-text.
- If user didn't specify a filter, omit it.

User message: {question}
""".strip()


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _heuristic_plan(question: str) -> SupabasePlan:
    q = (question or "").lower()
    table = "office_resources"
    if any(k in q for k in ["desk", "table", "seat", "mesa"]):
        table = "office_sections"

    filters: Dict[str, str] = {}
    region = _extract_region(question)
    if region:
        filters["office_region"] = f"ilike.*{region}*"
    return SupabasePlan(table=table, filters=filters)


def _extract_region(question: str) -> str | None:
    m = re.search(r"\b(in|at|em|no|na)\b\s+([a-zA-ZÀ-ÿ0-9 ]+)$", question.strip(), flags=re.IGNORECASE)
    if not m:
        return None
    region = m.group(2).strip()
    return region if region else None


class SupabaseEngine:
    def __init__(self, client: SupabasePostgrestClient, llm_client: Any | None = None) -> None:
        self.client = client
        self.llm_client = llm_client

    @property
    def available(self) -> bool:
        return self.client.available

    def supports(self, question: str) -> bool:
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
                "monitor",
            ]
        )

    def run(self, question: str) -> Dict[str, Any]:
        if not self.available:
            return {
                "answer": (
                    "Supabase is not configured.\n\n"
                    "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) in your .env."
                ),
                "sources": [],
            }

        plan = self._plan(question)
        rows = self.client.select(table=plan.table, filters=plan.filters, limit=20, order="id.desc")

        if not rows:
            return {
                "answer": (
                    "I couldn't find relevant information on that topic. "
                    "You can ask about another subject or rephrase your question."
                ),
                "sources": [],
            }

        return {
            "answer": "Here are the results:\n\n" + json.dumps(rows, ensure_ascii=False, indent=2),
            "sources": [],
        }

    def _plan(self, question: str) -> SupabasePlan:
        if self.llm_client is None:
            return _heuristic_plan(question)

        try:
            response = self.llm_client.generate_chat(
                messages=[{"role": "user", "content": _PLAN_PROMPT.format(question=question)}],
                temperature=0.0,
                max_tokens=250,
            )
            data = _extract_json(response)
            if not isinstance(data, dict):
                return _heuristic_plan(question)

            table = (data.get("table") or "").strip()
            if table not in {"office_sections", "office_resources"}:
                table = "office_resources"

            filters = data.get("filters") or {}
            if not isinstance(filters, dict):
                filters = {}

            cleaned: Dict[str, str] = {}
            for k, v in filters.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    continue
                if not v.strip():
                    continue
                cleaned[k.strip()] = v.strip()

            return SupabasePlan(table=table, filters=cleaned)

        except Exception as exc:
            logger.exception("supabase_engine.plan_failed", extra={"error": str(exc)})
            return _heuristic_plan(question)

