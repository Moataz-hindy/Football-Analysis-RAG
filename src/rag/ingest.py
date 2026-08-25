#load the embedded chunks from data/embeddings/ into Postgres.


import os
import sys
import json

import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

from utils import EMBEDDINGS_DIR

load_dotenv()


def get_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ.get("DB_NAME", "football_intelligence"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD"),
        )
    except psycopg2.OperationalError as e:
        sys.exit(
            f"Could not connect to Postgres: {e}\n"
            "Is the container running? Try: docker-compose up -d"
        )
    register_vector(conn)
    return conn


INSERT_SQL = """
    INSERT INTO football_chunks (doc_id, chunk_index, url, title, text, embedding)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (doc_id, chunk_index) DO UPDATE
        SET text = EXCLUDED.text,
            embedding = EXCLUDED.embedding,
            url = EXCLUDED.url,
            title = EXCLUDED.title
"""


def main():
    files = sorted(EMBEDDINGS_DIR.glob("*.json"))
    if not files:
        sys.exit(f"No files found in {EMBEDDINGS_DIR}. Run process_all.py first.")

    conn = get_connection()
    cur = conn.cursor()

    # Check the table's vector column size matches what we're about to
    # insert, so a dimension mismatch fails with a clear message instead
    # of a cryptic Postgres error mid-batch.
    cur.execute("""
        SELECT atttypmod FROM pg_attribute
        WHERE attrelid = 'football_chunks'::regclass AND attname = 'embedding'
    """)
    row = cur.fetchone()
    table_dim = row[0] if row and row[0] > 0 else None

    total_rows = 0
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        chunks = doc["chunks"]
        if not chunks:
            continue

        dim = len(chunks[0]["embedding"])
        if table_dim and dim != table_dim:
            sys.exit(
                f"Dimension mismatch: embeddings are {dim}-d but the "
                f"football_chunks table expects {table_dim}-d. "
                "Update the 'vector(N)' column in sql/init_db.sql to match, "
                "recreate the table, then re-run this script."
            )

        rows = [
            (doc["id"], c["chunk_index"], doc["url"], doc["title"], c["text"], c["embedding"])
            for c in chunks
        ]
        cur.executemany(INSERT_SQL, rows)
        conn.commit()
        total_rows += len(rows)
        print(f"Inserted {len(rows)} chunks from {doc['id']}.")

    cur.execute("SELECT COUNT(*) FROM football_chunks")
    db_total = cur.fetchone()[0]

    cur.close()
    conn.close()

    print(f"\nDone. Inserted/updated {total_rows} chunk rows from {len(files)} docs.")
    print(f"football_chunks table now has {db_total} rows total.")


if __name__ == "__main__":
    main()