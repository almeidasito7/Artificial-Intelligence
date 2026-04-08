import sqlite3
import os

from src.utils.logger import get_logger

logger = get_logger(__name__)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "staffing.db")


CREATE_CACHE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS semantic_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    question_hash TEXT NOT NULL UNIQUE,
    route TEXT NOT NULL,
    response TEXT NOT NULL,
    sources TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_database():
    logger.info("[DB INIT] Initializing database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # create cache table
    cursor.execute(CREATE_CACHE_TABLE_SQL)

    conn.commit()
    conn.close()

    logger.info("[DB INIT] semantic_cache table is ready")


if __name__ == "__main__":
    init_database()