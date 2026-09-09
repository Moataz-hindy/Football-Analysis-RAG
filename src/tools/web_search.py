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

        if not self.api_key:
            return "Error: TAVILY_API_KEY is not configured."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "query": query.strip(),
            "search_depth": "basic",
            "max_results": self.max_results,
            "include_answer": True,
        }

        # This entire block belongs inside run().
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=20,
            )

            # Raise an exception for unsuccessful HTTP responses.
            response.raise_for_status()

            # Convert the JSON response into Python data.
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

            if not formatted_results:
                return "No web search results found."

            return "\n---\n".join(formatted_results)

        except requests.exceptions.RequestException as error:
            return f"Error executing web search: {error}"

        except ValueError:
            return "Error: Tavily returned an invalid JSON response."