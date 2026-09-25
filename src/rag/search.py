""" retrieval

Takes a natural-language question, embeds it with the same model used for
the chunks, and finds the closest chunks in Postgres using pgvector's
cosine distance operator (<=>) — the same operator the ivfflat index in
init_db.sql was built with (vector_cosine_ops), so the index actually
gets used.

"""

import os
import sys
from pathlib import Path

import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, APIStatusError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

class RetrievalError(RuntimeError):
    """Knowledge infrastructure failed; this is not an empty search result."""


SQL = """
    SELECT doc_id, chunk_index, title, url, text,
           1 - (embedding <=> %(vec)s::vector) AS similarity
    FROM football_chunks
    ORDER BY embedding <=> %(vec)s::vector
    LIMIT %(k)s
"""


def get_client():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENROUTER_MODEL", "").strip()
    if not api_key or not model or "your key here" in api_key.lower():
        raise RetrievalError("Missing embedding API key or model in the project .env.")
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1"), model


def get_connection():
    try:
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            conn = psycopg2.connect(db_url, connect_timeout=10)
        else:
            conn = psycopg2.connect(
                host=os.environ.get("DB_HOST", "localhost"),
                port=os.environ.get("DB_PORT", "5432"),
                dbname=os.environ.get("DB_NAME", "football_intelligence"),
                user=os.environ.get("DB_USER", "postgres"),
                password=os.environ.get("DB_PASSWORD"),
                connect_timeout=10,
            )
    except psycopg2.OperationalError as e:
        raise RetrievalError("Could not connect to Postgres. Check database availability and DB settings.") from e
    try:
        register_vector(conn)
    except Exception as error:
        conn.close()
        raise RetrievalError("Could not initialize pgvector on the database connection.") from error
    return conn


def embed_query(client, model, text):
    response = client.embeddings.create(model=model, input=[text])
    return response.data[0].embedding


def _keyword_search(conn, question, k):
    """Rank title/text matches when the embedding service is unavailable."""
    terms = list(dict.fromkeys(
        word for word in question.replace("?", "").replace("'", "").replace('"', '').split()
        if len(word) > 3
    ))
    if not terms:
        raise RetrievalError("Embedding unavailable and no usable keyword search terms.")
    where_clause = " OR ".join(["text ILIKE %s OR title ILIKE %s" for _ in terms])
    title_score = " + ".join(["(CASE WHEN title ILIKE %s THEN 50 ELSE 0 END)" for _ in terms])
    text_score = " + ".join(["(CASE WHEN text ILIKE %s THEN 10 ELSE 0 END)" for _ in terms])
    sql = f"""
        SELECT doc_id, chunk_index, title, url, text, NULL AS similarity
        FROM football_chunks
        WHERE {where_clause}
        ORDER BY ({title_score} + {text_score}) DESC, doc_id ASC, chunk_index ASC
        LIMIT %s
    """
    params = [f"%{term}%" for term in terms for _ in range(2)]
    params += [f"%{term}%" for term in terms] * 2
    params.append(k)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def search(question, k=5, client=None, model=None, conn=None):
    """Search vectors, falling back to labeled keywords on provider outages.

    Database failures and configuration/authentication errors remain failures.
    Keyword ranks do not have a cosine similarity score.
    """
    own_conn = conn is None
    if client is None or model is None:
        client, model = get_client()
    if conn is None:
        conn = get_connection()
    mode = "vector"
    try:
        try:
            query_vec = embed_query(client, model, question)
        except (APIConnectionError, APIStatusError) as error:
            if isinstance(error, APIStatusError) and error.status_code not in (408, 429) and error.status_code < 500:
                raise
            rows = _keyword_search(conn, question, k)
            mode = "keyword"
        else:
            with conn.cursor() as cur:
                cur.execute(SQL, {"vec": query_vec, "k": k})
                rows = cur.fetchall()
    except Exception as error:
        raise RetrievalError("Knowledge search failed while embedding the query or reading Postgres.") from error
    finally:
        if own_conn:
            conn.close()
    return [
        {
            "doc_id": r[0], "chunk_index": r[1], "title": r[2],
            "url": r[3], "text": r[4],
            "similarity": float(r[5]) if r[5] is not None else None,
            "retrieval_mode": mode,
        }
        for r in rows
    ]


def print_results(question, results):
    print(f"\nQuestion: {question}")
    print("-" * 60)
    if not results:
        print("No passages found. The database may be empty or contain no matching rows.")
    for i, r in enumerate(results, 1):
        preview = r["text"][:200].replace("\n", " ")
        score = f"similarity={r['similarity']:.3f}" if r["similarity"] is not None else "keyword match (no vector score)"
        print(f"{i}. [{r['doc_id']} chunk {r['chunk_index']}] {score}")
        print(f"   {r['title']}")
        print(f"   {preview}...")
        print()


def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        results = search(question, k=5)
        print_results(question, results)
        return

    client, model = get_client()
    conn = get_connection()
    print("Football RAG search. Type a question (or 'quit' to exit).")
    try:
        while True:
            question = input("\n> ").strip()
            if question.lower() in ("quit", "exit", ""):
                break
            results = search(question, k=5, client=client, model=model, conn=conn)
            print_results(question, results)
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except RetrievalError as error:
        print(f"Search failed: {error}", file=sys.stderr)
        raise SystemExit(1)