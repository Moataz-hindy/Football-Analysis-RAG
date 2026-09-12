"""Reproducible multi-agent discussion demonstration (Week 3, Requirement 4.8).

Runs one complete discussion — initial opinions, ``--rounds`` discussion
rounds, mid-discussion Week 1 retrieval — and persists a self-contained
record under ``outputs/{discussion_id}.json`` that a downstream system
(Week 4) can reload by identifier alone.

Run from the project root::

    python -m src.discussion.run_discussion

The persisted config records the discussion id, topic, participating
agents, graph adjacency, number of rounds, and the LLM model/temperature
captured from the adapter that actually served the run, so the run and
its configuration stay traceable. LLM output itself is not exactly
reproducible; set ``LLM_TEMPERATURE=0`` in ``.env`` for more stable runs.
"""

import argparse
import re
import sys
import time
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from src.agent.agent import Agent
from src.agent.config import AgentConfig
from src.agent.llm import OpenAICompatibleLLM
from src.agent.memory import ConversationMemory
from src.agent.persona_loader import load_persona
from src.agent.retrieval import RAGRetrieval
from src.agent.tool_registery import ToolRegistry
from src.discussion.orchestrator import DiscussionOrchestrator, DiscussionRunError
from src.discussion.persistence import (
    load_discussion_by_id,
    save_discussion_from_state,
)
from src.discussion.router import GraphRouter
from src.tools.calculator import CalculatorTool
from src.tools.knowledge_search import KnowledgeSearchTool

DEFAULT_TOPIC = (
    "Evaluate Japan's 5-4-1 low block against Spain in the 2022 World Cup. "
    "Was it tactically effective?"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run and persist one reproducible multi-agent discussion.",
    )
    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
        help="Discussion topic (should be supported by the Week 1 knowledge base).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of discussion rounds (minimum 3; default 3).",
    )
    parser.add_argument(
        "--discussion-id",
        default=None,
        help=(
            "Identifier the run is persisted under (defaults to a fresh UUID). "
            "Pass an explicit value to make the run's name deterministic."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory the discussion JSON is written to (default: outputs).",
    )
    parser.add_argument(
        "--personas-dir",
        default="personas",
        help="Directory containing the persona YAML files (default: personas).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    discussion_id = args.discussion_id or str(uuid4())

    if not re.fullmatch(r"[A-Za-z0-9_-]+", discussion_id):
        raise ValueError("Use only letters, digits, underscores and hyphens in discussion IDs")
    if (Path(args.output_dir) / f"{discussion_id}.json").exists():
        raise ValueError("That discussion ID already exists; choose a new ID to preserve its history")

    router = GraphRouter()
    llm = OpenAICompatibleLLM()  # one shared adapter; config is captured from it

    agents: dict[str, Agent] = {}
    persona_files: dict[str, str] = {}
    for agent_id in sorted(router.graph.graph.nodes):
        persona_file = f"{agent_id}.yaml"
        persona = load_persona(Path(args.personas_dir) / persona_file)
        persona_files[agent_id] = persona_file

        retrieval = RAGRetrieval(k=3)
        config = AgentConfig(
            persona=persona,
            memory=ConversationMemory(llm=llm),
            retrieval=retrieval,
            tools=ToolRegistry(
                tools=[CalculatorTool(), KnowledgeSearchTool(retrieval=retrieval)]
            ),
            llm=llm,
        )
        agents[agent_id] = Agent(config, max_tool_rounds=3)

    started = time.monotonic()

    def checkpoint(state):
        save_discussion_from_state(
            state=state, router=router, output_dir=args.output_dir, llm=llm,
            config_metadata={"persona_files": persona_files,
                             "retrieval": "week1_pgvector_k3", "status": "running"},
            duration_seconds=time.monotonic() - started,
        )

    orchestrator = DiscussionOrchestrator(agents=agents, router=router, checkpoint=checkpoint)

    print(f"Discussion ID:   {discussion_id}")
    print(f"Agents:          {len(agents)}")
    print(f"Rounds:          {args.rounds}, plus initial opinions")
    print(f"Output dir:      {args.output_dir}")
    print(f"Topic:           {args.topic}")
    print("Starting discussion... (LLM calls may take several minutes)", flush=True)

    errors: list[str] = []
    try:
        state = orchestrator.run(
            topic=args.topic,
            total_rounds=args.rounds,
            discussion_id=discussion_id,
        )
    except DiscussionRunError as error:
        # Persist the partial history so the failure is inspectable instead
        # of silently lost; annotate the record with the error.
        errors.append(
            f"Agent '{error.agent_id}' failed in round {error.round_number}: "
            f"{error.__cause__}"
        )
        state = error.state
        path = save_discussion_from_state(
            state=state,
            router=router,
            output_dir=args.output_dir,
            llm=llm,
            config_metadata={
                "persona_files": persona_files,
                "retrieval": "week1_pgvector_k3",
                "status": "interrupted" if isinstance(error.__cause__, KeyboardInterrupt) else "failed_partial",
            },
            duration_seconds=time.monotonic() - started,
            errors=errors,
        )
        print(f"\nFAILED — partial history saved to {path}", file=sys.stderr)
        print(f"Failed agent: {error.agent_id} (round {error.round_number})", file=sys.stderr)
        return 1

    elapsed = time.monotonic() - started
    path = save_discussion_from_state(
        state=state,
        router=router,
        output_dir=args.output_dir,
        llm=llm,
        config_metadata={
            "persona_files": persona_files,
            "retrieval": "week1_pgvector_k3",
            "status": "completed",
        },
        duration_seconds=elapsed,
        errors=errors,
    )

    # Verify the run is reconstructable from its identifier alone.
    result = load_discussion_by_id(discussion_id, output_dir=args.output_dir)
    retrieval_events = sum(
        len(message.retrieval_events) for message in result.messages
    )
    opinion_changes = sum(
        1 for opinion in result.opinions if opinion.changed_from_previous
    )

    print("\n" + "=" * 72)
    print("DISCUSSION COMPLETE")
    print("=" * 72)
    print(f"Discussion ID:        {result.config.discussion_id}")
    print(f"Saved file:           {path}")
    print(f"Topic:                {result.config.topic}")
    print(f"Participants:         {', '.join(result.config.agent_ids)}")
    print(f"Rounds:               {result.config.num_rounds}")
    print(f"Messages:             {result.metadata.total_messages}")
    print(f"Retrieval events:     {retrieval_events}")
    print(f"Opinion changes:      {opinion_changes}")
    print(f"LLM model:            {result.config.llm_model}")
    print(f"LLM temperature:      {result.config.llm_temperature}")
    print(f"Duration (seconds):   {elapsed:.1f}")
    print("\nReload anytime with:")
    print(
        "  python -c \"from src.discussion import load_discussion_by_id;"
        f" r = load_discussion_by_id('{discussion_id}', '{args.output_dir}');"
        " print(r.config.topic)\""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
