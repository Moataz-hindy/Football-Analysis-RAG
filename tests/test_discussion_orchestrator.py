"""Test discussion orchestration without calling an LLM or database."""

from src.agent.types import AgentResponse
from src.discussion.orchestrator import (
    DiscussionOrchestrator,
    DiscussionRunError,)
from src.discussion.router import GraphRouter


class FakeAgent:
    """Acts like an agent but returns predictable text."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

        # A separate list for this agent's received tasks.
        self.tasks: list[str] = []

    def run(self, task: str) -> AgentResponse:
        # Remember exactly what the orchestrator sent this agent.
        self.tasks.append(task)

        # Call 1 represents initialization: turn 0.
        # Call 2 represents Round 1: turn 1, and so on.
        turn_number = len(self.tasks) - 1

        # A unique marker lets us trace this response through later prompts.
        # AgentResponse supplies empty sources and tool_calls by default.
        return AgentResponse(
            content=f"[{self.agent_id}|turn={turn_number}]"
        )


def test_three_round_discussion() -> None:
    """Verify participation, routing, and message visibility."""
    router = GraphRouter()
    agent_ids = sorted(router.graph.graph.nodes)

    # Dictionary keys are graph IDs.
    # Dictionary values are separate FakeAgent objects.
    agents = {
        agent_id: FakeAgent(agent_id)
        for agent_id in agent_ids
    }

    orchestrator = DiscussionOrchestrator(
        agents=agents,
        router=router,
    )

    state = orchestrator.run(
        topic="Does defensive organization win matches?",
        total_rounds=3,
    )

    assert state.current_round == 3

    # Six initial opinions + three rounds of six responses.
    assert len(state.messages) == 24

    # Every agent receives one initialization task and three round tasks.
    for agent in agents.values():
        assert len(agent.tasks) == 4

    # range(4) produces 0, 1, 2, 3.
    # Round 0 represents initial opinions.
    for round_number in range(4):
        round_messages = [
            message
            for message in state.messages
            if message.round_number == round_number
        ]

        assert len(round_messages) == 6

        # Comparing sorted lists checks that every agent spoke once.
        assert sorted(
            message.sender_id for message in round_messages
        ) == agent_ids

    # Every recorded recipient list must match the router's decision.
    for message in state.messages:
        expected_recipients = router.get_recipients(
            message.sender_id
        )

        assert sorted(message.recipient_ids) == sorted(
            expected_recipients
        )

    # .items() gives us each dictionary key and its corresponding object.
    for agent_id, agent in agents.items():
        for round_number in range(1, 4):
            # tasks[0] is initialization; tasks[1] is Round 1, etc.
            task = agent.tasks[round_number]

            for message in state.messages:
                # The task should include this message only if it
                # belongs to the previous round AND targets this agent.
                should_receive = (
                    message.round_number == round_number - 1
                    and agent_id in message.recipient_ids
                )

                # For strings, "in" checks whether text is present.
                is_present = message.content in task

                assert is_present == should_receive, (
                    f"Incorrect message visibility for {agent_id} "
                    f"in round {round_number}: {message.content}"
                )

    print("Passed: six agents completed three discussion rounds.")
    print("Passed: recipients follow the graph.")
    print("Passed: agents received only their previous-round messages.")



class FailingAgent(FakeAgent):
    """Behaves normally until its Round 2 call."""

    def run(self, task: str) -> AgentResponse:
        # Before the third call, two tasks have been received:
        # initial opinion and Round 1.
        if len(self.tasks) == 2:
            raise RuntimeError("Simulated model connection failure.")

        # Otherwise, use the normal fake-agent behavior.
        return super().run(task)



def test_agent_failure_preserves_partial_state() -> None:
    router = GraphRouter()
    agent_ids = sorted(router.graph.graph.nodes)

    agents = {
        agent_id: FakeAgent(agent_id)
        for agent_id in agent_ids
    }

    # Make the first scheduled agent fail during Round 2.
    failing_id = agent_ids[0]
    agents[failing_id] = FailingAgent(failing_id)

    orchestrator = DiscussionOrchestrator(
        agents=agents,
        router=router,
    )

    try:
        orchestrator.run(
            topic="Does defensive organization win matches?",
            total_rounds=3,
        )
    except DiscussionRunError as error:
        assert error.agent_id == failing_id
        assert error.round_number == 2

        # Six initial opinions + six Round 1 responses.
        assert len(error.state.messages) == 12

        assert {
            message.round_number
            for message in error.state.messages
        } == {0, 1}

        assert isinstance(error.__cause__, RuntimeError)
        assert str(error.__cause__) == (
            "Simulated model connection failure."
        )

        # NEW: Display the details of the expected failure.
        print(f"Simulated failed agent: {error.agent_id}")
        print(f"Failed during round: {error.round_number}")
        print(f"Original cause: {error.__cause__}")
        print(f"Messages preserved: {len(error.state.messages)}")
    else:
        raise AssertionError("The agent failure was not reported.")

    print("Passed: agent failure stops the run and preserves partial state.")






def test_configured_round_count() -> None:
    """Verify that the round count is configurable."""
    router = GraphRouter()
    agent_ids = sorted(router.graph.graph.nodes)

    # Use fresh fake agents so their task histories start empty.
    agents = {
        agent_id: FakeAgent(agent_id)
        for agent_id in agent_ids
    }

    orchestrator = DiscussionOrchestrator(
        agents=agents,
        router=router,
    )

    # Four rounds check that the implementation is not hardcoded to three.
    state = orchestrator.run(
        topic="Does defensive organization win matches?",
        total_rounds=4,
    )

    assert state.current_round == 4

    # Six agents × (one initial opinion + four rounds).
    assert len(state.messages) == 30

    for agent in agents.values():
        assert len(agent.tasks) == 5

    # Ensure the recorded phases are exactly initialization and rounds 1–4.
    assert {
        message.round_number for message in state.messages
    } == {0, 1, 2, 3, 4}

    print("Passed: the discussion stops at the configured round count.")


def test_missing_agent_is_rejected() -> None:
    """Verify that the agent dictionary matches the graph."""
    router = GraphRouter()
    agent_ids = sorted(router.graph.graph.nodes)

    agents = {
        agent_id: FakeAgent(agent_id)
        for agent_id in agent_ids
    }

    # Fan remains in the graph, but its executable agent is now missing.
    del agents["fan_analyst"]

    try:
        DiscussionOrchestrator(
            agents=agents,
            router=router,
        )
    except ValueError as error:
        # An exception is expected for this deliberately invalid setup.
        assert "fan_analyst" in str(error)
    else:
        # The else block executes only if the try block raised no exception.
        raise AssertionError("The orchestrator accepted a missing agent.")

    print("Passed: a missing graph participant is rejected.")


# Running this file as a module executes all three test functions.
if __name__ == "__main__":
    test_three_round_discussion()
    test_configured_round_count()
    test_missing_agent_is_rejected()
    test_agent_failure_preserves_partial_state()