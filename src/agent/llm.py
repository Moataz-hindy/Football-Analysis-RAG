"""OpenAI-compatible LLM adapter for the agent framework.

One class covers every free provider whose API speaks the OpenAI wire format:
Groq, Alibaba Model Studio (Qwen), OpenRouter, Google Gemini (compat endpoint),
Mistral, and a local Ollama. Switching provider is three environment variables --
see docs/llm_provider.md section 4. Cohere needs its own adapter (section 4.7).
"""

import os
import logging
import math
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from openai import OpenAI, APIConnectionError, APIStatusError, RateLimitError

from .interfaces import LLMInterface, ToolInterface

logger = logging.getLogger(__name__)

# ToolInterface carries no JSON schema, so tools without a `parameters`
# property fall back to an open object.
DEFAULT_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": True,
}


def _env_float(name: str, default: float, override: float | None = None) -> float:
    return override if override is not None else float(os.environ.get(name, default))


def _env_int(name: str, default: int, override: int | None = None) -> int:
    return override if override is not None else int(os.environ.get(name, default))


def to_tool_schema(tool: ToolInterface) -> dict[str, Any]:
    """Translate a ToolInterface into an OpenAI function-calling schema."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": getattr(tool, "parameters", DEFAULT_PARAMETERS),
        },
    }


class OpenAICompatibleLLM(LLMInterface):
    """Chat-completions LLM backed by any OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        api_key = api_key or os.environ.get("LLM_API_KEY", "").strip()
        base_url = base_url or os.environ.get("LLM_BASE_URL", "").strip()
        model = model or os.environ.get("LLM_MODEL", "").strip()
        if not api_key or not base_url or not model:
            raise RuntimeError(
                "Set LLM_API_KEY, LLM_BASE_URL and LLM_MODEL in .env "
                "(see docs/llm_provider.md section 4)."
            )

        self._model = model
        self._temperature = _env_float("LLM_TEMPERATURE", 0.2, temperature)
        self._max_tokens = _env_int("LLM_MAX_TOKENS", 1024, max_tokens)
        self._max_retries = _env_int("LLM_MAX_RETRIES", 3, max_retries)
        self._retry_max_wait = _env_float("LLM_RETRY_MAX_WAIT_SECONDS", 120.0)
        if self._max_retries < 0 or not math.isfinite(self._retry_max_wait) or self._retry_max_wait <= 0:
            raise ValueError("Invalid retry configuration")
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=_env_float("LLM_TIMEOUT_SECONDS", 60.0, timeout),
            max_retries=0,  # Retry here once, instead of stacking SDK and adapter retries.
        )
        self.last_response: Any = None       # usage / finish_reason, for debugging
        self._emitted: list[list[Any]] = []  # tool calls per round, for message repair
    @property
    def model(self) -> str:
        """Model identifier sent with every request (Requirement 4.8)."""
        return self._model

    @property
    def temperature(self) -> float:
        """Sampling temperature sent with every request (Requirement 4.8)."""
        return self._temperature

    @property
    def base_url(self) -> str:
        """Provider endpoint the client was configured with."""
        return str(self._client.base_url)

    @property
    def max_tokens(self) -> int:
        """Per-request output-token cap."""
        return self._max_tokens

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolInterface] | None = None,
    ) -> dict[str, Any]:
        if not any(message.get("role") == "tool" for message in messages):
            self._emitted = []   # new task: forget the previous run's tool calls

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._repair_tool_messages(messages),
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if tools:
            kwargs["tools"] = [to_tool_schema(tool) for tool in tools]
            kwargs["tool_choice"] = "auto"
        if self._model == "qwen/qwen3.6-27b":
             kwargs["reasoning_effort"] = "none"
   
        response = self._request_with_retry(kwargs)
        self.last_response = response

        message = response.choices[0].message
        calls = list(message.tool_calls or [])
        if calls:
            self._emitted.append(calls)

        # Agent._parse_result() accepts this dict shape. Returning it instead of the
        # raw SDK object stops a null content from becoming the string "None".
        return {"content": message.content or "", "tool_calls": calls}

    def _request_with_retry(self, kwargs):
        for attempt in range(self._max_retries + 1):
            try:
                return self._client.chat.completions.create(**kwargs)
            except (APIConnectionError, APIStatusError) as error:
                transient = (isinstance(error, (RateLimitError, APIConnectionError))
                             or error.status_code >= 500 or error.status_code == 408)
                if not transient or attempt == self._max_retries:
                    raise
                delay = self._retry_delay(error, attempt)
                if delay > self._retry_max_wait:
                    # A long quota reset must not silently turn into hours of waiting.
                    logger.warning("Provider delay exceeds retry budget; stopping for partial save.")
                    raise
                logger.warning("Temporary model failure (%s). Retrying request %d/%d in %.1fs.",
                               type(error).__name__, attempt + 1, self._max_retries, delay)
                time.sleep(delay)

    @staticmethod
    def _retry_delay(error, attempt):
        headers = getattr(getattr(error, "response", None), "headers", {})
        delay = None
        try:
            if headers.get("retry-after-ms"):
                delay = float(headers["retry-after-ms"]) / 1000
            elif headers.get("retry-after"):
                value = headers["retry-after"]
                try:
                    delay = float(value)
                except ValueError:
                    delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            delay = None
        if delay is None:
            match = re.search(r"try again in\s+([0-9]+(?:\.[0-9]+)?)s", str(error), re.I)
            if match:
                delay = float(match.group(1))
        if delay is not None and math.isfinite(delay) and delay >= 0:
            return delay + 1.0  # Small margin beyond the provider's reset time.
        return float(min(2 ** min(attempt + 1, 6), 60))

    def _repair_tool_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Make Agent.run()'s history valid for the OpenAI wire format.

        Agent.run() appends an assistant turn with no `tool_calls`, then tool turns
        with no `tool_call_id`. Strict endpoints reject that, so rebuild both from
        the calls this adapter emitted, matched in order.
        """
        if not self._emitted:
            return messages

        rounds = [list(calls) for calls in self._emitted]
        repaired: list[dict[str, Any]] = []
        index = 0
        while index < len(messages):
            message = messages[index]
            starts_round = (
                message.get("role") == "assistant"
                and index + 1 < len(messages)
                and messages[index + 1].get("role") == "tool"
                and rounds
            )
            if not starts_round:
                repaired.append(message)
                index += 1
                continue

            calls = rounds.pop(0)
            repaired.append({
                "role": "assistant",
                "content": message.get("content") or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in calls
                ],
            })
            index += 1
            for call in calls:
                if index < len(messages) and messages[index].get("role") == "tool":
                    repaired.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": messages[index].get("content", ""),
                    })
                    index += 1
        return repaired
