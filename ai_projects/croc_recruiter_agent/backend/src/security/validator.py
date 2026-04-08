import re


FORBIDDEN_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "replace"
]


def sanitize_sql(query: str) -> str:
    raw = (query or "").strip()
    if not raw:
        return ""

    raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    raw = raw.strip("`").strip()

    if ";" in raw:
        raw = raw.split(";", 1)[0].strip()

    raw = re.sub(r"\s+", " ", raw).strip()

    lowered = raw.lower()
    has_limit = " limit " in f" {lowered} "
    has_agg = any(x in lowered for x in ["count(", "sum(", "avg(", "min(", "max("]) or " group by " in lowered

    if lowered.startswith("select") and (not has_limit) and (not has_agg):
        raw = raw + " LIMIT 50"

    return raw.strip().rstrip(";")


def validate_sql(query: str) -> bool:
    if not query:
        raise ValueError("Empty query")

    # normalize
    normalized = query.strip().lower()

    if normalized.startswith("with"):
        raise ValueError("Common Table Expressions (CTEs) are not allowed")

    # allow only SELECT
    if not normalized.startswith("select"):
        raise ValueError("Only SELECT statements are allowed")

    # block multiple queries (;)
    if ";" in normalized and not normalized.endswith(";"):
        raise ValueError("Multiple queries are not allowed")
        
    # block forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized):
            raise ValueError(f"Forbidden keyword detected: {keyword}")

    # block SQL comments
    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise ValueError("SQL comments are not allowed")

    return True
