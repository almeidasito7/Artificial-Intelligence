from src.llm.sql_generator import generate_sql
from src.security.validator import validate_sql
from src.security.rls import apply_rls
from src.security.permissions import get_user_permissions
from src.database.db import execute_query
from src.core.formatters.response_formatter import format_sql_response
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_sql_pipeline(question: str, user_id: str):
    try:
        # Generate SQL
        sql = generate_sql(question)
        logger.info(f"[SQL GENERATED]: {sql}")

        # Validate SQL
        validate_sql(sql)
        logger.info("[SQL VALIDATED]")

        # Get permissions
        permissions = get_user_permissions(user_id)
        logger.info(f"[PERMISSIONS]: {permissions}")

        # Apply RLS
        secure_sql = apply_rls(sql, permissions)
        logger.info(f"[RLS APPLIED]: {secure_sql}")

        # Execute query
        rows = execute_query(secure_sql)
        logger.info(f"[ROWS RETURNED]: {len(rows)}")

        # Format response
        response = format_sql_response(rows)
        logger.info(f"[FINAL ANSWER]: {response}")

        return {
            "question": question,
            "answer": response,
            "rows_count": len(rows)
        }

    except Exception as e:
        logger.error(f"[PIPELINE ERROR]: {str(e)}")
        raise RuntimeError("Failed to process query")