"""Focused tests for Requirement 4.7 — Opinion Evolution.

Verifies that opinion history (initial opinion, per-round opinions, change
detection, change reason, and final opinion) is tracked as structured data
via `OpinionSnapshot` / `build_opinion_history`, and that it integrates with
the existing discussion rounds and persistence mechanism.
"""

import json
from pathlib import Path

import pytest

from src.discussion import OpinionSnapshot, load_discussion, save_discussion_from_state
from src.discussion.models import DiscussionMessage as OrchestratorMessage
from src.discussion.models import DiscussionState
from src.discussion.persistence import build_opinion_history


def _stance_message(round_number: int, sender_id: str, recipients: list[str], stance: str, reasoning: str) -> OrchestratorMessage:
    return OrchestratorMessage(
        round_number=round_number,
        sender_id=sender_id,
        recipient_ids=recipients,
        content=f"STANCE: {stance}\nREASONING: {reasoning}\nSOURCES USED: None.",
    )


@pytest.fixture
def two_agent_state() -> DiscussionState:
    """A discussion where one agent flips their stance and one doesn't, over 3 rounds."""
    state = DiscussionState(
        topic="Should teams use high pressing in knockout rounds?",
        agent_ids=["tactical_analyst", "statistical_analyst"],
        total_rounds=3,
    )

    # Round 0 — initial opinions.
    state.record_and_queue(_stance_message(
        0, "tactical_analyst", ["statistical_analyst"],
        "High pressing is effective.", "It forces turnovers high up the pitch.",
    ))
    state.record_and_queue(_stance_message(
        0, "statistical_analyst", ["tactical_analyst"],
        "High pressing is too risky.", "Fatigue data shows a drop-off after 60 minutes.",
    ))

    # Round 1 — tactical_analyst holds firm, statistical_analyst is swayed.
    state.advance_round()
    state.record_and_queue(_stance_message(
        1, "tactical_analyst", ["statistical_analyst"],
        "High pressing is effective.", "The opposing argument doesn't change the tactical logic.",
    ))
    state.record_and_queue(_stance_message(
        1, "statistical_analyst", ["tactical_analyst"],
        "High pressing can be effective in short bursts.",
        "Turnover data near the opposition box changed my view on selective pressing.",
    ))

    # Round 2 — both hold their round-1 stance.
    state.advance_round()
    state.record_and_queue(_stance_message(
        2, "tactical_analyst", ["statistical_analyst"],
        "High pressing is effective.", "Still no compelling counter-evidence.",
    ))
    state.record_and_queue(_stance_message(
        2, "statistical_analyst", ["tactical_analyst"],
        "High pressing can be effective in short bursts.",
        "The sample size supports selective pressing over blanket pressing.",
    ))

    # Round 3 — tactical_analyst finally shifts too.
    state.advance_round()
    state.record_and_queue(_stance_message(
        3, "tactical_analyst", ["statistical_analyst"],
        "Selective high pressing is the best approach.",
        "The statistical evidence for bursts over sustained pressing is convincing.",
    ))
    state.record_and_queue(_stance_message(
        3, "statistical_analyst", ["tactical_analyst"],
        "High pressing can be effective in short bursts.",
        "No new evidence changes this.",
    ))

    return state


def test_initial_opinion_is_stored(two_agent_state: DiscussionState):
    """1. Initial opinion (round 0) is captured for every agent."""
    history = build_opinion_history(two_agent_state)

    initial_snapshots = [o for o in history if o["round_num"] == 0]
    agent_ids = {o["agent_id"] for o in initial_snapshots}

    assert agent_ids == {"tactical_analyst", "statistical_analyst"}
    tactical_initial = next(o for o in initial_snapshots if o["agent_id"] == "tactical_analyst")
    assert "effective" in tactical_initial["stance"].lower()
    # Round 0 has no prior round to compare against.
    assert tactical_initial["changed_from_previous"] is False
    assert tactical_initial["change_reason"] == ""


