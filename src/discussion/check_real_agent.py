from pathlib import Path
from dotenv import load_dotenv

from src.agent.agent import Agent
from src.agent.config import AgentConfig
from src.agent.llm import OpenAICompatibleLLM
from src.agent.memory import ConversationMemory
from src.agent.tool_registery import ToolRegistery
from src.tools.calculator import CalculatorTool
from src.tools.knowledge_search import KnowledgeSearchTool
from src.tools.web_search import WebSearchTool

def main() -> None:

    project_root = Path(__file__).resolve().parent[2]

    load_dotenv(project_root / ".env")


    persona = load_persona(
        project_root / "personas" / "tactical_analyst.yaml"
)

    meomory = ConversationMemory()

    retreivel = RagRetrieval(k=3)

    tools = ToolRegistry(
    tools=[
        CalculatorTool(),
        KnowledgeSearchTool(retrieval=retrieval),
        WebSearchTool(),
    ]
)

    llm = OpenAICompatibleLLM()

    config = AgentConfig(
        persona=persona,
        memory=memory,
        tools=tools,
        retrieval=retrieval,
        llm=llm,
    )

    agent = Agent(config, max_tool_rounds=3)

    response = agent.run(
        "What are the advantages and limitations of a low defensive "
        "block against a stronger opponent? Explain from your tactical "
        "perspective and cite the retrieved sources. If the evidence "
        "is insufficient, say so."
    )


    print(f"\nAgent: {persona.name}")
    print("\nResponse:")
    print(response.content)

    print(f"\nRetrieved sources: {len(response.sources)}")
    for index, source in enumerate(response.sources, start=1):
        print(f"{index}. {source.source}")

    print(f"\nTool calls: {len(response.tool_calls)}")
    for call in response.tool_calls:
        print(f"- {call.name}")

    # A generated answer alone does not establish working retrieval.
    if not response.content.strip():
        raise RuntimeError("The agent returned an empty response.")

    if not response.sources:
        raise RuntimeError(
            "The agent responded, but returned no initial retrieval sources. "
            "Check the retrieval configuration and database."
        )

    print("\nPassed: the agent returned an answer and retrieval sources.")


if __name__ == "__main__":
    main()