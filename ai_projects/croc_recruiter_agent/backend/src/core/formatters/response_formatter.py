from typing import List, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


def format_sql_response(rows: List[Dict[str, Any]]) -> str:
    logger.info(f"[FORMATTER] Rows: {len(rows)}")

    # empty case
    if not rows:
        return (
            "I couldn't find relevant information on that topic. "
            "You can ask about another subject or rephrase your question."
        )

    # extract columns dynamically
    columns = list(rows[0].keys())

    # simple aggregation (COUNT, AVG, etc.)
    if len(rows) == 1 and len(columns) == 1:
        value = rows[0][columns[0]]
        return f"Based on your access scope, the result is {value}."

    # single record with multiple columns
    if len(rows) == 1:
        items = [f"{col}: {rows[0][col]}" for col in columns]
        return "Here is the result:\n" + "\n".join(items)

    # list of records (top N)
    MAX_RESULTS = 5

    top = rows[:MAX_RESULTS]

    if {"first_name", "last_name"} <= set(columns):
        items = []
        for r in top:
            name = f"{r.get('first_name','')} {r.get('last_name','')}".strip()
            division = r.get("division")
            region = r.get("region")
            years = r.get("years_experience")
            status = r.get("status")
            parts = [name]
            meta = []
            if division:
                meta.append(str(division))
            if region:
                meta.append(str(region))
            if years is not None:
                meta.append(f"{years} yrs")
            if status:
                meta.append(str(status))
            if meta:
                parts.append(" — " + " · ".join(meta))
            items.append("- " + "".join(parts))
        return "Here are the top employees:\n" + "\n".join(items)

    formatted_rows = []
    for r in top:
        values = [f"{k}: {v}" for k, v in r.items()]
        formatted_rows.append("- " + " | ".join(values))

    return "Here are the top results:\n" + "\n".join(formatted_rows)
