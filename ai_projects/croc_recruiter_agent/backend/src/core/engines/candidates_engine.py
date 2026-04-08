from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.database.db import execute_query
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _extract_min_years(question: str) -> Optional[int]:
    m = re.search(r"(\d{1,2})\s*\+?\s*(years?|yrs?|anos?)\b", question, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _extract_limit(question: str) -> Optional[int]:
    q = (question or "").lower()
    m = re.search(r"\b(?:top|first|show|list)\s+(\d{1,2})\b", q)
    if not m:
        m = re.search(r"\b(\d{1,2})\b\s+(?:candidates|people|employees|candidatos)\b", q)
    if not m:
        return None
    try:
        n = int(m.group(1))
        return max(1, min(n, 25))
    except Exception:
        return None


def _extract_skills(question: str) -> List[str]:
    q = (question or "").strip()
    if not q:
        return []

    normalized = q.lower()
    tail = ""
    if " in " in normalized:
        tail = q.rsplit(" in ", 1)[-1]
    elif " with " in normalized:
        tail = q.rsplit(" with ", 1)[-1]
    else:
        return []

    tail = re.sub(r"\b(years?|yrs?|anos?)\b", " ", tail, flags=re.IGNORECASE)
    tail = re.sub(r"\b(experience|experiência)\b", " ", tail, flags=re.IGNORECASE)
    tail = re.sub(r"\b(of|de|do|da|in|with)\b", " ", tail, flags=re.IGNORECASE)
    tail = re.sub(r"[^a-zA-Z0-9À-ÿ,\-/ ]+", " ", tail)

    parts = re.split(r"\s*(?:,|/| and | e )\s*", tail, flags=re.IGNORECASE)
    skills = []
    for p in parts:
        s = p.strip()
        if len(s) < 2:
            continue
        if re.fullmatch(r"\d+", s):
            continue
        if s.lower() in {"a", "an", "the", "um", "uma", "de", "do", "da"}:
            continue
        skills.append(s)

    seen = set()
    uniq = []
    for s in skills:
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(s)
    return uniq[:5]


def _in_clause(values: List[str]) -> Tuple[str, List[Any]]:
    if not values:
        return "(NULL)", []
    placeholders = ", ".join(["?"] * len(values))
    return f"({placeholders})", list(values)


class CandidatesEngine:
    def run(self, question: str, user_id: str, permissions: Dict[str, Any]) -> Dict[str, Any]:
        regions = permissions.get("regions", [])
        divisions = permissions.get("divisions", [])
        if not regions and not divisions:
            return {"answer": "You don't have access to any region or division.", "sources": []}

        min_years = _extract_min_years(question) or 0
        skills = _extract_skills(question)
        limit = _extract_limit(question) or 10

        is_list_request = bool(re.search(r"\b(list|show)\b.*\b(candidates|candidatos|employees|people)\b", question, flags=re.IGNORECASE))
        if is_list_request:
            min_years = 0
            skills = []

        where_parts = ["1=1"]
        params: List[Any] = []

        if min_years > 0:
            where_parts.append("years_experience >= ?")
            params.append(min_years)

        for s in skills:
            where_parts.append("LOWER(skills) LIKE ?")
            params.append(f"%{s.lower()}%")

        if regions:
            clause, clause_params = _in_clause(regions)
            where_parts.append(f"region IN {clause}")
            params.extend(clause_params)

        if divisions:
            clause, clause_params = _in_clause(divisions)
            where_parts.append(f"division IN {clause}")
            params.extend(clause_params)

        where_sql = " AND ".join(where_parts)

        sql = f"""
        SELECT
            candidate_id,
            first_name,
            last_name,
            division,
            region,
            years_experience,
            skills,
            status
        FROM candidates
        WHERE {where_sql}
        ORDER BY years_experience DESC, last_activity_date DESC
        LIMIT {limit}
        """.strip()

        logger.info(
            "candidates_engine.query",
            extra={
                "user_id": user_id,
                "min_years": min_years,
                "skills_count": len(skills),
            },
        )

        rows = execute_query(sql, tuple(params))

        compact = [
            {
                "candidate_id": r.get("candidate_id"),
                "name": f"{r.get('first_name','')} {r.get('last_name','')}".strip(),
                "division": r.get("division"),
                "region": r.get("region"),
                "years_experience": r.get("years_experience"),
                "skills": r.get("skills"),
                "status": r.get("status"),
            }
            for r in rows
        ]

        if not compact:
            criteria = []
            if min_years:
                criteria.append(f"{min_years}+ years")
            if skills:
                criteria.append(", ".join(skills))
            suffix = f" ({' | '.join(criteria)})" if criteria else ""
            return {"answer": f"I couldn't find candidates matching your criteria{suffix}.", "sources": []}

        lines = []
        for c in compact:
            name = c.get("name") or "Unknown"
            yrs = c.get("years_experience")
            region = c.get("region")
            division = c.get("division")
            status = c.get("status")

            meta = []
            if yrs is not None:
                meta.append(f"{yrs} yrs")
            if division:
                meta.append(str(division))
            if region:
                meta.append(str(region))
            if status:
                meta.append(str(status))

            if meta:
                lines.append(f"- **{name}** — " + " · ".join(meta))
            else:
                lines.append(f"- **{name}**")

        answer = "Here are candidates I found:\n" + "\n".join(lines)

        return {"answer": answer, "sources": []}
