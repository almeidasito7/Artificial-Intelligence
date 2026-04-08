from __future__ import annotations

from typing import Any, Dict, List, Sequence, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import psycopg  # type: ignore
    from psycopg.rows import dict_row  # type: ignore

    _HAS_PSYCOPG = True
except Exception:  # pragma: no cover
    psycopg = None  # type: ignore
    dict_row = None  # type: ignore
    _HAS_PSYCOPG = False

try:
    import psycopg2  # type: ignore
    from psycopg2.extras import RealDictCursor  # type: ignore

    _HAS_PSYCOPG2 = True
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore
    RealDictCursor = None  # type: ignore
    _HAS_PSYCOPG2 = False


class PostgresClient:
    def __init__(self, dsn: str, connect_timeout: int = 5) -> None:
        self.dsn = (dsn or "").strip()
        self.connect_timeout = connect_timeout

    @property
    def available(self) -> bool:
        return bool(self.dsn) and (_HAS_PSYCOPG or _HAS_PSYCOPG2)

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        if not self.dsn:
            raise RuntimeError("Postgres DSN is not configured (OFFICE_DB_DSN or DATABASE_URL).")

        if not (_HAS_PSYCOPG or _HAS_PSYCOPG2):
            raise RuntimeError("Postgres driver is not installed. Install 'psycopg[binary]' or 'psycopg2-binary'.")

        logger.info("postgres.query", extra={"sql_preview": (sql or "")[:120]})

        if _HAS_PSYCOPG:
            with psycopg.connect(self.dsn, connect_timeout=self.connect_timeout, row_factory=dict_row) as conn:  # type: ignore
                with conn.cursor() as cur:  # type: ignore
                    cur.execute(sql, params)  # type: ignore
                    rows = cur.fetchall()  # type: ignore
                    return list(rows)

        conn = psycopg2.connect(self.dsn, connect_timeout=self.connect_timeout, cursor_factory=RealDictCursor)  # type: ignore
        try:
            cur = conn.cursor()  # type: ignore
            try:
                cur.execute(sql, params)  # type: ignore
                rows = cur.fetchall()  # type: ignore
                return [dict(r) for r in rows]
            finally:
                cur.close()  # type: ignore
        finally:
            conn.close()  # type: ignore
