import sqlite3, glob, os

dbs = glob.glob('**/*.db', recursive=True)
print("DB files:", dbs)
for db in dbs:
    print(f"=== {db} ===")
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        print("Tables:", tables)
        for t in tables:
            tname = t[0]
            c.execute(f"SELECT count(*) FROM {tname}")
            print(f"  {tname} row count: {c.fetchone()[0]}")
    except Exception as e:
        print("Error:", e)
