from __future__ import annotations

from typing import Any

from src.llm.client import OpenAILLMClient
from src.llm.prompt_builder import build_sql_prompt


def generate_sql(question: str, llm_client: Any | None = None) -> str:
    client = llm_client or OpenAILLMClient(model="gpt-4o-mini")

    prompt = build_sql_prompt(question)

    raw_sql = client.generate_chat(
        messages=[
            {"role": "system", "content": "You generate SQL queries only. Return ONLY the SQL statement, no explanations, no markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=300,
    )

    return clean_sql_response(raw_sql)


def clean_sql_response(sql: str) -> str:
    if not sql:
        return ""

    sql = sql.replace("```sql", "").replace("```", "")
    sql = sql.strip()

    lower_sql = sql.lower()
    select_index = lower_sql.find("select")

    if select_index != -1:
        sql = sql[select_index:]

    return sql.strip().rstrip(";")
