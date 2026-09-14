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

        search_query = self._build_persona_query(task)
        memory = self.memory.get_relevant(task)
        sources = self.retrieval.retrieve(search_query)
        tools = self.tools.get_tools()
        messages = self._build_messages(
            task=task,
            memory=memory,
            sources=sources,
        )

        tool_calls: list[ToolCall] = []
        result: object = None
        for _ in range(self.max_tool_rounds):
            result = self.llm.generate(messages=messages, tools=tools)
            content, requested_calls = self._parse_result(result)
            if not requested_calls:
                break

            messages.append({"role": "assistant", "content": content})
            for requested_call in requested_calls:
                try:
                    tool_result = self.tools.execute(
                        requested_call.name,
                        requested_call.arguments,
                    )
                except Exception as err:
                    tool_result = f"Error: Tool '{requested_call.name}' is not available or failed: {err}"
                requested_call.result = tool_result
                tool_calls.append(requested_call)
                messages.append({
                    "role": "tool",
                    "name": requested_call.name,
                    "content": str(tool_result),
                })
        else:
            messages.append({
                "role": "user",
                "content": "Conclude your tool searches and provide your final response now.",
            })
            result = self.llm.generate(messages=messages, tools=None)

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
            "\n\nThis is a live discussion turn with tools enabled (`web_search`, `knowledge_search`, `calculator`).\n"
            "MANDATORY VERIFICATION DIRECTIVE:\n"
            "Review the claims and arguments in the received messages from other analysts:\n"
            "- If an opponent alleges officiating bias, referee influence, controversial decisions (e.g. VAR reviews, disallowed goals, penalty calls), "
            "or contested match events, you MUST invoke `web_search` or `knowledge_search` first to verify the facts before answering.\n"
            "- If you want to challenge an opponent's factual assertion or if critical match facts are in dispute, "
            "use `web_search` (e.g., query: '<match> referee VAR disallowed goal controversy') to retrieve verified reporting.\n"
            "- Do not guess or argue over unverified premises. First retrieve the facts with tools, then deliver your analytical stance."
        )

        content, tool_calls = self._complete_with_tools(messages)

        # Anti-duplication check: ensure the agent did not copy-paste or recycle its previous turn
        if hasattr(self.memory, "history") and self.memory.history:
            prev_response = self.memory.history[-1].get("response", "")
            if prev_response and self._is_duplicate_response(content, prev_response):
                retry_messages = list(messages)
                retry_messages.append({"role": "assistant", "content": content})
                retry_messages.append({
                    "role": "user",
                    "content": (
                        "CRITICAL REJECTION: Your response was rejected because you recycled or copy-pasted "
                        "text/paragraphs from your previous round turn. "
                        "You MUST NOT repeat your previous text or reasoning. "
                        "Deliver a completely fresh analysis or conclusive synthesis addressing the latest "
                        "arguments and counter-arguments from other analysts."
                    ),
                })
                retry_result = self.llm.generate(messages=retry_messages, tools=None)
                retry_content, _ = self._parse_result(retry_result)
                if retry_content.strip() and not self._is_duplicate_response(retry_content, prev_response):
                    content = retry_content

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
        for _ in range(self.max_tool_rounds):
            result = self.llm.generate(messages=messages, tools=tools)
            content, requested_calls = self._parse_result(result)
            if not requested_calls:
                return content, tool_calls

            messages.append({"role": "assistant", "content": content})
            for requested_call in requested_calls:
                try:
                    tool_result = self.tools.execute(
                        requested_call.name,
                        requested_call.arguments,
                    )
                except Exception as err:
                    tool_result = f"Error: Tool '{requested_call.name}' is not available or failed: {err}"
                requested_call.result = tool_result
                tool_calls.append(requested_call)
                messages.append({
                    "role": "tool",
                    "name": requested_call.name,
                    "content": str(tool_result),
                })

        # When max_tool_rounds is reached, prompt the agent to formulate
        # its final response without tools to prevent infinite tool loops.
        messages.append({
            "role": "user",
            "content": (
                "You have completed your tool queries. Now provide your final response "
                "following the required format:\n"
                "STANCE: Your current position.\n"
                "REASONING: Address the received arguments and explain your position using available evidence.\n"
                "SOURCES USED: Identify the sources you relied on."
            ),
        })
        final_result = self.llm.generate(messages=messages, tools=None)
        final_content, _ = self._parse_result(final_result)
        if not final_content.strip():
            final_content = (
                "STANCE: Evidence is insufficient to support a definitive conclusion.\n"
                "REASONING: After multiple queries, sufficient factual data could not be retrieved.\n"
                "SOURCES USED: None."
            )
        return final_content, tool_calls

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
            if call.name == "knowledge_search" and isinstance(call.result, list):
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
            elif call.name == "web_search" and isinstance(call.result, str):
                entries = call.result.split("\n---\n")
                for entry in entries:
                    lines = entry.strip().split("\n")
                    title = ""
                    url = ""
                    content_lines = []
                    for line in lines:
                        if line.startswith("Title: "):
                            title = line[len("Title: "):].strip()
                        elif line.startswith("URL: "):
                            url = line[len("URL: "):].strip()
                        elif line.startswith("Content: "):
                            content_lines.append(line[len("Content: "):].strip())
                        else:
                            content_lines.append(line)
                    content_text = "\n".join(content_lines).strip()
                    if content_text or title:
                        sources.append(
                            RetrievedSource(
                                content=content_text or title,
                                source=url or title or "web_search",
                                score=1.0,
                                metadata={"title": title, "url": url},
                            )
                        )
        return sources

    @staticmethod
    def _is_duplicate_response(current: str, previous: str) -> bool:
        """Detect if current response is an exact copy or substantial paragraph duplicate of previous turn."""
        curr = current.strip()
        prev = previous.strip()
        if not curr or not prev:
            return False
        if curr == prev:
            return True

        curr_paras = [p.strip() for p in curr.split("\n\n") if len(p.strip()) > 60]
        prev_paras = set(p.strip() for p in prev.split("\n\n") if len(p.strip()) > 60)

        if not curr_paras or not prev_paras:
            return False

        # Exclude header/footer boilerplate lines
        substantive_curr = [p for p in curr_paras if not p.startswith("SOURCES USED:") and not p.startswith("STANCE:")]
        substantive_prev = {p for p in prev_paras if not p.startswith("SOURCES USED:") and not p.startswith("STANCE:")}

        if not substantive_curr or not substantive_prev:
            return False

        matches = sum(1 for p in substantive_curr if p in substantive_prev)
        return (matches / len(substantive_curr)) >= 0.5

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

        source_context = self._format_sources(sources)
        available_tools = ", ".join(t.name for t in self.tools.get_tools()) if self.tools else "none"

        # Include summary of older conversation if present
        summary_context = ""
        mem_str = str(memory).strip() if memory else ""
        if mem_str and mem_str not in ("No relevant previous memory.", "No previous context."):
            summary_context = f"\n\nEARLIER CONTEXT SUMMARY:\n{mem_str}\n"

        system_message = (
            "You are an AI agent operating according to this persona.\n\n"
            f"PERSONA:\n{persona}"
            f"{summary_context}\n"
            f"KNOWLEDGE:\n{source_context}\n\n"
            f"AVAILABLE TOOLS: {available_tools}.\n"
            "Only invoke tools from the AVAILABLE TOOLS list. Do not attempt to invoke unlisted tools.\n"
            "Use the retrieved knowledge to ground your response. "
            "Do not invent sources."
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_message}]

        # Add past conversation history as proper alternating user/assistant messages
        if hasattr(self.memory, "get_messages") and callable(self.memory.get_messages):
            messages.extend(self.memory.get_messages())
        elif hasattr(self.memory, "history") and isinstance(self.memory.history, list):
            for turn in self.memory.history:
                if isinstance(turn, dict) and "response" in turn:
                    t_lines = [l.strip() for l in turn.get("task", "").split("\n") if l.strip()]
                    t_summary = t_lines[0] if t_lines else "Discussion turn"
                    messages.append({"role": "user", "content": t_summary})
                    messages.append({"role": "assistant", "content": turn["response"]})

        messages.append({"role": "user", "content": task})
        return messages

    def _build_persona_query(self, task: str) -> str:
        """Formulate a targeted retrieval query incorporating persona domain expertise."""
        base_query = task
        if "Discussion topic:" in task:
            topic_line = task.split("Discussion topic:", 1)[1].split("\n", 1)[0].strip()
            if topic_line:
                base_query = topic_line

        persona_name = getattr(self.persona, "name", "").lower()
        expertise_text = " ".join(getattr(self.persona, "expertise", [])).lower()
        combined = f"{persona_name} {expertise_text}"

        if any(term in combined for term in ["var", "referee", "law 12", "officiating"]):
            return f"{base_query} referee decisions VAR disallowed goal penalties fouls cards"
        if any(term in combined for term in ["tactical", "pressing", "low block", "formation", "coach"]):
            return f"{base_query} tactical formations pressing low block transition shape"
        if any(term in combined for term in ["statistical", "data", "xg", "metrics"]):
            return f"{base_query} Opta stats expected goals xG shots possession metrics"
        if any(term in combined for term in ["fan", "supporter", "underdog", "pharaohs"]):
            return f"{base_query} controversy disallowed goal referee decisions fan reaction"
        if any(term in combined for term in ["performance", "athletic", "fatigue", "intensity"]):
            return f"{base_query} player performance physical fatigue individual duels mental resilience"
        if any(term in combined for term in ["context", "historical", "tournament", "history"]):
            return f"{base_query} match report tournament context history records comeback"

        return base_query

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