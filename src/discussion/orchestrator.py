"""Coordinates the agents participating in a discussion."""

import time
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
    def __init__(
        self,
        agents: dict[str, Agent],
        router: GraphRouter,
        checkpoint: Callable[[DiscussionState], None] | None = None,
        camps: dict | None = None,
    ) -> None:
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
        self.camps = camps

    def _get_agent_camp_info(self, agent_id: str, state: DiscussionState) -> dict[str, str]:
        """Resolve camp assignment, perspective name, and opening mandate for an agent."""
        camps_data = self.camps
        if isinstance(camps_data, dict) and "camps" in camps_data and isinstance(camps_data["camps"], dict):
            camps_data = camps_data["camps"]

        camp_a = camps_data.get("camp_a", {}) if isinstance(camps_data, dict) else {}
        camp_b = camps_data.get("camp_b", {}) if isinstance(camps_data, dict) else {}

        # 1. Collect Camp A members
        a_members = set()
        if "ids" in camp_a and isinstance(camp_a["ids"], list):
            a_members.update(camp_a["ids"])
        for role in ("coach", "fan", "pundit"):
            if role in camp_a and camp_a[role]:
                a_members.add(camp_a[role])

        # 2. Collect Camp B members
        b_members = set()
        if "ids" in camp_b and isinstance(camp_b["ids"], list):
            b_members.update(camp_b["ids"])
        for role in ("coach", "fan", "pundit"):
            if role in camp_b and camp_b[role]:
                b_members.add(camp_b[role])

        camp_a_name = str(camp_a.get("name") or "Camp A (Affirmative / Thesis)").strip()
        camp_b_name = str(camp_b.get("name") or "Camp B (Counter / Antithesis)").strip()

        # Fallback if no explicit camps or agent not in explicit camps
        if agent_id not in a_members and agent_id not in b_members:
            agent_list = list(state.agent_ids)
            half = max(1, len(agent_list) // 2)
            if agent_id in agent_list[:half]:
                a_members.add(agent_id)
            else:
                b_members.add(agent_id)

            if " vs " in state.topic.lower():
                import re
                parts = re.split(r"\s+vs\.?\s+", state.topic, flags=re.IGNORECASE)
                if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                    camp_a_name = f"In favor of {parts[0].strip()}"
                    camp_b_name = f"In favor of {parts[1].strip()}"

        if agent_id in a_members:
            return {
                "camp_key": "camp_a",
                "camp_name": camp_a_name,
                "opposing_camp_name": camp_b_name,
                "camp_role": "affirmative",
            }
        else:
            return {
                "camp_key": "camp_b",
                "camp_name": camp_b_name,
                "opposing_camp_name": camp_a_name,
                "camp_role": "counter",
            }



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

    def _run_agent_with_retry(
        self,
        agent_id: str,
        task: str,
        state: DiscussionState,
        received_messages: list[dict[str, str]] | None = None,
        attempts: int = 3,
        backoff_seconds: float = 30.0,
    ) -> AgentResponse:
        """Retry a failed agent turn; one transient provider outage must not
        abort a multi-minute discussion run."""
        for attempt in range(attempts):
            try:
                return self._run_agent(
                    agent_id=agent_id, task=task, state=state,
                    received_messages=received_messages,
                )
            except DiscussionRunError:
                if attempt == attempts - 1:
                    raise
                wait = backoff_seconds * (attempt + 1)
                print(
                    f"  !! Turn failed for {agent_id} "
                    f"(provider error); retrying in {wait:.0f}s "
                    f"({attempt + 1}/{attempts - 1})...",
                    flush=True,
                )
                time.sleep(wait)






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

        # Persist the freshly created run immediately, before the first agent
        # turn. This makes the discussion retrievable (status "running", empty
        # message list) for the whole duration of the first LLM call instead of
        # only after the first agent finishes.
        if self.checkpoint:
            self.checkpoint(state)

        for agent_id in state.agent_ids:
            print(f"  -> Initial opinion: {agent_id}...", flush=True)
            camp_info = self._get_agent_camp_info(agent_id, state)
            camp_name = camp_info["camp_name"]
            opposing_name = camp_info["opposing_camp_name"]
            is_camp_a = (camp_info["camp_role"] == "affirmative")

            if is_camp_a:
                camp_mandate = (
                    f"=== INITIAL OPENING LEAN: {camp_name.upper()} (CAMP A) ===\n"
                    f"You enter this debate with a natural initial lean toward Camp A: \"{camp_name}\".\n"
                    f"- In this opening round, articulate a reasoned, evidence-grounded opening perspective that highlights the merits of \"{camp_name}\" through your persona's distinctive tactical, analytical, or supporter lens.\n"
                    f"- State a clear initial lean (a reasoned, non-dogmatic position, e.g. +0.6 to +0.8) while acknowledging the complexity of the match.\n"
                    f"- Maintain intellectual agility: you are not locked into this view permanently. You are expected to evaluate counter-arguments and calibrate or adjust your position across rounds if peers present verified match data or compelling points."
                )
            else:
                camp_mandate = (
                    f"=== INITIAL OPENING LEAN: {camp_name.upper()} (CAMP B) ===\n"
                    f"You enter this debate with a natural initial lean toward Camp B: \"{camp_name}\".\n"
                    f"- In this opening round, articulate a reasoned, evidence-grounded opening perspective that highlights the merits of \"{camp_name}\" through your persona's distinctive tactical, analytical, or supporter lens.\n"
                    f"- State a clear initial lean (a reasoned, non-dogmatic counter-position, e.g. -0.6 to -0.8), contrasting against the opposing premise of \"{opposing_name}\" without adopting rigid dogmatism.\n"
                    f"- Maintain intellectual agility: you are not locked into this view permanently. You are expected to evaluate counter-arguments and calibrate or adjust your position across rounds if peers present verified match data or compelling points."
                )

            task = (
                f"Discussion topic: {state.topic}\n\n"
                f"{camp_mandate}\n\n"
                "Give your initial opening opinion from your persona's unique perspective, football philosophy, and priorities.\n"
                "State a clear, assertive stance and provide evidence-based reasoning.\n"
                "CRITICAL: Base your position strictly on concrete match facts, rules, and tactical realities. "
                "Do NOT invent fictional match timelines, scores, or referee calls. "
                "Do NOT confabulate tracking metrics, exact distance measurements (e.g. meter gaps), or unverified statistics. "
                "Use the `web_search` or `knowledge_search` tool if you need to verify specific match details.\n"
                "Provide your response in this format:\n"
                "STANCE: Your opening position on the topic.\n"
                "REASONING: Explain your position using available evidence, match insights, and your persona's analytical lens.\n"
                "SOURCES USED: Identify the sources you relied on."
            )

            response = self._run_agent_with_retry(
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
                sentiment_score=getattr(response, "sentiment_score", None),
                sentiment_label=getattr(response, "sentiment_label", None),
            )

            state.record_and_queue(message)
            if self.checkpoint:
                self.checkpoint(state)
            time.sleep(1.0)
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
                        "- DIALECTICAL STANCE CALIBRATION: Engage genuinely with peer evidence. If an opponent highlighted valid match data (e.g. goals conceded, errors, transition moments), "
                        "calibrate your stance to reflect nuance or dual tactical attribution rather than obstinately repeating 'Maintain'."
                    )

                task = (
                    f"Discussion topic: {state.topic}\n"
                    f"Round: {state.current_round} of {state.total_rounds}\n\n"
                    f"{round_instruction}\n\n"
                    "Acknowledge verified peer evidence that changes your reasoning, and explain any concession or calibrated view. "
                    "Do not change your view merely to produce superficial agreement, but reflect genuine analytical nuance.\n"
                    "If you need to verify claims, call `web_search` or `knowledge_search` first. "
                    "When ready, provide your response in this format:\n"
                    "STANCE: State your calibrated stance on the debate question (note your core position and any nuanced adjustment or concession in light of peer arguments).\n"
                    "REASONING: Address the specific received arguments and evidence from other analysts.\n"
                    "SOURCES USED: Identify the sources you relied on."
                )

                response = self._run_agent_with_retry(
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
                    sentiment_score=getattr(response, "sentiment_score", None),
                    sentiment_label=getattr(response, "sentiment_label", None),
                )

                state.record_and_queue(message)
                if self.checkpoint:
                    self.checkpoint(state)
                time.sleep(1.0)
        return state