def test_opinions_stored_for_multiple_rounds(two_agent_state: DiscussionState):
    """2. An opinion snapshot exists for every configured round, for every agent."""
    history = build_opinion_history(two_agent_state)

    rounds_for_tactical = sorted(o["round_num"] for o in history if o["agent_id"] == "tactical_analyst")
    rounds_for_statistical = sorted(o["round_num"] for o in history if o["agent_id"] == "statistical_analyst")

    # total_rounds=3 → rounds 0 (initial) through 3.
    assert rounds_for_tactical == [0, 1, 2, 3]
    assert rounds_for_statistical == [0, 1, 2, 3]


def test_unchanged_opinion_not_marked_changed(two_agent_state: DiscussionState):
    """3. Repeating the same stance from the previous round is not flagged as a change."""
    history = build_opinion_history(two_agent_state)

    # tactical_analyst repeats the same stance in round 2 as round 1.
    round2 = next(
        o for o in history if o["agent_id"] == "tactical_analyst" and o["round_num"] == 2
    )
    assert round2["changed_from_previous"] is False
    assert round2["change_reason"] == ""


def test_changed_opinion_is_detected(two_agent_state: DiscussionState):
    """4. A genuine stance change is flagged, with a reason drawn from the agent's reasoning."""
    history = build_opinion_history(two_agent_state)

    # statistical_analyst shifts stance between round 0 and round 1.
    round1 = next(
        o for o in history if o["agent_id"] == "statistical_analyst" and o["round_num"] == 1
    )
    assert round1["changed_from_previous"] is True
    assert round1["change_reason"]  # non-empty, best-effort reason
    assert "turnover" in round1["change_reason"].lower()

    # tactical_analyst only shifts at round 3.
    tactical_rounds = {
        o["round_num"]: o for o in history if o["agent_id"] == "tactical_analyst"
    }
    assert tactical_rounds[1]["changed_from_previous"] is False
    assert tactical_rounds[3]["changed_from_previous"] is True
    assert tactical_rounds[3]["change_reason"]


def test_multiple_agents_have_independent_histories(two_agent_state: DiscussionState):
    """5. Each agent's changed_from_previous / stance sequence is independent of the other's."""
    history = build_opinion_history(two_agent_state)

    tactical_changes = [
        o["changed_from_previous"]
        for o in sorted(
            [x for x in history if x["agent_id"] == "tactical_analyst"],
            key=lambda x: x["round_num"],
        )
    ]
    statistical_changes = [
        o["changed_from_previous"]
        for o in sorted(
            [x for x in history if x["agent_id"] == "statistical_analyst"],
            key=lambda x: x["round_num"],
        )
    ]

    # tactical_analyst changes only at round 3; statistical_analyst changes at round 1.
    assert tactical_changes == [False, False, False, True]
    assert statistical_changes == [False, True, False, False]
    assert tactical_changes != statistical_changes


def test_opinion_history_persists_and_reloads(tmp_path: Path, two_agent_state: DiscussionState):
    """6. Opinion history is serialized/persisted using the existing persistence mechanism."""
    path = save_discussion_from_state(
        state=two_agent_state,
        output_dir=tmp_path,
        llm_model="test-model",
        llm_temperature=0.2,
    )

    # Raw JSON contains the structured opinion fields (not just message text).
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "opinions" in data
    assert len(data["opinions"]) == 8  # 2 agents x 4 snapshots (rounds 0-3)
    for snapshot in data["opinions"]:
        assert "changed_from_previous" in snapshot
        assert "change_reason" in snapshot

    # Round-trip through load_discussion reconstructs OpinionSnapshot objects.
    loaded = load_discussion(path)
    assert len(loaded.opinions) == 8
    assert all(isinstance(o, OpinionSnapshot) for o in loaded.opinions)

    reloaded_round1_stat = next(
        o for o in loaded.opinions
        if o.agent_id == "statistical_analyst" and o.round_num == 1
    )
    assert reloaded_round1_stat.changed_from_previous is True
    assert reloaded_round1_stat.change_reason
