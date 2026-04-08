from typing import List, Dict

import re

try:
    import sqlglot  # type: ignore
    from sqlglot import exp  # type: ignore
    _HAS_SQLGLOT = True
except Exception:  # pragma: no cover
    sqlglot = None  # type: ignore
    exp = None  # type: ignore
    _HAS_SQLGLOT = False

ALLOWED_TABLES = ("jobs", "candidates", "placements")


def _format_in_list(values: List[str]) -> str:
    safe = [v.replace("'", "''") for v in values]
    return ", ".join(["'" + v + "'" for v in safe])


def _wrap_table(sql: str, table_name: str, regions: List[str], divisions: List[str]) -> str:
    filters = []
    if regions:
        filters.append(f"region IN ({_format_in_list(regions)})")
    if divisions:
        filters.append(f"division IN ({_format_in_list(divisions)})")
    if not filters:
        return sql

    where_clause = " AND ".join(filters)

    pattern = re.compile(
        rf"(?P<prefix>\b(from|join)\s+)(?P<table>{re.escape(table_name)})\b(\s+(?:as\s+)?(?P<alias>[a-zA-Z_][a-zA-Z0-9_]*))?",
        flags=re.IGNORECASE,
    )

    def repl(match: re.Match) -> str:
        alias = match.group("alias") or match.group("table")
        prefix = match.group("prefix")
        return f"{prefix}(SELECT * FROM {table_name} WHERE {where_clause}) {alias}"

    return pattern.sub(repl, sql)


def _fallback_rls_rewrite(sql: str, regions: List[str], divisions: List[str]) -> str:
    normalized = (sql or "").strip().rstrip(";")
    if not normalized:
        raise ValueError("Empty SQL")

    rewritten = normalized
    for t in ALLOWED_TABLES:
        rewritten = _wrap_table(rewritten, t, regions, divisions)

    if rewritten == normalized:
        raise ValueError("Unable to apply RLS to this query")

    return rewritten.strip().rstrip(";")


def apply_rls(sql: str, permissions: Dict) -> str:
    regions = permissions.get("regions", [])
    divisions = permissions.get("divisions", [])

    if not regions and not divisions:
        raise ValueError("User has no permissions")

    if not _HAS_SQLGLOT:
        return _fallback_rls_rewrite(sql, regions, divisions)

    normalized_sql = (sql or "").strip().rstrip(";")
    if not normalized_sql:
        raise ValueError("Empty SQL")

    try:
        parsed = sqlglot.parse_one(normalized_sql, read="sqlite")  # type: ignore
    except Exception as exc:
        return _fallback_rls_rewrite(normalized_sql, regions, divisions)

    try:
        select_expr = parsed
        if isinstance(parsed, exp.Subquery):  # type: ignore
            select_expr = parsed.this

        if not isinstance(select_expr, exp.Select):  # type: ignore
            inner_select = parsed.find(exp.Select)  # type: ignore
            if inner_select is None:
                return _fallback_rls_rewrite(normalized_sql, regions, divisions)
            select_expr = inner_select

        conditions = []  # type: ignore
        for table in parsed.find_all(exp.Table):  # type: ignore
            table_name = (table.name or "").lower()
            if table_name not in ALLOWED_TABLES:
                continue

            alias = table.args.get("alias")
            if alias is not None and getattr(alias, "this", None) is not None:
                table_alias = alias.this.name
            else:
                table_alias = table_name

            if regions:
                conditions.append(exp.In(this=exp.column("region", table=table_alias), expressions=[exp.Literal.string(v) for v in regions]))  # type: ignore
            if divisions:
                conditions.append(exp.In(this=exp.column("division", table=table_alias), expressions=[exp.Literal.string(v) for v in divisions]))  # type: ignore

        if not conditions:
            return _fallback_rls_rewrite(normalized_sql, regions, divisions)

        combined = conditions[0]
        for cond in conditions[1:]:
            combined = exp.and_(combined, cond)  # type: ignore

        existing_where = select_expr.args.get("where")
        if existing_where is None:
            select_expr.set("where", exp.Where(this=combined))  # type: ignore
        else:
            select_expr.set("where", exp.Where(this=exp.and_(existing_where.this, combined)))  # type: ignore

        return parsed.sql(dialect="sqlite").strip().rstrip(";")  # type: ignore
    except Exception:
        return _fallback_rls_rewrite(normalized_sql, regions, divisions)
