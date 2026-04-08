from typing import List, Dict, Any
import sqlite3
from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Connection
def get_connection():
    settings = get_settings()

    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row 

    return conn


# Core query executor (read only)
def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        logger.info(f"[DB] Executing query")

        cursor.execute(query, params)

        rows = cursor.fetchall()

        # always return dict
        result = [dict(row) for row in rows]

        return result

    except sqlite3.Error as e:
        logger.error(f"[DB ERROR]: {str(e)}")
        raise RuntimeError("Database query failed")

    finally:
        cursor.close()
        conn.close()


# SAFE TABLE VALIDATION
def _validate_identifier(name: str):
    if not name.isidentifier():
        raise ValueError("Invalid identifier")


# Database Introspection

def get_tables() -> List[str]:
    result = execute_query(
        "SELECT name FROM sqlite_master WHERE type='table';"
    )
    return [table["name"] for table in result]


def get_table_schema(table_name: str) -> List[Dict]:
    _validate_identifier(table_name)

    return execute_query(
        f"PRAGMA table_info({table_name});"
    )


def get_table_preview(table_name: str, limit: int = 5) -> List[Dict]:
    _validate_identifier(table_name)

    return execute_query(
        f"SELECT * FROM {table_name} LIMIT {limit};"
    )


def inspect_database() -> Dict[str, Any]:
    tables = get_tables()

    result = {}

    for table in tables:
        result[table] = {
            "schema": get_table_schema(table),
            "preview": get_table_preview(table)
        }

    return result


# Schema Prompt Builder (for LLM)

def generate_schema_prompt() -> str:
    tables = get_tables()

    schema_lines = []

    for table in tables:
        columns = get_table_schema(table)

        column_defs = []
        for col in columns:
            col_name = col["name"]
            col_type = col["type"]
            column_defs.append(f"{col_name} ({col_type})")

        columns_str = ", ".join(column_defs)
        schema_lines.append(f"Table {table}: {columns_str}")

    return "\n".join(schema_lines)