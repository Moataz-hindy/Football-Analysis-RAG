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

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search topic or question."}
            },
            "required": ["query"],
        }

    def run(self, arguments: dict[str, Any] | str | None = None, **kwargs: Any) -> Any:
        """Execute vector similarity search against the Week 1 database."""
        params: dict[str, Any] = {}
        if isinstance(arguments, dict):
            params.update(arguments)
        elif isinstance(arguments, str) and arguments.strip():
            params["query"] = arguments.strip()
        params.update(kwargs)

        query = params.get("query") or params.get("queries") or params.get("search_query") or params.get("q")
        if isinstance(query, list) and query:
            query = " ".join(item.strip() for item in query if isinstance(item, str) and item.strip())

        if not query or not isinstance(query, str) or not query.strip():
            raise ValueError("KnowledgeSearchTool requires a non-empty string 'query' argument.")

        # Perform pgvector search
        results = self._retrieval.retrieve(query=query)

        # Return formatted dictionaries with content, source URL, and similarity score
        return [
            {
                "content": item.content,
                "source": item.source,
                "score": item.score,
                "metadata": item.metadata,
            }
            for item in results
        ]
