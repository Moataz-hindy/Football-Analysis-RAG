#chunk every cleaned doc and embed the chunks.

import os
import sys
import json
import time

from dotenv import load_dotenv
from openai import OpenAI

from utils import chunk_text, CLEAN_DIR, EMBEDDINGS_DIR

load_dotenv()

SKIP_EXISTING = True   # set False to force re-embedding of every doc
BATCH_SIZE = 50         # chunks per embeddings API call (keeps requests small)
MAX_RETRIES = 3


def get_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL")
    if not api_key or not model:
        sys.exit(
            "Missing OPENAI_API_KEY or OPENROUTER_MODEL in your .env file. "
            "Copy .env.example to .env and fill in real values first."
        )
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    return client, model


def embed_batch(client, model, texts):
    """Call the embeddings API with retries (OpenRouter free-tier models
    can rate-limit or hiccup, so a bare single attempt is fragile)."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.embeddings.create(model=model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            last_error = e
            wait = 2 ** attempt
            print(f"    embedding call failed ({e}); retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Embedding failed after {MAX_RETRIES} attempts: {last_error}")


def process_doc(client, model, doc):
    chunks = chunk_text(doc["text"])
    embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        embeddings.extend(embed_batch(client, model, batch))
    return chunks, embeddings


def main():
    client, model = get_client()
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    clean_files = sorted(CLEAN_DIR.glob("*.json"))
    if not clean_files:
        sys.exit(f"No files found in {CLEAN_DIR}. Run clean.py first.")

    print(f"Found {len(clean_files)} cleaned docs.")

    expected_dim = None
    total_chunks = 0
    processed = 0
    skipped = 0

    for path in clean_files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        out_path = EMBEDDINGS_DIR / path.name

        if SKIP_EXISTING and out_path.exists():
            skipped += 1
            continue

        print(f"Processing {doc['id']} ({len(doc['text'])} chars)...")
        try:
            chunks, embeddings = process_doc(client, model, doc)
        except RuntimeError as e:
            print(f"  -> SKIPPED {doc['id']}: {e}")
            continue

        dim = len(embeddings[0]) if embeddings else 0
        if expected_dim is None:
            expected_dim = dim
            print(f"  -> Detected embedding dimension: {dim}")
        elif dim != expected_dim:
            sys.exit(
                f"Dimension mismatch on {doc['id']}: got {dim}, "
                f"expected {expected_dim}. Did the model change mid-run?"
            )

        out_doc = {
            "id": doc["id"],
            "url": doc["url"],
            "title": doc["title"],
            "chunks": [
                {"chunk_index": i, "text": c, "embedding": e}
                for i, (c, e) in enumerate(zip(chunks, embeddings))
            ],
        }
        out_path.write_text(json.dumps(out_doc), encoding="utf-8")

        total_chunks += len(chunks)
        processed += 1
        print(f"  -> {len(chunks)} chunks embedded and saved.")

    print(f"\nDone. Processed {processed} docs ({total_chunks} chunks), "
          f"skipped {skipped} already-embedded docs.")
    if expected_dim is not None:
        print(f"Embedding dimension used: {expected_dim}")
        print("Make sure sql/init_db.sql's 'vector(N)' column matches this "
              "number before running ingest.py.")


if __name__ == "__main__":
    main()