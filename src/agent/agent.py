from .config import AgentConfig
from .types import AgentResponse, RetrievedSource, ToolCall


class Agent:


    """Orchestrate persona, memory, retrieval, tools, and an LLM."""

    def __init__(self, config: AgentConfig, max_tool_rounds: int = 5):
        if max_tool_rounds < 0:
            raise ValueError("max_tool_rounds must be non-negative")

        self.persona = config.persona
        self.memory = config.memory
        self.tools = config.tools
        self.retrieval = config.retrieval
        self.llm = config.llm
        self.max_tool_rounds = max_tool_rounds

    def run(self, task: str) -> AgentResponse:
        """Run a task and return the final answer with its evidence and tools."""
        if not isinstance(task, str) or not task.strip():
            raise ValueError("task must be a non-empty string")

        memory = self.memory.get_relevant(task)
        sources = self.retrieval.retrieve(task)
        tools = self.tools.get_tools()
        messages = self._build_messages(
            task=task,
            memory=memory,
            sources=sources,
        )

        tool_calls: list[ToolCall] = []
        result: object = None
        for _ in range(self.max_tool_rounds + 1):
            result = self.llm.generate(messages=messages, tools=tools)
            content, requested_calls = self._parse_result(result)
            if not requested_calls:
                break

            messages.append({"role": "assistant", "content": content})
            for requested_call in requested_calls:
                tool_result = self.tools.execute(
                    requested_call.name,
                    requested_call.arguments,
                )
                requested_call.result = tool_result
                tool_calls.append(requested_call)
                messages.append({
                    "role": "tool",
                    "name": requested_call.name,
                    "content": str(tool_result),
                })
        else:
            raise RuntimeError("LLM exceeded the maximum number of tool rounds")

        content, _ = self._parse_result(result)
        self.memory.add({
            "task": task,
            "response": content,
        })

        return AgentResponse(
            content=content,
            sources=sources,
            tool_calls=tool_calls,
        )

    def run_discussion_turn(
        self,
        task: str,
        received_messages: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Respond to a discussion turn and retrieve evidence when needed.

        ``received_messages`` contains messages routed to this agent by the
        discussion engine. Retrieval is exposed through the configured tools,
        so the LLM can request Week 1 knowledge after reading those messages.
        Retrieved tool results are returned in ``AgentResponse.sources``.
        """
        if not isinstance(task, str) or not task.strip():
            raise ValueError("task must be a non-empty string")
        if received_messages is not None and not isinstance(received_messages, list):
            raise TypeError("received_messages must be a list of message dictionaries")
        if any(
            not isinstance(message, dict)
            or not isinstance(message.get("content"), str)
            for message in received_messages or []
        ):
            raise ValueError("each received message must contain string 'content'")

        memory = self.memory.get_relevant(task)
        discussion_context = self._format_discussion_messages(received_messages or [])
        messages = self._build_messages(
            task=(
                f"Discussion task:\n{task}\n\n"
                f"Messages received from other agents:\n{discussion_context}"
            ),
            memory=memory,
            sources=[],
        )
        messages[0]["content"] += (
            "\n\nThis is a live discussion turn. If a received claim needs "
            "verification or additional football knowledge, use the "
            "knowledge_search tool before answering."
        )

        content, tool_calls = self._complete_with_tools(messages)
        sources = self._sources_from_tool_calls(tool_calls)
        self.memory.add({"task": task, "response": content})

        return AgentResponse(
            content=content,
            sources=sources,
            tool_calls=tool_calls,
            metadata={"received_messages": received_messages or []},
        )

    def _complete_with_tools(
        self,
        messages: list[dict[str, str]],
    ) -> tuple[str, list[ToolCall]]:
        tools = self.tools.get_tools()
        tool_calls: list[ToolCall] = []
        for _ in range(self.max_tool_rounds + 1):
            result = self.llm.generate(messages=messages, tools=tools)
            content, requested_calls = self._parse_result(result)
            if not requested_calls:
                return content, tool_calls

            messages.append({"role": "assistant", "content": content})
            for requested_call in requested_calls:
                requested_call.result = self.tools.execute(
                    requested_call.name,
                    requested_call.arguments,
                )
                tool_calls.append(requested_call)
                messages.append({
                    "role": "tool",
                    "name": requested_call.name,
                    "content": str(requested_call.result),
                })
        raise RuntimeError("LLM exceeded the maximum number of tool rounds")

    @staticmethod
    def _format_discussion_messages(messages: list[dict[str, str]]) -> str:
        if not messages:
            return "No messages have been received yet."
        return "\n\n".join(
            f"From {message.get('sender', 'unknown agent')}: {message['content']}"
            for message in messages
        )

    @staticmethod
    def _sources_from_tool_calls(tool_calls: list[ToolCall]) -> list[RetrievedSource]:
        sources: list[RetrievedSource] = []
        for call in tool_calls:
            if call.name != "knowledge_search" or not isinstance(call.result, list):
                continue
            for item in call.result:
                if not isinstance(item, dict) or "content" not in item:
                    continue
                sources.append(
                    RetrievedSource(
                        content=str(item["content"]),
                        source=str(item.get("source", "Unknown")),
                        score=item.get("score"),
                    )
                )
        return sources

    def _build_messages(
        self,
        task: str,
        memory: object,
        sources: list[RetrievedSource],
    ) -> list[dict[str, str]]:
        """Build the model context without coupling to component implementations."""
        persona = "\n".join([
            f"Name: {self.persona.name}",
            f"Background: {self.persona.background}",
            f"Stance: {self.persona.stance}",
            f"Communication style: {self.persona.communication_style}",
            f"Expertise: {', '.join(self.persona.expertise)}",
            f"Priorities: {', '.join(self.persona.priorities)}",
        ])

        memory_context = str(memory) if memory else "No relevant previous memory."
        source_context = self._format_sources(sources)
        system_message = (
            "You are an AI agent operating according to this persona.\n\n"
            f"PERSONA:\n{persona}\n\n"
            f"MEMORY:\n{memory_context}\n\n"
            f"KNOWLEDGE:\n{source_context}\n\n"
            "Use the retrieved knowledge to ground your response. "
            "Do not invent sources."
        )
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task},
        ]

    @staticmethod
    def _format_sources(sources: list[RetrievedSource]) -> str:
        if not sources:
            return "No retrieved knowledge."
        return "\n\n".join(
            f"Source {index}\nContent:\n{source.content}\n"
            f"Source: {source.source}\nScore: {source.score}"
            for index, source in enumerate(sources, start=1)
        )

    @staticmethod
    def _parse_result(result: object) -> tuple[str, list[ToolCall]]:
        """Accept a plain string, AgentResponse, dict, or SDK-like result object."""
        if isinstance(result, AgentResponse):
            return result.content, list(result.tool_calls)
        if isinstance(result, str):
            return result, []

        if isinstance(result, dict):
            content = result.get("content", "")
            raw_calls = result.get("tool_calls", [])
        else:
            message = getattr(result, "message", result)
            choices = getattr(result, "choices", None)
            if choices:
                message = getattr(choices[0], "message", choices[0])
            content = getattr(message, "content", "")
            raw_calls = getattr(message, "tool_calls", [])

        calls = []
        for raw_call in raw_calls or []:
            if isinstance(raw_call, ToolCall):
                calls.append(raw_call)
                continue
            if isinstance(raw_call, dict):
                name = raw_call.get("name") or raw_call.get("function", {}).get("name")
                arguments = raw_call.get("arguments") or raw_call.get("function", {}).get("arguments", {})
            else:
                function = getattr(raw_call, "function", raw_call)
                name = getattr(raw_call, "name", None) or getattr(function, "name", None)
                arguments = getattr(raw_call, "arguments", None) or getattr(function, "arguments", {})
            if not name:
                raise ValueError("LLM returned a tool call without a name")
            calls.append(ToolCall(name=name, arguments=Agent._parse_arguments(arguments)))
        return str(content), calls

    @staticmethod
    def _parse_arguments(arguments: object) -> dict:
        if isinstance(arguments, dict):
            return arguments
        if isinstance(arguments, str):
            import json
            parsed = json.loads(arguments)
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("Tool-call arguments must be a dictionary or JSON object")