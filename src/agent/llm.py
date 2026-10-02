"""OpenAI-compatible LLM adapter for the agent framework.

One class covers every free provider whose API speaks the OpenAI wire format:
Groq, Alibaba Model Studio (Qwen), OpenRouter, Google Gemini (compat endpoint),
Mistral, and a local Ollama. Switching provider is three environment variables --
see docs/llm_provider.md section 4. Cohere needs its own adapter (section 4.7).
"""

import logging
import os
import math
import re
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from openai import OpenAI, APIConnectionError, APIStatusError, RateLimitError

from .interfaces import LLMInterface, ToolInterface

logger = logging.getLogger(__name__)

# Legacy tools without a `parameters` property fall back to an open object.
DEFAULT_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": True,
}


def _env_float(name: str, default: float, override: float | None = None) -> float:
    return override if override is not None else float(os.environ.get(name, default))


def _env_int(name: str, default: int, override: int | None = None) -> int:
    return override if override is not None else int(os.environ.get(name, default))


def _env_pace_waits() -> tuple[float, ...]:
    # Extra retry cycles are opt-in; normal callers use one request retry ladder.
    raw = os.environ.get("LLM_PACE_WAITS", "")
    return tuple(float(x) for x in raw.split(",") if x.strip())


class _RatePacer:
    """Process-wide sliding-window request pacing.

    Free provider tiers enforce per-minute and per-hour request caps; a
    discussion run with tool rounds can exhaust an hourly bucket mid-run and
    receive retry-after values longer than any sane wait. Spacing requests
    keeps the run under the caps instead of stalling on quota resets.
    """

    def __init__(self) -> None:
        self._minute_times: list[float] = []
        self._hour_times: list[float] = []

    def wait_for_slot(self) -> None:
        max_per_minute = _env_int("LLM_PACER_MAX_PER_MINUTE", 0)
        max_per_hour = _env_int("LLM_PACER_MAX_PER_HOUR", 0)
        if max_per_minute <= 0 and max_per_hour <= 0:
            return
        while True:
            now = time.monotonic()
            self._minute_times = [t for t in self._minute_times if now - t < 60.0]
            self._hour_times = [t for t in self._hour_times if now - t < 3600.0]
            waits = []
            if max_per_minute > 0 and len(self._minute_times) >= max_per_minute:
                waits.append(60.0 - (now - self._minute_times[0]) + 0.5)
            if max_per_hour > 0 and len(self._hour_times) >= max_per_hour:
                waits.append(3600.0 - (now - self._hour_times[0]) + 0.5)
            if not waits:
                break
            time.sleep(min(max(waits), 120.0))
            now = time.monotonic()
        stamp = time.monotonic()
        self._minute_times.append(stamp)
        self._hour_times.append(stamp)


