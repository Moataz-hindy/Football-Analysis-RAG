"""Knowledge Search Tool Implementation.

Allows the AI Agent to perform semantic vector searches over the pgvector database.
"""

from typing import Any
from src.agent.interfaces import ToolInterface
from src.agent.retrieval import RAGRetrieval


class KnowledgeSearchTool(ToolInterface):
    """Exposes Week 1 pgvector RAG search capability as an Agent Tool."""

    def __init__(self, retrieval: RAGRetrieval | None = None, default_k: int = 3):
        # Store provided RAGRetrieval wrapper or create a default instance
        self._retrieval = retrieval or RAGRetrieval(k=default_k)

    @property
    def name(self) -> str:
        """Tool name passed to the LLM."""
        return "knowledge_search"

    @property
    def description(self) -> str:
        """Instruction for LLM on when and how to invoke this tool."""
        return (
            "Search the football intelligence knowledge base for relevant articles, match reports, "
            "and tactical stats. Argument: 'query' (str) - the search query topic."
        )

    def run(self, arguments: dict[str, Any]) -> Any:
        """Execute vector similarity search against the Week 1 database."""
        query = arguments.get("query")
        if not query or not isinstance(query, str):
            raise ValueError("KnowledgeSearchTool requires a non-empty string 'query' argument.")

        # Perform pgvector search
        results = self._retrieval.retrieve(query=query)

        # Return formatted dictionaries with content, source URL, and similarity score
        return [
            {
                "content": item.content,
                "source": item.source,
                "score": item.score,
            }
            for item in results
        ]
