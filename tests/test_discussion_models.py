from src.discussion.models import DiscussionMessage, DiscussionState


def test_message_delivery_between_rounds():
    state = DiscussionState(
        topic="Does defensive organization win matches?",
        agent_ids=[
            "context_analyst",
            "fan_analyst",
            "performance_analyst",
            "refereeing_analyst",
            "statistical_analyst",
            "tactical_analyst",
        ],
        total_rounds=3,
    )

    # Create an initial opinion before the discussion rounds begin.
    message = DiscussionMessage(
        round_number=0,
        sender_id="tactical_analyst",
        recipient_ids=["performance_analyst", "fan_analyst"],
        content="A compact defense limits the opponent's chances.",
    )

    # Record it and place it in the recipients' waiting inboxes.
    state.record_and_queue(message)

    assert state.messages == [message]
    assert state.inboxes["fan_analyst"] == []
    assert state.next_inboxes["fan_analyst"] == [message]
    assert state.next_inboxes["performance_analyst"] == [message]
    assert state.next_inboxes["statistical_analyst"] == []

    # Begin Round 1: initial opinions become available to read.
    state.advance_round()

    assert state.current_round == 1
    assert state.inboxes["fan_analyst"] == [message]
    assert state.inboxes["performance_analyst"] == [message]
    assert state.next_inboxes["fan_analyst"] == []

    print("Passed: messages become available when the next round starts.")


if __name__ == "__main__":
    test_message_delivery_between_rounds()