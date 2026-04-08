from src.database.db import generate_schema_prompt


def build_sql_prompt(user_question: str) -> str:
    schema = generate_schema_prompt()

    prompt = f"""
You are an expert SQL generator.

Your task is to convert natural language questions into SQL queries.

=====================
DATABASE SCHEMA
=====================
{schema}

=====================
RULES (STRICT)
=====================
- Only generate SELECT queries
- Do NOT use INSERT, UPDATE, DELETE, DROP, ALTER
- Do NOT generate multiple queries
- Do NOT use comments
- DO NOT include region or division filters (they are applied automatically)
- Always use existing tables and columns from the schema
- Keep queries simple and readable

=====================
SECURITY CONTEXT
=====================
- The query will be post-processed with Row-Level Security (RLS)
- RLS will enforce:
  region IN (...)
  division IN (...)

- DO NOT attempt to bypass security
- DO NOT remove filters
- DO NOT use subqueries to bypass restrictions

=====================
EXAMPLES
=====================

User: How many jobs are open?
SQL:
SELECT COUNT(*) FROM jobs WHERE status = 'open';

---

User: List candidates in IT division
SQL:
SELECT * FROM candidates;

---

User: Average bill rate for IT placements
SQL:
SELECT AVG(bill_rate) FROM placements WHERE division = 'IT';

=====================
USER QUESTION
=====================
{user_question}

=====================
OUTPUT FORMAT
=====================
Return ONLY the SQL query.
Do NOT include explanations.
Do NOT include markdown.
"""
    return prompt.strip()