_PACER = _RatePacer()


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
        pace_waits: tuple[float, ...] | None = None,
        use_pacer: bool = True,
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
        self._max_retries = _env_int("LLM_MAX_RETRIES", 8, max_retries)
        self._retry_max_wait = _env_float("LLM_RETRY_MAX_WAIT_SECONDS", 300.0)
        self._retry_wait_budget = _env_float("LLM_RETRY_WAIT_BUDGET_SECONDS", 600.0)
        self._retry_delays = tuple(float(value.strip()) for value in os.environ.get(
            "LLM_RETRY_DELAYS_SECONDS", "5,10,20,40,60,90,120,180"
        ).split(",") if value.strip())
        # waits[i] is slept after pace attempt i; attempts = len(waits) + 1.
        # Explicit retry limits also disable this outer ladder unless requested.
        # An empty tuple leaves retries solely to _request_with_retry.
        self._pace_waits = (tuple(pace_waits) if pace_waits is not None else
                            () if max_retries is not None else _env_pace_waits())
        self._use_pacer = use_pacer
        if (self._max_retries < 0
                or not math.isfinite(self._retry_max_wait) or self._retry_max_wait <= 0
                or not math.isfinite(self._retry_wait_budget) or self._retry_wait_budget <= 0
                or not self._retry_delays
                or any(not math.isfinite(wait) or wait < 0
                       for wait in (*self._retry_delays, *self._pace_waits))):
            raise ValueError("Invalid retry configuration")
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=_env_float("LLM_TIMEOUT_SECONDS", 60.0, timeout),
            max_retries=0,  # The adapter owns retries; do not stack SDK retries.
            default_headers={"User-Agent": "Mozilla/5.0"},
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
        *,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not any(message.get("role") == "tool" for message in messages):
            self._emitted = []   # new task: forget the previous run's tool calls

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._repair_tool_messages(messages),
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if response_format is not None:
            # Send structured-output requirements to the provider, not just the prompt.
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = [to_tool_schema(tool) for tool in tools]
            kwargs["tool_choice"] = "auto"
        if self._model == "qwen/qwen3.6-27b" or self._model == "qwen-3.8-27b":
            kwargs["reasoning_effort"] = "none"
        if self._model.startswith("openai/gpt-oss") or self._model.startswith("gpt-oss"):
            kwargs["extra_body"] = {"reasoning_format": "hidden"}
   
        response = None
        last_error: Exception | None = None
        # One cumulative sleep budget per generate(), including opt-in outer cycles.
        remaining_wait = [self._retry_wait_budget]
        waits = self._pace_waits
        for _pace_attempt in range(len(waits) + 1):
            if self._use_pacer:
                _PACER.wait_for_slot()
            try:
                response = self._request_with_retry(kwargs, remaining_wait)
                break
            except (RateLimitError, APIConnectionError, APIStatusError) as pace_error:
                last_error = pace_error
                status = getattr(pace_error, "status_code", None)
                transient = (isinstance(pace_error, (RateLimitError, APIConnectionError))
                             or (status is not None and (status >= 500 or status == 408)))
                if not transient or _pace_attempt >= len(waits):
                    raise
                delay = max(waits[_pace_attempt], self._retry_delay(pace_error, 0))
                self._wait_before_retry(pace_error, delay, remaining_wait,
                                        f"extra cycle {_pace_attempt + 1}/{len(waits)}")
        if response is None:
            raise last_error  # type: ignore[misc]
        self.last_response = response

        message = response.choices[0].message
        calls = list(message.tool_calls or [])
        if calls:
            self._emitted.append(calls)

        # Agent._parse_result() accepts this dict shape. Returning it instead of the
        # raw SDK object stops a null content from becoming the string "None".
        return {"content": message.content or "", "tool_calls": calls}

    def _request_with_retry(self, kwargs, remaining_wait):
        for attempt in range(self._max_retries + 1):
            try:
                return self._client.chat.completions.create(**kwargs)
            except (APIConnectionError, APIStatusError) as error:
                transient = (isinstance(error, (RateLimitError, APIConnectionError))
                             or error.status_code >= 500 or error.status_code == 408)
                if not transient or attempt == self._max_retries:
                    if transient:
                        logger.warning("Model %s exhausted %d retries (HTTP %s).",
                                       self._model, self._max_retries,
                                       getattr(error, "status_code", "connection/timeout"))
                    raise
                delay = self._retry_delay(error, attempt)
                self._wait_before_retry(error, delay, remaining_wait,
                                        f"request {attempt + 1}/{self._max_retries}")

    def _wait_before_retry(self, error, delay, remaining_wait, label):
        if delay > self._retry_max_wait or delay > remaining_wait[0]:
            logger.warning(
                "Model %s needs %.1fs before retry; per-wait limit %.1fs, "
                "remaining wait budget %.1fs. Stopping retries.",
                self._model, delay, self._retry_max_wait, remaining_wait[0],
            )
            raise error
        # Positive jitter avoids synchronized retries without shortening Retry-After.
        jitter = random.uniform(0, min(1.0, delay * 0.1))
        delay = min(delay + jitter, self._retry_max_wait, remaining_wait[0])
        remaining_wait[0] -= delay
        logger.warning(
            "Temporary model failure (%s, HTTP %s, model %s). Retrying %s in %.1fs "
            "(%.1fs wait budget remaining).",
            type(error).__name__, getattr(error, "status_code", "connection/timeout"),
            self._model, label, delay, remaining_wait[0],
        )
        time.sleep(delay)

    def _retry_delay(self, error, attempt):
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
            ms_match = re.search(r"(?:try again|retry)\s+in\s+([0-9]+(?:\.[0-9]+)?)\s*ms", str(error), re.I)
            if ms_match:
                delay = float(ms_match.group(1)) / 1000.0
            else:
                s_match = re.search(r"(?:try again|retry)\s+in\s+([0-9]+(?:\.[0-9]+)?)\s*s", str(error), re.I)
                if s_match:
                    delay = float(s_match.group(1))
        window = min(self._retry_delays[min(attempt, len(self._retry_delays) - 1)],
                     self._retry_max_wait)
        if delay is not None and math.isfinite(delay) and delay >= 0:
            # Honor both our recovery window and the provider's minimum delay.
            return max(window, delay + 1.0)
        return window

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
