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