DB_PATH = "cache.db"

class CacheRepository:
    def __init__(self, db_path: str = DB_PATH, ttl_seconds: int = 3600):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

        self.embedding_model = get_embedding_model()
        self.ttl_seconds = ttl_seconds

        self._create_table()