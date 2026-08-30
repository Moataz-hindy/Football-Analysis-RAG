from dataclasses import dataclass
from typing import Any

from .interfaces import (
    LLMInterface,
    MemoryInterface,
    PersonaInterface,
    RetrievalInterface,
    ToolRegistryInterface,
)


@dataclass
class AgentConfig:
    """Dependencies required to construct an :class:`Agent`."""

    persona: PersonaInterface

    memory: MemoryInterface

    tools: ToolRegistryInterface

    retrieval: RetrievalInterface

    llm: LLMInterface