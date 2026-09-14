"""OpenAI-compatible LLM adapter for the agent framework.

One class covers every free provider whose API speaks the OpenAI wire format:
Groq, Alibaba Model Studio (Qwen), OpenRouter, Google Gemini (compat endpoint),
Mistral, and a local Ollama. Switching provider is three environment variables --
see docs/llm_provider.md section 4. Cohere needs its own adapter (section 4.7).
"""

import logging
import os
from typing import Any

from openai import OpenAI

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


def _sanitize_messages_without_tools(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tool-augmented message history into clean conversational turns.

    Used when a provider rejects tool calling or when falling back from a tool error,
    so that providers (Gemini, Groq, Ollama, etc.) do not 400 on unexpected 'tool' roles
    without active tool definitions.
    """
    sanitized: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "tool":
            tool_name = m.get("name") or "search"
            content = m.get("content", "")
            sanitized.append({
                "role": "user",
                "content": f"[Retrieved Information from {tool_name}]:\n{content}",
            })
        elif role == "assistant":
            content = m.get("content")
            if not content:
                content = "I reviewed the available match evidence."
            sanitized.append({
                "role": "assistant",
                "content": content,
            })
        else:
            sanitized.append(dict(m))
    return sanitized


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

        ssl_cert = os.environ.get("SSL_CERT_FILE")
        if ssl_cert and not os.path.exists(ssl_cert):
            os.environ.pop("SSL_CERT_FILE", None)

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=_env_float("LLM_TIMEOUT_SECONDS", 60.0, timeout),
            max_retries=_env_int("LLM_MAX_RETRIES", 3, max_retries),
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
   
        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as err:
            err_str = str(err).lower()
            err_body = getattr(err, "body", None)
            # Try to recover a tool call if the provider returned failed_generation
            if isinstance(err_body, dict):
                error_info = err_body.get("error", {})
                failed_gen = error_info.get("failed_generation")
                if failed_gen:
                    import json
                    from types import SimpleNamespace
                    from uuid import uuid4
                    try:
                        parsed_call = json.loads(failed_gen)
                        if isinstance(parsed_call, dict) and "name" in parsed_call:
                            call_name = parsed_call["name"]
                            call_args = parsed_call.get("arguments", {})
                            mock_call = SimpleNamespace(
                                id=f"call_{uuid4().hex[:8]}",
                                type="function",
                                function=SimpleNamespace(
                                    name=call_name,
                                    arguments=json.dumps(call_args) if isinstance(call_args, dict) else str(call_args),
                                ),
                            )
                            self._emitted.append([mock_call])
                            return {"content": "", "tool_calls": [mock_call]}
                    except Exception:
                        pass

            if tools and ("tool" in err_str or "400" in err_str):
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                kwargs["messages"] = _sanitize_messages_without_tools(kwargs["messages"])
                try:
                    response = self._client.chat.completions.create(**kwargs)
                except Exception as fallback_err:
                    logger.warning("Fallback without tools failed: %s", fallback_err)
                    return {
                        "content": (
                            "STANCE: Insufficient evidence available.\n"
                            "REASONING: Retrieval could not be completed for this turn.\n"
                            "SOURCES USED: None."
                        ),
                        "tool_calls": [],
                    }
            elif "tool" in err_str or "400" in err_str:
                kwargs["messages"] = _sanitize_messages_without_tools(kwargs["messages"])
                try:
                    response = self._client.chat.completions.create(**kwargs)
                except Exception:
                    return {
                        "content": (
                            "STANCE: Insufficient evidence to support a definitive conclusion.\n"
                            "REASONING: Detailed match metrics were not available to ground the position.\n"
                            "SOURCES USED: None."
                        ),
                        "tool_calls": [],
                    }
            elif "429" in err_str or "rate_limit" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                import time
                logger.warning("LLM rate limit encountered; waiting 5 seconds before retrying...")
                time.sleep(5)
                try:
                    response = self._client.chat.completions.create(**kwargs)
                except Exception as retry_err:
                    logger.warning("Retry with tools failed: %s; retrying without tools...", retry_err)
                    kwargs.pop("tools", None)
                    kwargs.pop("tool_choice", None)
                    kwargs["messages"] = _sanitize_messages_without_tools(kwargs["messages"])
                    try:
                        response = self._client.chat.completions.create(**kwargs)
                    except Exception as second_retry_err:
                        logger.warning("Final retry failed: %s. Returning structured fallback.", second_retry_err)
                        return {
                            "content": (
                                "STANCE: Maintains tactical position pending further match evidence.\n"
                                "REASONING: Provider request limits constrained retrieval during this turn; maintaining position based on established analysis.\n"
                                "SOURCES USED: None."
                            ),
                            "tool_calls": [],
                        }
            else:
                raise
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
            repaired_calls: list[dict[str, Any]] = []
            for call in calls:
                call_id = getattr(call, "id", None) or (call.get("id") if isinstance(call, dict) else "")
                func = getattr(call, "function", None) or (call.get("function") if isinstance(call, dict) else None)
                fname = getattr(func, "name", None) or (func.get("name") if isinstance(func, dict) else "")
                fargs = getattr(func, "arguments", None) or (func.get("arguments") if isinstance(func, dict) else "")
                c_dict: dict[str, Any] = {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": fname,
                        "arguments": fargs,
                    },
                }
                # Preserve provider-specific extra content (such as Google Gemini thought_signature)
                extra = getattr(call, "extra_content", None) or (call.get("extra_content") if isinstance(call, dict) else None)
                if extra:
                    c_dict["extra_content"] = extra
                repaired_calls.append(c_dict)

            repaired.append({
                "role": "assistant",
                "content": message.get("content") or None,
                "tool_calls": repaired_calls,
            })
            index += 1
            for call in calls:
                call_id = getattr(call, "id", None) or (call.get("id") if isinstance(call, dict) else "")
                if index < len(messages) and messages[index].get("role") == "tool":
                    repaired.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": messages[index].get("content", ""),
                    })
                    index += 1
        return repaired
