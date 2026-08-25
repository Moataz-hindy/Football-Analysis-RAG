

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"


def chunk_text(text, max_chars=1200, overlap=200):
    """Split text into overlapping fixed-size character chunks.

    Simple and dependency-free. Not sentence/token aware, but the overlap
    means a fact split across a chunk boundary is still likely to appear
    whole in the next chunk.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks