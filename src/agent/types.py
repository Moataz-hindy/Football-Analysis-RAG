from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedSource:
    """
    Represents a piece of knowledge retrieved from the Week 1
    knowledge infrastructure.
    """

    content: str
    source: str
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """
    Represents a tool invocation performed by the agent.
    """

    name: str
    arguments: dict[str, Any]
    result: Any = None


@dataclass
class AgentResponse:
    """
    Standard response returned by the Agent.
    """

    content: str

    sources: list[RetrievedSource] = field(default_factory=list)

    tool_calls: list[ToolCall] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)