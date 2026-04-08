def test_sqlite_tables_exist():
    import sqlite3

    conn = sqlite3.connect("data/staffing.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {t[0] for t in cursor.fetchall()}

    conn.close()

    expected_tables = {"jobs", "candidates", "placements"}
  
    missing_tables = expected_tables - tables

    assert not missing_tables, f"Missing tables: {missing_tables}"