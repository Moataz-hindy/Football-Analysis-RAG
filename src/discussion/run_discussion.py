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
import os
from pathlib import Path
from uuid import uuid4

# Fix for Windows SSL_CERT_FILE crash
os.environ.pop("SSL_CERT_FILE", None)

from dotenv import load_dotenv

from src.agent.agent import Agent
from src.agent.config import AgentConfig
from src.agent.llm import OpenAICompatibleLLM
from src.agent.memory import ConversationMemory
from src.agent.persona_loader import load_persona
from src.agent.retrieval import RAGRetrieval
from src.agent.tool_registery import ToolRegistry
from src.discussion.graph import DEFAULT_AGENT_ROSTER, build_discussion_graph, select_agent_roster
from src.discussion.orchestrator import DiscussionOrchestrator, DiscussionRunError
from src.discussion.persistence import (
    load_discussion_by_id,
    save_discussion_from_state,
)
from src.discussion.router import GraphRouter
from src.tools.calculator import CalculatorTool
from src.tools.knowledge_search import KnowledgeSearchTool
from src.tools.web_search import WebSearchTool

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
        "--agents",
        type=int,
        default=6,
        help="Number of specialist agents in the deliberation (2-6; default 6).",
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
    parser.add_argument(
        "--dynamic-personas",
        action="store_true",
        dest="dynamic_personas",
        help="Dynamically generate 3v3 polarized personas based on the debate topic using LLM.",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        dest="force_regenerate",
        help="Force regeneration of dynamic personas even if cached in personas/generated/<id>/.",
    )
    parser.add_argument(
        "--persona-ids",
        default="",
        help="Comma-separated list of persona IDs to use (system or custom user personas).",
    )
    parser.add_argument(
        "--camp-a-ids",
        default="",
        help="Comma-separated list of persona IDs assigned to Camp A (Thesis / Home).",
    )
    parser.add_argument(
        "--camp-b-ids",
        default="",
        help="Comma-separated list of persona IDs assigned to Camp B (Antithesis / Away).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        dest="overwrite",
        help="Overwrite existing output JSON file if discussion ID already exists.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=True)

    discussion_id = args.discussion_id or str(uuid4())
    discussion_id = re.sub(r"[^A-Za-z0-9_-]+", "-", discussion_id.strip()).strip("-")
    if not discussion_id or not re.fullmatch(r"[A-Za-z0-9_-]+", discussion_id):
        raise ValueError("Use only letters, digits, underscores and hyphens in discussion IDs")
    output_file = Path(args.output_dir) / f"{discussion_id}.json"
    if output_file.exists() and not args.overwrite:
        raise ValueError("That discussion ID already exists; choose a new ID or pass --overwrite to replace it")

    llm = OpenAICompatibleLLM()  # one shared adapter; config is captured from it
    agents: dict[str, Agent] = {}
    persona_files: dict[str, str] = {}

    manifest: dict = {}

    if args.dynamic_personas:
        from src.agent.persona_generator import generate_personas_for_topic
        from src.discussion.graph import DiscussionGraph

        personas_dict, persona_files_map, manifest = generate_personas_for_topic(
            topic=args.topic,
            llm=llm,
            discussion_id=discussion_id,
            output_dir=Path(args.personas_dir) / "generated",
            force_regenerate=args.force_regenerate,
        )
        n_agents = getattr(args, "agents", 6) or 6
        if n_agents == 6:
            graph = DiscussionGraph.create_symmetrical_3v3(
                camp_a=manifest["camp_a"],
                camp_b=manifest["camp_b"],
            )
        else:
            # Pairwise balanced selection between Camp A and Camp B (2 to 5 agents)
            camp_a_roles = manifest["camp_a"]
            camp_b_roles = manifest["camp_b"]
            interleaved = [
                camp_a_roles["coach"],
                camp_b_roles["coach"],
                camp_a_roles["fan"],
                camp_b_roles["fan"],
                camp_a_roles["pundit"],
                camp_b_roles["pundit"],
            ]
            chosen_dynamic_ids = interleaved[:n_agents]
            graph = DiscussionGraph.build_dynamic_discussion_graph(chosen_dynamic_ids)

        router = GraphRouter(graph=graph)
        active_ids = set(router.graph.graph.nodes)
        persona_files = {aid: persona_files_map[aid] for aid in active_ids if aid in persona_files_map}

        for agent_id in sorted(router.graph.graph.nodes):
            persona = personas_dict[agent_id]
            retrieval = RAGRetrieval(k=6)
            config = AgentConfig(
                persona=persona,
                memory=ConversationMemory(llm=llm),
                retrieval=retrieval,
                tools=ToolRegistry(
                    tools=[
                        CalculatorTool(),
                        KnowledgeSearchTool(retrieval=retrieval),
                        WebSearchTool(),
                    ]
                ),
                llm=llm,
            )
            agents[agent_id] = Agent(config, max_tool_rounds=3)
    elif getattr(args, "camp_a_ids", None) or getattr(args, "persona_ids", None):
        from src.discussion.graph import DiscussionGraph
        from src.platform.personas import get_persona_by_id
        import yaml

        camp_a_raw = [pid.strip() for pid in getattr(args, "camp_a_ids", "").split(",") if pid.strip()]
        camp_b_raw = [pid.strip() for pid in getattr(args, "camp_b_ids", "").split(",") if pid.strip()]
        if camp_a_raw and camp_b_raw:
            selected_ids = camp_a_raw + camp_b_raw
        else:
            selected_ids = [pid.strip() for pid in getattr(args, "persona_ids", "").split(",") if pid.strip()]
            half = max(1, len(selected_ids) // 2)
            camp_a_raw = selected_ids[:half]
            camp_b_raw = selected_ids[half:]

        personas_dict = {}
        for aid in selected_ids:
            p = get_persona_by_id(aid)
            if p:
                personas_dict[aid] = p
                gen_dir = Path(args.personas_dir) / "generated" / discussion_id
                gen_dir.mkdir(parents=True, exist_ok=True)
                p_yaml = gen_dir / f"{aid}.yaml"
                if not p_yaml.exists():
                    p_yaml.write_text(
                        yaml.safe_dump({
                            "name": p.name,
                            "background": p.background,
                            "stance": p.stance,
                            "communication_style": p.communication_style,
                            "expertise": p.expertise,
                            "priorities": p.priorities,
                        }),
                        encoding="utf-8",
                    )
                persona_files[aid] = str(p_yaml)

        valid_a = [aid for aid in camp_a_raw if aid in personas_dict]
        valid_b = [aid for aid in camp_b_raw if aid in personas_dict]
        valid_ids = valid_a + valid_b
        if len(valid_ids) < 2 or len(valid_ids) > 6:
            raise ValueError(
                f"Curated roster requires between 2 and 6 valid personas (received {len(valid_ids)})."
            )
        if len(valid_a) < 1 or len(valid_b) < 1:
            raise ValueError(
                f"Both Camp A and Camp B must have at least 1 persona (got A:{len(valid_a)}, B:{len(valid_b)})."
            )

        graph = DiscussionGraph.build_dynamic_discussion_graph(valid_ids)
        router = GraphRouter(graph=graph)

        manifest = {
            "camp_a": {"name": "Camp A", "ids": valid_a},
            "camp_b": {"name": "Camp B", "ids": valid_b},
        }

        for agent_id in sorted(router.graph.graph.nodes):
            persona = personas_dict[agent_id]
            retrieval = RAGRetrieval(k=6)
            config = AgentConfig(
                persona=persona,
                memory=ConversationMemory(llm=llm),
                retrieval=retrieval,
                tools=ToolRegistry(
                    tools=[
                        CalculatorTool(),
                        KnowledgeSearchTool(retrieval=retrieval),
                        WebSearchTool(),
                    ]
                ),
                llm=llm,
            )
            agents[agent_id] = Agent(config, max_tool_rounds=3)
    else:
        roster = select_agent_roster(getattr(args, "agents", 6))
        if len(roster) == len(DEFAULT_AGENT_ROSTER):
            # The full roster keeps the curated six-agent debate graph.
            router = GraphRouter()
        else:
            router = GraphRouter(graph=build_discussion_graph(list(roster)))
        for agent_id in sorted(router.graph.graph.nodes):
            persona_file = f"{agent_id}.yaml"
            persona = load_persona(Path(args.personas_dir) / persona_file)
            persona_files[agent_id] = persona_file

            retrieval = RAGRetrieval(k=6)
            config = AgentConfig(
                persona=persona,
                memory=ConversationMemory(llm=llm),
                retrieval=retrieval,
                tools=ToolRegistry(
                    tools=[
                        CalculatorTool(),
                        KnowledgeSearchTool(retrieval=retrieval),
                        WebSearchTool(),
                    ]
                ),
                llm=llm,
            )
            agents[agent_id] = Agent(config, max_tool_rounds=3)

    started = time.monotonic()

    extra_meta = {}
    if args.dynamic_personas:
        extra_meta["dynamic_personas"] = True
        if manifest:
            extra_meta["camps"] = manifest

    def checkpoint(state):
        save_discussion_from_state(
            state=state, router=router, output_dir=args.output_dir, llm=llm,
            config_metadata={
                "persona_files": persona_files,
                "retrieval": "week1_pgvector_k6",
                "status": "running",
                **extra_meta,
            },
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
                "retrieval": "week1_pgvector_k6",
                "status": "interrupted" if isinstance(error.__cause__, KeyboardInterrupt) else "failed_partial",
                **extra_meta,
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
            "retrieval": "week1_pgvector_k6",
            "status": "completed",
            **extra_meta,
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
