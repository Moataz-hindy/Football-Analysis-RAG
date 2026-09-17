"""Temporary real-agent check without Week 1 database or embeddings."""

from pathlib import Path

from dotenv import load_dotenv

from src.agent.agent import Agent
from src.agent.config import AgentConfig
from src.agent.interfaces import MemoryInterface, RetrievalInterface
from src.agent.llm import OpenAICompatibleLLM
from src.agent.persona_loader import load_persona
from src.agent.tool_registery import ToolRegistry
from src.agent.types import RetrievedSource
from src.tools.calculator import CalculatorTool
from src.tools.web_search import WebSearchTool


class DisabledRetrieval(RetrievalInterface):
    """Return no knowledge-base sources and make no external requests."""

    def retrieve(self, query: str) -> list[RetrievedSource]:
        return []


class TemporaryMemory(MemoryInterface):
    """Keep interactions locally without the Week 1-based summarizer."""

    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []

    def get_relevant(self, query: str) -> str:
        return "\n\n".join(
            f"Previous task: {item['task']}\n"
            f"Previous response: {item['response']}"
            for item in self.history
        )

    def add(self, data: dict[str, str]) -> None:
        self.history.append(dict(data))


def main() -> None:
    # Locate the project root and load your existing API settings.
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    persona = load_persona(
        project_root / "personas" / "tactical_analyst.yaml"
    )

    # Only these tools are available in this temporary check.
    tools = ToolRegistry(
        tools=[
            CalculatorTool(),
            WebSearchTool(),
        ]
    )

    config = AgentConfig(
        persona=persona,
        memory=TemporaryMemory(),
        retrieval=DisabledRetrieval(),
        tools=tools,
        llm=OpenAICompatibleLLM(max_tokens=800),
    )

    agent = Agent(config, max_tool_rounds=3)

    print("Week 1 retrieval is DISABLED for this temporary check.")
    print("Calling the real model; web search may also make an API request.")

    response = agent.run(
        "This test has no access to the internal football knowledge base.\n"
        "First, use the calculator tool to calculate (12 / 20) * 100. "
        "These are hypothetical numbers: 12 successful presses out of "
        "20 attempts.\n"
        "Then use web_search to find an article explaining pressing "
        "in football. Explain briefly how the calculated percentage "
        "could be interpreted, using your tactical perspective. "
        "Include the article URL and distinguish the hypothetical "
        "calculation from the article's actual claims.\n"
        "If a tool fails, clearly report that limitation."
    )

    print(f"\nAgent: {persona.name}")
    print("\nResponse:")
    print(response.content)

    print(f"\nWeek 1 sources: {len(response.sources)} (expected: 0)")
    print(f"Tool calls: {len(response.tool_calls)}")

    for call in response.tool_calls:
        print(f"\nTool: {call.name}")
        print(f"Arguments: {call.arguments}")
        print(f"Result: {str(call.result)[:1000]}")

    
    raw_response = agent.llm.last_response

    if raw_response is not None:
        choice = raw_response.choices[0]

    # "length" means generation reached its token limit.
    # "stop" means the model reported normal completion.
        print("Finish reason:", choice.finish_reason)

    # repr() makes None, empty strings, and whitespace visible.
        print("Raw answer:", repr(choice.message.content))

    # Shows how many tokens the provider reports using.
        print("Token usage:", raw_response.usage)



    if not response.content.strip():
        raise RuntimeError("The model returned an empty answer.")

    called_tools = {call.name for call in response.tool_calls}
    missing_tools = {"calculator", "web_search"} - called_tools

    if missing_tools:
        print(
            "\nThe model responded, but did not call these requested tools: "
            + ", ".join(sorted(missing_tools))
        )
    else:
        print("\nThe model responded and called both requested tools.")

    # A call can return an error, so inspect results as well as call names.
    print("Check the tool results above to confirm each call succeeded.")


if __name__ == "__main__":
    main()