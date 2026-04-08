from src.cache.cache_repository import CacheRepository


def main():
    cache = CacheRepository()

    print("\nTables:")
    tables = cache.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()

    for t in tables:
        print("-", t["name"])

    exists = cache.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_cache';"
    ).fetchone()

    if not exists:
        print("\nsemantic_cache table does not exist.\n")
        return

    print("\nSchema:")
    schema = cache.conn.execute(
        "SELECT sql FROM sqlite_master WHERE name='semantic_cache';"
    ).fetchone()

    print(schema["sql"])

    print("\nColumns:")
    columns = cache.conn.execute(
        "PRAGMA table_info(semantic_cache)"
    ).fetchall()

    for col in columns:
        print(dict(col))

    print("\nSample data:")
    rows = cache.conn.execute(
        "SELECT * FROM semantic_cache LIMIT 5"
    ).fetchall()

    for row in rows:
        print(dict(row))


if __name__ == "__main__":
    main()