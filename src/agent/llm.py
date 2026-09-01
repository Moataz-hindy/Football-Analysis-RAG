"""OpenAI-compatible LLM adapter for the agent framework.

One class covers every free provider whose API speaks the OpenAI wire format:
Groq, Alibaba Model Studio (Qwen), OpenRouter, Google Gemini (compat endpoint),
Mistral, and a local Ollama. Switching provider is three environment variables --
see docs/llm_provider.md section 4. Cohere needs its own adapter (section 4.7).
"""

import os
from typing import Any

from openai import OpenAI

from .interfaces import LLMInterface, ToolInterface

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
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=_env_float("LLM_TIMEOUT_SECONDS", 60.0, timeout),
            max_retries=_env_int("LLM_MAX_RETRIES", 3, max_retries),
        )
        self.last_response: Any = None       # usage / finish_reason, for debugging
        self._emitted: list[list[Any]] = []  # tool calls per round, for message repair

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

        response = self._client.chat.completions.create(**kwargs)
        self.last_response = response

        message = response.choices[0].message
        calls = list(message.tool_calls or [])
        if calls:
            self._emitted.append(calls)

        # Agent._parse_result() accepts this dict shape. Returning it instead of the
        # raw SDK object stops a null content from becoming the string "None".
        return {"content": message.content or "", "tool_calls": calls}

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
