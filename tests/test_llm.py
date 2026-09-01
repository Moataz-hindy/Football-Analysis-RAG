"""Offline tests for the OpenAI-compatible LLM adapter.

Nothing here reaches the network or needs an API key -- the SDK client is mocked.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.agent.agent import Agent
from src.agent.llm import DEFAULT_PARAMETERS, OpenAICompatibleLLM, to_tool_schema

LLM_ENV_VARS = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")


def make_tool_call(call_id, name, arguments):
    """Duck-types openai's ChatCompletionMessageFunctionToolCall."""
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def make_response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)


@pytest.fixture
def llm():
    """Adapter whose client is mocked, so no request leaves the process."""
    adapter = OpenAICompatibleLLM(
        api_key="test-key", base_url="http://localhost:1/v1", model="test-model"
    )
    adapter._client = MagicMock()
    adapter._client.chat.completions.create.return_value = make_response(content="hi")
    return adapter


def sent_kwargs(llm):
    return llm._client.chat.completions.create.call_args.kwargs


def test_to_tool_schema_defaults_when_a_tool_has_no_parameters():
    # ToolInterface exposes only name/description today, so this is the common case.
    tool = SimpleNamespace(name="calculator", description="does maths")
    schema = to_tool_schema(tool)

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "calculator"
    assert schema["function"]["description"] == "does maths"
    assert schema["function"]["parameters"] == DEFAULT_PARAMETERS


def test_to_tool_schema_prefers_the_tools_own_parameters():
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}
    tool = SimpleNamespace(name="knowledge_search", description="d", parameters=parameters)

    assert to_tool_schema(tool)["function"]["parameters"] == parameters


def test_generate_forwards_model_and_sampling_settings(llm):
    llm.generate([{"role": "user", "content": "hi"}])

    kwargs = sent_kwargs(llm)
    assert kwargs["model"] == "test-model"
    assert kwargs["temperature"] == 0.2
    assert kwargs["max_tokens"] == 1024
    assert "tools" not in kwargs
    assert "tool_choice" not in kwargs


def test_generate_serialises_tools_and_lets_the_model_choose(llm):
    tool = SimpleNamespace(name="calculator", description="does maths")

    llm.generate([{"role": "user", "content": "2+2"}], tools=[tool])

    kwargs = sent_kwargs(llm)
    assert kwargs["tools"] == [to_tool_schema(tool)]
    assert kwargs["tool_choice"] == "auto"


def test_generate_returns_a_shape_agent_can_parse(llm):
    calls = [make_tool_call("call_1", "knowledge_search", '{"query": "xg"}')]
    llm._client.chat.completions.create.return_value = make_response(tool_calls=calls)

    result = llm.generate([{"role": "user", "content": "xg?"}])

    # The wire sends content=None beside tool calls; Agent._parse_result() coerces
    # with str(), so passing None through would write the string "None".
    assert result["content"] == ""
    content, parsed = Agent._parse_result(result)
    assert content == ""
    assert [call.name for call in parsed] == ["knowledge_search"]
    assert parsed[0].arguments == {"query": "xg"}


def test_tool_messages_get_the_ids_the_wire_format_requires(llm):
    calls = [make_tool_call("call_1", "knowledge_search", '{"query": "xg"}')]
    llm._client.chat.completions.create.return_value = make_response(tool_calls=calls)
    llm.generate([{"role": "user", "content": "xg?"}])

    # Exactly what Agent.run() appends after executing the tool: no tool_calls on
    # the assistant turn, no tool_call_id on the tool turn.
    history = [
        {"role": "user", "content": "xg?"},
        {"role": "assistant", "content": ""},
        {"role": "tool", "name": "knowledge_search", "content": "[...]"},
    ]
    llm._client.chat.completions.create.return_value = make_response(content="done")
    llm.generate(history)

    sent = sent_kwargs(llm)["messages"]
    assert sent[1]["tool_calls"][0]["id"] == "call_1"
    assert sent[1]["tool_calls"][0]["function"]["name"] == "knowledge_search"
    assert sent[1]["tool_calls"][0]["function"]["arguments"] == '{"query": "xg"}'
    assert sent[2] == {"role": "tool", "tool_call_id": "call_1", "content": "[...]"}
    # The caller's list is copied, not rewritten underneath it.
    assert history[2] == {"role": "tool", "name": "knowledge_search", "content": "[...]"}


def test_repair_pairs_several_rounds_and_parallel_calls_by_position(llm):
    llm._emitted = [
        [make_tool_call("call_1", "knowledge_search", "{}")],
        [
            make_tool_call("call_2", "calculator", "{}"),
            make_tool_call("call_3", "knowledge_search", "{}"),
        ],
    ]
    history = [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": ""},
        {"role": "tool", "name": "knowledge_search", "content": "r1"},
        {"role": "assistant", "content": "thinking"},
        {"role": "tool", "name": "calculator", "content": "r2"},
        {"role": "tool", "name": "knowledge_search", "content": "r3"},
    ]

    repaired = llm._repair_tool_messages(history)

    tool_turns = [(m["tool_call_id"], m["content"]) for m in repaired if m["role"] == "tool"]
    assert tool_turns == [("call_1", "r1"), ("call_2", "r2"), ("call_3", "r3")]
    assert [call["id"] for call in repaired[3]["tool_calls"]] == ["call_2", "call_3"]
    assert repaired[3]["content"] == "thinking"
    assert repaired[1]["content"] is None      # empty content is sent as null


def test_a_new_task_forgets_the_previous_runs_tool_calls(llm):
    llm._emitted = [[make_tool_call("call_1", "knowledge_search", "{}")]]

    llm.generate([{"role": "user", "content": "an unrelated question"}])

    assert llm._emitted == []


@pytest.mark.parametrize(
    "configured", [(), ("LLM_API_KEY",), ("LLM_API_KEY", "LLM_BASE_URL")]
)
def test_incomplete_configuration_fails_before_any_request(monkeypatch, configured):
    for name in LLM_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    for name in configured:
        monkeypatch.setenv(name, "set")

    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        OpenAICompatibleLLM()
