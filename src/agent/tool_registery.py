"""Tool Registry Implementation.
Manages tool registration, listing, and safe execution for the Intelligent Agent Framework.
"""

from typing import Any
from .interfaces import ToolInterface, ToolRegistryInterface

class ToolRegistery(ToolRegistryInterface):

    def __init__(self, tools: list[ToolInterface] | None = None):

        self._tools: dict[str, ToolInterface] = {}
        if tools:
            for tool in tools:
                self.register(tool)

    def register(self, tool: ToolInterface) -> None:
        """Register a tool instance satisfying ToolInterface.
        
        Args:
            tool: An instance implementing ToolInterface.
        """
        if not isinstance(tool, ToolInterface):
            raise TypeError(f"Expected ToolInterface implement, got {type(tool).__name__}") 

        name = tool.name
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Tool must have a non-empty string name, got {name!r}")
        
        if name in self._tools:
            raise ValueError(f"Tool with name '{name}' is already registered")

        self._tools[name] = tool

    def get_tools(self) -> list[ToolInterface]:
        """Return a list of all registered tool instances.
        
        Returns:
            list[ToolInterface]: List of registered tools.
        """
        return list(self._tools.values())

    def execute(self, name: str, arguments:dict[str, Any]) -> Any:
        """Execute a registered tool by name with arguments.
        
        Args:
            name: Name of the tool to execute.
            arguments: Dictionary of arguments passed to the tool.
            
        Returns:
            Any: Result of tool execution.
        """

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tool name must be a non-empty string.")
        
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        
        if not isinstance(arguments, dict):
            raise TypeError(f"Tool arguments must be a dict, got {type(arguments).__name__}")

        tool = self._tools[name]
        try:
            return tool.run(arguments)
        except Exception as e:
            return f"Error executing tool '{name}':{str(e)}"
        
    def __contains__(self, name: str) -> bool:
        return name in self._tools
    
    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistery tools={list(self._tools.keys())}>"


# Alias matching standard spelling in tests
ToolRegistry = ToolRegistery