import logging

from .interfaces import RetrievalInterface
from .types import RetrievedSource

from src.rag.search import search

logger = logging.getLogger(__name__)


class RAGRetrieval(RetrievalInterface):
    """
    Integrates with the Week 1 pgvector knowledge retrieval system.
    """

    def __init__(self, k: int = 6):
        self.k = k

    def retrieve(self, query: str) -> list[RetrievedSource]:
        """
        Executes a vector similarity search against the Week 1 Postgres database
        and returns the results as a list of RetrievedSource objects.
        """
        try:
            raw_results = search(query, k=self.k)
        except Exception as error:
            # The knowledge base (Postgres/pgvector or the embedding provider)
            # is unreachable. This is an infrastructure outage, not an empty
            # search result: log it and degrade to no sources so callers
            # (agents, discussions, tools) can continue using their own
            # knowledge, persona background, and web_search instead of
            # aborting the whole run.
            logger.warning(
                "Knowledge retrieval unavailable (%s: %s); returning no sources.",
                type(error).__name__, error,
            )
            return []
        
        sources = []
        for result in raw_results:
            sources.append(
                RetrievedSource(
                    content=result.get("text", ""),
                    source=result.get("url") or result.get("title") or result.get("doc_id", "Unknown"),
                    score=float(result["similarity"]) if result.get("similarity") is not None else None,
                    metadata={
                        "doc_id": result.get("doc_id"),
                        "chunk_index": result.get("chunk_index"),
                        "title": result.get("title"),
                        "retrieval_mode": result.get("retrieval_mode", "vector")
                    }
                )
            )
            
        return sources
