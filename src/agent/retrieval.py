from .interfaces import RetrievalInterface
from .types import RetrievedSource

# Assuming `search` handles its own connection and openrouter calls when None are provided.
# If not, we might need to handle connection lifecycle here.
try:
    from src.rag.search import search
except ImportError:
    # Fallback if run from a different directory level
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from src.rag.search import search


class RAGRetrieval(RetrievalInterface):
    """
    Integrates with the Week 1 pgvector knowledge retrieval system.
    """

    def __init__(self, k: int = 3):
        self.k = k

    def retrieve(self, query: str) -> list[RetrievedSource]:
        """
        Executes a vector similarity search against the Week 1 Postgres database
        and returns the results as a list of RetrievedSource objects.
        """
        try:
            # We use the search function from Week 1 which returns a list of dictionaries:
            # doc_id, chunk_index, title, url, text, similarity
            raw_results = search(query, k=self.k)
        except Exception as e:
            print(f"Warning: RAG retrieval failed: {e}")
            return []
        
        sources = []
        for result in raw_results:
            sources.append(
                RetrievedSource(
                    content=result.get("text", ""),
                    source=result.get("url") or result.get("title") or result.get("doc_id", "Unknown"),
                    score=result.get("similarity", 0.0),
                    metadata={
                        "doc_id": result.get("doc_id"),
                        "chunk_index": result.get("chunk_index"),
                        "title": result.get("title")
                    }
                )
            )
            
        return sources
