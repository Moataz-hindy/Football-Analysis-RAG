"""Interactive Week 2 check using the existing project's agents and configuration."""
import argparse
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--repo', required=True, type=Path)
a = p.parse_args()
repo = a.repo.resolve()
sys.path.insert(0, str(repo))
from dotenv import load_dotenv
load_dotenv(repo / '.env', override=True)
from src.agent.agent import Agent
from src.agent.config import AgentConfig
from src.agent.llm import OpenAICompatibleLLM
from src.agent.memory import ConversationMemory
from src.agent.persona_loader import load_persona
from src.agent.retrieval import RAGRetrieval
from src.agent.tool_registery import ToolRegistry
from src.tools.knowledge_search import KnowledgeSearchTool
from src.tools.calculator import CalculatorTool
from src.tools.web_search import WebSearchTool

llm = OpenAICompatibleLLM(max_retries=0, timeout=45)
agents = {}
for name in ('tactical', 'statistical'):
    retrieval = RAGRetrieval(k=6)
    agents[name] = Agent(AgentConfig(
        persona=load_persona(repo / 'personas' / f'{name}_analyst.yaml'),
        memory=ConversationMemory(max_turns=5, llm=llm),
        tools=ToolRegistry([KnowledgeSearchTool(retrieval=retrieval), CalculatorTool(), WebSearchTool()]),
        retrieval=retrieval, llm=llm,
    ), max_tool_rounds=3)

print('Week 2 interactive check. Each question calls your configured chat API.')
print('Use tactical: QUESTION, statistical: QUESTION, or both: QUESTION.')
print('Available tools: knowledge_search, calculator, web_search.')
print('Memory stays separate for each analyst and lasts for this session. Type quit to exit.')
try:
    while True:
        text = input('\n> ').strip()
        if text.lower() in ('quit', 'exit'):
            break
        target, sep, task = text.partition(':')
        if not sep or target.strip().lower() not in ('tactical', 'statistical', 'both') or not task.strip():
            print('Example: both: How useful is xG for evaluating team performance?')
            continue
        names = list(agents) if target.strip().lower() == 'both' else [target.strip().lower()]
        for name in names:
            print(f'\n--- {name.upper()} ---', flush=True)
            try:
                result = agents[name].run(task.strip())
            except Exception as error:
                cause = error
                while cause.__cause__ is not None:
                    cause = cause.__cause__
                print(f'Failed: {type(cause).__name__}; HTTP status: {getattr(cause, "status_code", "not available")}.')
                print('Check provider/model configuration and quota. No fallback opinion was generated.')
                continue
            print(result.content)
            print('\nEvidence retrieved (check that it actually supports the answer):')
            for source in result.sources:
                meta = source.metadata or {}
                print(f'  {meta.get("doc_id")} chunk {meta.get("chunk_index")} [{meta.get("retrieval_mode", "unknown")}] {source.source}')
            print('Tool activity:', ', '.join(f'{t.name} ({t.status})' for t in result.tool_calls))
            print('Turns retained:', len(agents[name].memory.history))
except (KeyboardInterrupt, EOFError):
    print('\nStopped.')
finally:
    llm._client.close()
