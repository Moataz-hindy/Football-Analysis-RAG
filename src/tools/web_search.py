"""Web search tool backed by the Tavily API."""

import os
from typing import Any

import requests

from src.agent.interfaces import ToolInterface


class WebSearchTool(ToolInterface):
    """Search the internet for information relevant to an agent's task."""

    def __init__(
        self,
        api_key: str | None = None,
        max_results: int = 3,
    ) -> None:
        # Use the supplied key, or read it from the environment.
        self.api_key = (
            api_key or os.environ.get("TAVILY_API_KEY", "")
        ).strip()

        if not 1 <= max_results <= 20:
            raise ValueError("max_results must be between 1 and 20.")

        self.max_results = max_results
        self.endpoint = "https://api.tavily.com/search"

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the internet for up-to-date football news, transfers, "
            "match results, and recent events. "
            "Argument: 'query' (str) - search query text."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        """Describe the arguments the LLM can supply to this tool."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def run(self, arguments: dict[str, Any]) -> str:
        """Submit a search and return readable results."""
        query = arguments.get("query")

        if not isinstance(query, str) or not query.strip():
            raise ValueError(
                "web_search requires a non-empty string 'query' argument."
            )

        if self.api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                }
                payload = {
                    "query": query.strip(),
                    "search_depth": "basic",
                    "max_results": self.max_results,
                    "include_answer": True,
                }
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
                response.raise_for_status()
                data = response.json()

                formatted_results = []
                if data.get("answer"):
                    formatted_results.append(
                        f"Tavily-generated summary: {data['answer']}"
                    )

                for result in data.get("results", []):
                    formatted_results.append(
                        f"Title: {result.get('title', '')}\n"
                        f"URL: {result.get('url', '')}\n"
                        f"Content: {result.get('content', '')}"
                    )

                if formatted_results:
                    return "\n---\n".join(formatted_results)
            except Exception:
                # Fall back to DuckDuckGo search if Tavily fails or times out
                pass

        return self._duckduckgo_search(query.strip())

    def _duckduckgo_search(self, query: str) -> str:
        """Search the web using DuckDuckGo (no API key required)."""
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            results = list(DDGS().text(query, max_results=self.max_results))
            if not results:
                return "No web search results found."
            formatted = []
            for r in results:
                title = r.get("title", "")
                url = r.get("href") or r.get("url", "")
                snippet = r.get("body") or r.get("content", "")
                formatted.append(f"Title: {title}\nURL: {url}\nContent: {snippet}")
            return "\n---\n".join(formatted)
        except Exception as err:
            raise RuntimeError("Web search failed after provider fallback.") from err