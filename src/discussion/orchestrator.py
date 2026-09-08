"""Coordinates the agents participating in a discussion."""

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
    def __init__(self, agents: dict[str, Agent], router: GraphRouter) -> None:
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



    def _run_agent(
        self,
        agent_id: str,
        task: str,
        state: DiscussionState,
    ) -> AgentResponse:
        """Run one agent and attach discussion context if it fails."""
        try:
            return self.agents[agent_id].run(task)
        except Exception as error:
            raise DiscussionRunError(
                agent_id=agent_id,
                state=state,
            ) from error






    def initialize_discussion(
        self,
        topic: str,
        total_rounds: int = 3,
    ) -> DiscussionState:
        """Create a new discussion state and collect each agent's initial opinion."""
        state = DiscussionState(
            topic=topic,
            agent_ids=list(self.agents),
            total_rounds=total_rounds,
        )

        for agent_id in state.agent_ids:

            task = (
                f"Discussion topic: {state.topic}\n\n"
                "Give your initial opinion from your persona's perspective.\n"
                "Use this format:\n"
                "STANCE: Your position on the topic.\n"
                "REASONING: Explain your position using available evidence.\n"
                "SOURCES USED: Identify the sources you relied on.\n"
                "If evidence is insufficient, say so. Do not invent sources."
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

        return state

    def run(
        self,
        topic: str,
        total_rounds: int = 3,
    ) -> DiscussionState:
        """Initialize the discussion and execute the configured rounds."""
        state = self.initialize_discussion(
            topic=topic,
            total_rounds=total_rounds,
        )

        for _ in range(state.total_rounds):
            state.advance_round()

            for agent_id in state.agent_ids:
                received_messages = state.inboxes[agent_id]

                received_text = "\n\n".join(
                    f"From: {message.sender_id}\n"
                    f"Message: {message.content}"
                    for message in received_messages
                )

                if not received_text:
                    received_text = "No messages received for this round"

                task = (
                    f"Discussion topic: {state.topic}\n"
                    f"Round: {state.current_round} of {state.total_rounds}\n\n"
                    f"Messages received:\n{received_text}\n\n"
                    "Respond to the arguments you received from your persona's perspective. "
                    "Treat other agents' claims as discussion input, not verified evidence.\n"
                    "Explain whether you maintain or revise your position and why. "
                    "Use available knowledge and tools when useful. Do not invent evidence or sources.\n"
                    "Use this format:\n"
                    "STANCE: Your current position.\n"
                    "REASONING: Address the received arguments and explain your position using available evidence.\n"
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

        return state