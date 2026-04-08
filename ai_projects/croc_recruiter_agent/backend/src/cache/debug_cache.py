import sqlite3


def main():
    conn = sqlite3.connect("data/cache.db")
    conn.row_factory = sqlite3.Row

    print("\nTables:")
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()

    for t in tables:
        print("-", t["name"])

    print("\nSchema:")
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='semantic_cache';"
    ).fetchone()

    print(schema["sql"] if schema else "Table not found")

    print("\nColumns:")
    columns = conn.execute("PRAGMA table_info(semantic_cache)").fetchall()

    for col in columns:
        print(dict(col))

    print("\nSample data:")
    rows = conn.execute("SELECT * FROM semantic_cache LIMIT 5").fetchall()

    for row in rows:
        print(dict(row))

    conn.close()


if __name__ == "__main__":
    main()