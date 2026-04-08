from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import numpy as np

from src.rag.embeddings import get_embedding_model

DB_PATH = "data/cache.db"


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)

    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0

    return float(np.dot(a, b) / denom)


class CacheRepository:

    def __init__(self, db_path: str = DB_PATH, ttl_seconds: int = 3600):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self.embedding_model = None
        self.ttl_seconds = ttl_seconds

        self._create_table()

    # TABLE SETUP
    def _create_table(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS semantic_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            query_embedding TEXT,
            response TEXT,
            sources TEXT,
            scope_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        self.conn.commit()

    def reset_table(self):
        print("Dropping table...")
        self.conn.execute("DROP TABLE IF EXISTS semantic_cache;")
        self.conn.commit()

        print("Recreating table...")
        self._create_table()

        print("Done.")

    # EMBEDDING
    def _embed_query(self, query: str) -> List[float]:
        if self.embedding_model is None:
            self.embedding_model = get_embedding_model()

        emb = self.embedding_model.encode(
            [query],
            normalize_embeddings=True
        )[0]

        return emb.tolist()

    # CACHE GET
    def get_cache(
        self,
        query: str,
        scope_hash: str,
        threshold: float = 0.92,
    ) -> Optional[Dict[str, Any]]:

        query_embedding = self._embed_query(query)

        rows = self.conn.execute(
            "SELECT * FROM semantic_cache WHERE scope_hash = ?",
            (scope_hash,)
        ).fetchall()

        best_match = None
        best_score = 0

        for row in rows:
            stored_embedding = json.loads(row["query_embedding"])

            score = cosine_similarity(query_embedding, stored_embedding)

            if score < threshold:
                continue

            created_at = datetime.fromisoformat(row["created_at"])

            if created_at.tzinfo is not None:
                created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)

            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            age = (now_utc - created_at).total_seconds()

            if age > self.ttl_seconds:
                continue

            if score > best_score:
                best_score = score
                best_match = row

        if best_match:
            return {
                "response": best_match["response"],
                "sources": json.loads(best_match["sources"]),
            }

        return None

    # CACHE SAVE
    def save_cache(
        self,
        query: str,
        response: str,
        sources: List[str],
        scope_hash: str,
    ) -> None:

        query_embedding = self._embed_query(query)

        self.conn.execute("""
            INSERT INTO semantic_cache (
                query,
                query_embedding,
                response,
                sources,
                scope_hash
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            query,
            json.dumps(query_embedding),
            response,
            json.dumps(sources),
            scope_hash
        ))

        self.conn.commit()
