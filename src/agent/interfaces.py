from abc import ABC, abstractmethod
from typing import Any

from .types import RetrievedSource


class MemoryInterface(ABC):

    @abstractmethod
    def get_relevant(self, query: str) -> Any:
        pass

    @abstractmethod
    def add(self, data: Any) -> None:
        pass


class RetrievalInterface(ABC):

    @abstractmethod
    def retrieve(self, query: str) -> list[RetrievedSource]:
        pass


class ToolInterface(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def run(self, arguments: dict[str, Any]) -> Any:
        pass


class ToolRegistryInterface(ABC):

    @abstractmethod
    def register(self, tool: ToolInterface) -> None:
        pass

    @abstractmethod
    def get_tools(self) -> list[ToolInterface]:
        pass

    @abstractmethod
    def execute(
        self,
        name: str,
        arguments: dict[str, Any]
    ) -> Any:
        pass


class LLMInterface(ABC):

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolInterface] | None = None,
    ) -> Any:
        pass


class PersonaInterface(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def background(self) -> str:
        pass

    @property
    @abstractmethod
    def stance(self) -> str:
        pass

    @property
    @abstractmethod
    def communication_style(self) -> str:
        pass

    @property
    @abstractmethod
    def expertise(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def priorities(self) -> list[str]:
        pass