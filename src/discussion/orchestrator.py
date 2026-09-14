"""Coordinates the agents participating in a discussion."""

from dataclasses import asdict
from typing import Callable

from src.agent.agent import Agent
from src.discussion.models import DiscussionMessage, DiscussionState
from src.discussion.router import GraphRouter
from src.agent.types  import AgentResponse 



class DiscussionRunError(RuntimeError):
    """An agent failed; retain the discussion state for inspection."""

    def __init__(
        self,
        agent_id: str,
        state: DiscussionState,
    ) -> None:
        # Save the identity of the failed agent.
        self.agent_id = agent_id

        # Save the round at the moment the failure happened.
        self.round_number = state.current_round

        # Keep the partial history and inboxes available to the caller.
        self.state = state

        # Initialize the normal exception message.
        super().__init__(
            f"Agent '{agent_id}' failed during round "
            f"{self.round_number}. The discussion stopped."
        )    





class DiscussionOrchestrator:
    def __init__(self, agents: dict[str, Agent], router: GraphRouter,
                 checkpoint: Callable[[DiscussionState], None] | None = None) -> None:
        graph_agent_ids = set(router.graph.graph.nodes)
        provided_agent_ids = set(agents)

        if provided_agent_ids != graph_agent_ids:
            missing_agents = graph_agent_ids - provided_agent_ids
            extra_agents = provided_agent_ids - graph_agent_ids

            raise ValueError(
                "Agents must match the discussion graph. "
                f"Missing agents: {sorted(missing_agents)}. "
                f"Extra agents: {sorted(extra_agents)}."
            )

        self.agents = dict(agents)
        self.router = router
        self.checkpoint = checkpoint



    def _run_agent(
        self,
        agent_id: str,
        task: str,
        state: DiscussionState,
        received_messages: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Run one agent and attach discussion context if it fails."""
        try:
            agent = self.agents[agent_id]
            # None means initialization; even an empty list means a debate turn.
            if received_messages is None:
                return agent.run(task)
            return agent.run_discussion_turn(
                task=task,
                received_messages=received_messages,
            )
        except (Exception, KeyboardInterrupt) as error:
            state.failed_turns.append({
                "agent_id": agent_id,
                "round_num": state.current_round,
                "error_type": type(error).__name__,
                "error": str(error),
                "tool_events": [asdict(call) for call in getattr(error, "tool_calls", [])],
            })
            raise DiscussionRunError(
                agent_id=agent_id,
                state=state,
            ) from error






    def initialize_discussion(
        self,
        topic: str,
        total_rounds: int = 3,
        discussion_id: str | None = None,
    ) -> DiscussionState:
        """Create a new discussion state and collect each agent's initial opinion.

        ``discussion_id`` pins the run's identifier (Requirement 4.8) so a
        run can be named deterministically, e.g. by a reviewer script.
        When omitted, the state generates a fresh UUID.
        """
        state = DiscussionState(
            topic=topic,
            agent_ids=list(self.agents),
            total_rounds=total_rounds,
            **({"discussion_id": discussion_id} if discussion_id else {}),
        )

        for agent_id in state.agent_ids:
            print(f"  -> Initial opinion: {agent_id}...", flush=True)
            task = (
                f"Discussion topic: {state.topic}\n\n"
                "Give your initial opinion from your persona's perspective.\n"
                "State a clear, assertive stance and provide evidence-based reasoning.\n"
                "CRITICAL: Base your position strictly on concrete match facts, rules, and tactical realities. "
                "Do NOT invent fictional match timelines, scores, or referee calls. "
                "Do NOT confabulate tracking metrics, exact distance measurements (e.g. meter gaps), or unverified statistics. "
                "Use the `web_search` or `knowledge_search` tool if you need to verify specific match details.\n"
                "Provide your response in this format:\n"
                "STANCE: Your position on the topic.\n"
                "REASONING: Explain your position using available evidence and match insights.\n"
                "SOURCES USED: Identify the sources you relied on."
            )

            response = self._run_agent(
                agent_id=agent_id,
                task=task,
                state=state,
            )
            recipients = self.router.get_recipients(agent_id)

            message = DiscussionMessage(
                round_number=state.current_round,
                sender_id=agent_id,
                recipient_ids=recipients,
                content=response.content,
                sources=response.sources,
                tool_calls=response.tool_calls,
            )

            state.record_and_queue(message)
            if self.checkpoint:
                self.checkpoint(state)

        return state

    def run(
        self,
        topic: str,
        total_rounds: int = 3,
        discussion_id: str | None = None,
    ) -> DiscussionState:
        """Initialize the discussion and execute the configured rounds.

        ``discussion_id`` is forwarded to ``initialize_discussion``; see
        that method (Requirement 4.8).
        """
        print("\n--- Phase 1: Collecting Initial Opinions ---", flush=True)
        state = self.initialize_discussion(
            topic=topic,
            total_rounds=total_rounds,
            discussion_id=discussion_id,
        )

        for _ in range(state.total_rounds):
            state.advance_round()
            print(f"\n--- Phase 2: Discussion Round {state.current_round} of {state.total_rounds} ---", flush=True)

            for agent_id in state.agent_ids:
                print(f"  -> Round {state.current_round} turn: {agent_id}...", flush=True)
                # Translate our message objects into the agent's input format.
                # The agent formats these messages for the LLM itself.
                received_messages = [
                    {"sender": message.sender_id, "content": message.content}
                    for message in state.inboxes[agent_id]
                ]

                is_final_round = (state.current_round == state.total_rounds)
                if is_final_round:
                    round_instruction = (
                        "This is the FINAL round of the studio debate. Deliver your definitive, conclusive closing verdict.\n"
                        "- Provide a fresh, comprehensive synthesis summarizing the core conflict of the debate and your final judgment.\n"
                        "- Address unresolved points of friction directly (e.g. the procedural validity of the VAR review vs. the perception of momentum disruption).\n"
                        "- CRITICAL ANTI-REPETITION MANDATE: Do NOT copy, re-emit, or recycle paragraphs or phrases from your earlier turns. Any recycled text will be automatically rejected. Deliver a completely fresh conclusive closing argument.\n"
                        "- CRITICAL ANTI-HALLUCINATION & METRIC GROUNDING: Base your conclusive synthesis strictly on verified match facts and reports.\n"
                        "- CRITICAL: Avoid sycophancy, cheerleading, and filler praise ('It is refreshing to see consensus', 'I agree with my esteemed colleagues'). Focus 100% on analytical substance."
                    )
                else:
                    round_instruction = (
                        "Directly cross-examine the arguments you received from other analysts by name.\n"
                        "- ACTIVE FACT-CHECKING & SEARCH: If an analyst raises claims about referee bias, controversial decisions, "
                        "disallowed goals, VAR reviews, or disputed match statistics, invoke `web_search` or `knowledge_search` to look up verified reporting before answering.\n"
                        "- If an analyst presented concrete match facts or data (e.g. scorelines, penalties, match timeline), "
                        "you MUST directly address and reconcile those facts with your thesis.\n"
                        "- If an opposing analyst's premise contradicts established match events, directly challenge their contradiction with retrieved evidence.\n"
                        "- CRITICAL ANTI-HALLUCINATION & METRIC GROUNDING: Do NOT invent, confabulate, or extrapolate ungrounded numerical metrics, spatial measurements (e.g. '4.2 meters between lines', exact physical distances), or pseudo-statistical formulas not in your sources. "
                        "If a colleague introduces an ungrounded metric or numerical claim lacking source attribution, do NOT adopt it as fact or treat it as a 'smoking gun'; challenge its empirical validity and source.\n"
                        "- CRITICAL: Do NOT use conversational filler, pleasantries, or mutual congratulations "
                        "('I agree with my esteemed colleague', 'It is refreshing to see such a consensus'). "
                        "Jump immediately into substantive critique and evidence.\n"
                        "- CRITICAL: Do NOT repeat paragraphs from your previous turns or recycle boilerplate text. "
                        "Advance a new, deeper argument or interrogate a specific counter-point in every round.\n"
                        "- Explain clearly whether you maintain, adapt, or revise your position."
                    )

                task = (
                    f"Discussion topic: {state.topic}\n"
                    f"Round: {state.current_round} of {state.total_rounds}\n\n"
                    f"{round_instruction}\n\n"
                    "If you need to verify claims, call `web_search` or `knowledge_search` first. "
                    "When ready, provide your response in this format:\n"
                    "STANCE: Your current position (clearly state if you maintain, adapt, or shift).\n"
                    "REASONING: Address the specific received arguments and evidence from other analysts.\n"
                    "SOURCES USED: Identify the sources you relied on."
                )

                response = self._run_agent(
                    agent_id=agent_id,
                    task=task,
                    state=state,
                    received_messages=received_messages,
                )
                recipients = self.router.get_recipients(agent_id)

                message = DiscussionMessage(
                    round_number=state.current_round,
                    sender_id=agent_id,
                    recipient_ids=recipients,
                    content=response.content,
                    sources=response.sources,
                    tool_calls=response.tool_calls,
                )

                state.record_and_queue(message)
                if self.checkpoint:
                    self.checkpoint(state)

        return state
