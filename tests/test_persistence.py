import json
import logging
from pathlib import Path
from uuid import uuid4

import pytest

from src.agent.types import RetrievedSource
from src.discussion import (
    DiscussionConfig,
    DiscussionMessage,
    DiscussionMetadata,
    DiscussionResult,
    OpinionSnapshot,
    RetrievalEvent,
    list_discussions,
    load_discussion,
    save_discussion,
)


@pytest.fixture
def sample_discussion() -> DiscussionResult:
    """Fixture providing a complete, realistic DiscussionResult object."""
    disc_id = str(uuid4())
    config = DiscussionConfig(
        discussion_id=disc_id,
        topic="Evaluate the tactical effectiveness of Japan's low block against Spain in the 2022 World Cup",
        num_rounds=3,
        agent_ids=["Tactical Analyst", "Statistical Analyst"],
        graph={
            "Tactical Analyst": ["Statistical Analyst"],
            "Statistical Analyst": ["Tactical Analyst"],
        },
        llm_model="openai/gpt-oss-20b",
        llm_temperature=0.2,
        timestamp="2026-09-07T14:00:00Z",
        metadata={"session_env": "test"},
    )

    msg1 = DiscussionMessage(
        round_num=1,
        sender_id="Tactical Analyst",
        recipient_ids=["Statistical Analyst"],
        content="Japan used a 5-4-1 mid-to-low block effectively restricting central spaces.",
        timestamp="2026-09-07T14:01:00Z",
        sources_used=[
            RetrievedSource(
                content="Japan maintained 17.7% possession against Spain, the lowest in World Cup history for a winning team.",
                source="https://theanalyst.com/2022/12/japan-spain-world-cup",
                score=0.92,
                metadata={"category": "stats"},
            )
        ],
        retrieval_events=[
            RetrievalEvent(
                query="Japan low block Spain possession stats",
                num_results=1,
                timestamp="2026-09-07T14:00:45Z",
                metadata={"engine": "vector"},
            )
        ],
    )

    msg2 = DiscussionMessage(
        round_num=1,
        sender_id="Statistical Analyst",
        recipient_ids=["Tactical Analyst"],
        content="Spain's xG was limited to 1.05 despite over 1000 passes, proving Japan's defensive efficiency.",
        timestamp="2026-09-07T14:02:00Z",
        sources_used=[],
        retrieval_events=[],
    )

    op0_tac = OpinionSnapshot(
        agent_id="Tactical Analyst",
        round_num=0,
        stance="Japan's low block was high-risk but structurally sound.",
        reasoning="Compact horizontal spacing denied central progression for Spain's midfield.",
        sources_used="",
        raw_text="Initial thought on tactical structure.",
        timestamp="2026-09-07T14:00:05Z",
    )

    op1_tac = OpinionSnapshot(
        agent_id="Tactical Analyst",
        round_num=1,
        stance="Confirmed effectiveness: Spain generated very low dangerous passes.",
        reasoning="Transition moments punished Spain's high defensive line.",
        sources_used="1",
        raw_text="Round 1 updated analysis.",
        timestamp="2026-09-07T14:02:10Z",
    )

    meta = DiscussionMetadata(
        duration_seconds=125.4,
        total_messages=2,
        total_retrieval_events=1,
        errors=[],
        extra={"run_mode": "automated_eval"},
    )

    return DiscussionResult(
        config=config,
        messages=[msg1, msg2],
        opinions=[op0_tac, op1_tac],
        metadata=meta,
    )


def test_save_creates_json_file(tmp_path: Path, sample_discussion: DiscussionResult):
    file_path = save_discussion(sample_discussion, output_dir=tmp_path)
    path_obj = Path(file_path)

    assert path_obj.exists()
    assert path_obj.is_file()
    assert path_obj.suffix == ".json"


def test_discussion_id_in_filename(tmp_path: Path, sample_discussion: DiscussionResult):
    file_path = save_discussion(sample_discussion, output_dir=tmp_path)
    expected_filename = f"{sample_discussion.config.discussion_id}.json"
    assert Path(file_path).name == expected_filename


def test_save_produces_valid_json(tmp_path: Path, sample_discussion: DiscussionResult):
    file_path = save_discussion(sample_discussion, output_dir=tmp_path)
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    assert "config" in data
    assert "messages" in data
    assert "opinions" in data
    assert "metadata" in data


def test_load_reconstructs_all_fields(tmp_path: Path, sample_discussion: DiscussionResult):
    file_path = save_discussion(sample_discussion, output_dir=tmp_path)
    loaded = load_discussion(file_path)

    # Validate Config
    assert loaded.config.discussion_id == sample_discussion.config.discussion_id
    assert loaded.config.topic == sample_discussion.config.topic
    assert loaded.config.num_rounds == sample_discussion.config.num_rounds
    assert loaded.config.agent_ids == sample_discussion.config.agent_ids
    assert loaded.config.graph == sample_discussion.config.graph
    assert loaded.config.llm_model == sample_discussion.config.llm_model
    assert loaded.config.llm_temperature == sample_discussion.config.llm_temperature
    assert loaded.config.timestamp == sample_discussion.config.timestamp
    assert loaded.config.metadata == sample_discussion.config.metadata

    # Validate Messages
    assert len(loaded.messages) == len(sample_discussion.messages)
    for orig, rec in zip(sample_discussion.messages, loaded.messages):
        assert orig.round_num == rec.round_num
        assert orig.sender_id == rec.sender_id
        assert orig.recipient_ids == rec.recipient_ids
        assert orig.content == rec.content
        assert orig.timestamp == rec.timestamp
        assert len(orig.sources_used) == len(rec.sources_used)
        if orig.sources_used:
            assert orig.sources_used[0].content == rec.sources_used[0].content
            assert orig.sources_used[0].score == rec.sources_used[0].score
        assert len(orig.retrieval_events) == len(rec.retrieval_events)
        if orig.retrieval_events:
            assert orig.retrieval_events[0].query == rec.retrieval_events[0].query
            assert orig.retrieval_events[0].num_results == rec.retrieval_events[0].num_results

    # Validate Opinions
    assert len(loaded.opinions) == len(sample_discussion.opinions)
    for orig_op, rec_op in zip(sample_discussion.opinions, loaded.opinions):
        assert orig_op.agent_id == rec_op.agent_id
        assert orig_op.round_num == rec_op.round_num
        assert orig_op.stance == rec_op.stance
        assert orig_op.reasoning == rec_op.reasoning
        assert orig_op.sources_used == rec_op.sources_used

    # Validate Metadata
    assert loaded.metadata.duration_seconds == sample_discussion.metadata.duration_seconds
    assert loaded.metadata.total_messages == sample_discussion.metadata.total_messages
    assert loaded.metadata.total_retrieval_events == sample_discussion.metadata.total_retrieval_events
    assert loaded.metadata.errors == sample_discussion.metadata.errors
    assert loaded.metadata.extra == sample_discussion.metadata.extra


def test_messages_preserved_in_order(tmp_path: Path, sample_discussion: DiscussionResult):
    file_path = save_discussion(sample_discussion, output_dir=tmp_path)
    loaded = load_discussion(file_path)

    senders = [m.sender_id for m in loaded.messages]
    assert senders == ["Tactical Analyst", "Statistical Analyst"]


def test_retrieval_events_preserved(tmp_path: Path, sample_discussion: DiscussionResult):
    file_path = save_discussion(sample_discussion, output_dir=tmp_path)
    loaded = load_discussion(file_path)

    has_retrieval = any(len(m.retrieval_events) > 0 for m in loaded.messages)
    assert has_retrieval
    first_event = loaded.messages[0].retrieval_events[0]
    assert first_event.query == "Japan low block Spain possession stats"
    assert first_event.num_results == 1


def test_two_saves_produce_different_files(tmp_path: Path, sample_discussion: DiscussionResult):
    file1 = save_discussion(sample_discussion, output_dir=tmp_path)

    disc2 = DiscussionResult(
        config=DiscussionConfig(
            discussion_id=str(uuid4()),
            topic="Topic 2",
            num_rounds=2,
            agent_ids=["Agent A"],
            graph={"Agent A": []},
            llm_model="test-model",
            llm_temperature=0.0,
        ),
        messages=[],
        opinions=[],
    )
    file2 = save_discussion(disc2, output_dir=tmp_path)

    assert file1 != file2
    assert Path(file1).exists()
    assert Path(file2).exists()


def test_load_nonexistent_raises(tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError) as exc_info:
        load_discussion(nonexistent)
    assert "Discussion file not found" in str(exc_info.value)


def test_load_invalid_json_raises(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.json"
    with open(corrupt_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json syntax ...")

    with pytest.raises(ValueError) as exc_info:
        load_discussion(corrupt_file)
    assert "Invalid JSON" in str(exc_info.value)


def test_load_missing_required_config_raises(tmp_path: Path):
    bad_data_file = tmp_path / "bad_schema.json"
    with open(bad_data_file, "w", encoding="utf-8") as f:
        json.dump({"messages": [], "opinions": []}, f)

    with pytest.raises(ValueError) as exc_info:
        load_discussion(bad_data_file)
    assert "Missing required key 'config'" in str(exc_info.value)


def test_output_dir_created_if_missing(tmp_path: Path, sample_discussion: DiscussionResult):
    nested_dir = tmp_path / "deeply" / "nested" / "output_dir"
    assert not nested_dir.exists()

    file_path = save_discussion(sample_discussion, output_dir=nested_dir)
    assert nested_dir.exists()
    assert Path(file_path).exists()


def test_save_with_dict_input(tmp_path: Path):
    disc_id = str(uuid4())
    raw_dict = {
        "config": {
            "discussion_id": disc_id,
            "topic": "Dict input test",
            "num_rounds": 1,
            "agent_ids": ["Analyst A"],
            "graph": {"Analyst A": []},
            "llm_model": "gpt-4",
            "llm_temperature": 0.5,
            "timestamp": "2026-09-07T12:00:00Z",
        },
        "messages": [
            {
                "round_num": 1,
                "sender_id": "Analyst A",
                "recipient_ids": [],
                "content": "Testing dict input.",
                "timestamp": "2026-09-07T12:01:00Z",
                "sources_used": [],
                "retrieval_events": [],
            }
        ],
        "opinions": [],
        "metadata": {
            "duration_seconds": 10.0,
            "total_messages": 1,
            "total_retrieval_events": 0,
            "errors": [],
        },
    }

    file_path = save_discussion(raw_dict, output_dir=tmp_path)
    assert Path(file_path).name == f"{disc_id}.json"

    loaded = load_discussion(file_path)
    assert loaded.config.discussion_id == disc_id
    assert loaded.config.topic == "Dict input test"
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "Testing dict input."


def test_missing_discussion_id_raises(tmp_path: Path):
    bad_dict = {
        "config": {
            "topic": "No ID here",
        }
    }
    with pytest.raises(ValueError) as exc_info:
        save_discussion(bad_dict, output_dir=tmp_path)
    assert "discussion_id" in str(exc_info.value).lower()


def test_list_empty_dir_returns_empty(tmp_path: Path):
    res = list_discussions(output_dir=tmp_path)
    assert res == []


def test_list_nonexistent_dir_returns_empty(tmp_path: Path):
    nonexistent = tmp_path / "not_created"
    res = list_discussions(output_dir=nonexistent)
    assert res == []


def test_list_discussions_finds_files_and_sorts(tmp_path: Path, sample_discussion: DiscussionResult):
    save_discussion(sample_discussion, output_dir=tmp_path)

    # Add second discussion with newer timestamp
    disc2 = DiscussionResult(
        config=DiscussionConfig(
            discussion_id="disc_newer",
            topic="Newer discussion",
            num_rounds=2,
            agent_ids=["Agent 1", "Agent 2", "Agent 3"],
            graph={},
            llm_model="model-x",
            llm_temperature=0.7,
            timestamp="2026-09-07T15:00:00Z",
        ),
        messages=[],
        opinions=[],
    )
    save_discussion(disc2, output_dir=tmp_path)

    # Add a corrupt file to verify resilience
    corrupt = tmp_path / "broken.json"
    with open(corrupt, "w", encoding="utf-8") as f:
        f.write("{ not valid json")

    summaries = list_discussions(output_dir=tmp_path)
    assert len(summaries) == 2

    # Should be sorted newest timestamp first
    assert summaries[0]["discussion_id"] == "disc_newer"
    assert summaries[0]["num_agents"] == 3
    assert summaries[0]["topic"] == "Newer discussion"

    assert summaries[1]["discussion_id"] == sample_discussion.config.discussion_id
    assert summaries[1]["num_agents"] == 2


def test_logging_recorded(caplog: pytest.LogCaptureFixture, tmp_path: Path, sample_discussion: DiscussionResult):
    with caplog.at_level(logging.INFO):
        file_path = save_discussion(sample_discussion, output_dir=tmp_path)
        load_discussion(file_path)
        list_discussions(output_dir=tmp_path)

    messages = [rec.message for rec in caplog.records]
    assert any("Saving discussion" in msg for msg in messages)
    assert any("saved to" in msg for msg in messages)
    assert any("Loading discussion from" in msg for msg in messages)
    assert any("Loaded discussion" in msg for msg in messages)
    assert any("Found 1 discussion(s)" in msg for msg in messages)


# ===========================================================================
# Integration tests: save_discussion_from_state (bridge)
# ===========================================================================

from src.discussion.models import DiscussionMessage as OrchestratorMessage
from src.discussion.models import DiscussionState
from src.discussion.graph import DiscussionGraph
from src.discussion.router import GraphRouter
from src.discussion.persistence import save_discussion_from_state, _extract_opinion
from src.agent.types import RetrievedSource as AgentRetrievedSource, ToolCall


@pytest.fixture
def mock_discussion_state() -> DiscussionState:
    """Create a DiscussionState that mimics what the orchestrator returns."""
    state = DiscussionState(
        topic="Should teams use high pressing in World Cup knockout rounds?",
        agent_ids=["context_analyst", "tactical_analyst"],
        total_rounds=3,
    )

    # Round 0 — initial opinions
    msg0a = OrchestratorMessage(
        round_number=0,
        sender_id="context_analyst",
        recipient_ids=["tactical_analyst"],
        content=(
            "STANCE: High pressing is risky in knockout rounds due to fatigue.\n"
            "REASONING: Teams playing extra time face 30 extra minutes, "
            "making sustained pressing unsustainable.\n"
            "SOURCES USED: None available."
        ),
        sources=[],
        tool_calls=[],
    )
    msg0b = OrchestratorMessage(
        round_number=0,
        sender_id="tactical_analyst",
        recipient_ids=["context_analyst"],
        content=(
            "STANCE: Selective high pressing is effective.\n"
            "REASONING: Pressing in the opponent's half forces turnovers "
            "near the goal. The key is pressing triggers, not constant pressure.\n"
            "SOURCES USED: Tactical analysis patterns."
        ),
        sources=[
            AgentRetrievedSource(
                content="High pressing teams won 67% of World Cup knockout matches since 2014.",
                source="https://example.com/pressing-stats",
                score=0.88,
            )
        ],
        tool_calls=[
            ToolCall(
                name="knowledge_search",
                arguments={"query": "high pressing World Cup knockout results"},
                result=[
                    {"content": "High pressing teams won 67%...", "source": "https://example.com/pressing-stats"}
                ],
            )
        ],
    )

    state.record_and_queue(msg0a)
    state.record_and_queue(msg0b)

    # Advance through 3 rounds with minimal messages
    for round_num in range(1, 4):
        state.advance_round()
        for agent_id in state.agent_ids:
            other = [a for a in state.agent_ids if a != agent_id]
            msg = OrchestratorMessage(
                round_number=round_num,
                sender_id=agent_id,
                recipient_ids=other,
                content=f"STANCE: Position updated after round {round_num}.\n"
                        f"REASONING: Considering new arguments.\n"
                        f"SOURCES USED: Discussion context.",
            )
            state.record_and_queue(msg)

    return state


def test_bridge_saves_valid_json(tmp_path: Path, mock_discussion_state: DiscussionState):
    path = save_discussion_from_state(
        state=mock_discussion_state,
        output_dir=tmp_path,
        llm_model="qwen-3.6",
        llm_temperature=0.2,
        duration_seconds=300.0,
    )
    assert Path(path).exists()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "config" in data
    assert "messages" in data
    assert "opinions" in data
    assert "metadata" in data


def test_bridge_config_fields(tmp_path: Path, mock_discussion_state: DiscussionState):
    path = save_discussion_from_state(
        state=mock_discussion_state,
        output_dir=tmp_path,
        llm_model="qwen-3.6",
        llm_temperature=0.2,
    )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = data["config"]
    assert config["discussion_id"] == mock_discussion_state.discussion_id
    assert config["topic"] == mock_discussion_state.topic
    assert config["num_rounds"] == mock_discussion_state.total_rounds
    assert set(config["agent_ids"]) == set(mock_discussion_state.agent_ids)
    assert config["llm_model"] == "qwen-3.6"
    assert config["llm_temperature"] == 0.2


def test_bridge_preserves_messages(tmp_path: Path, mock_discussion_state: DiscussionState):
    path = save_discussion_from_state(
        state=mock_discussion_state,
        output_dir=tmp_path,
    )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data["messages"]
    # 2 initial (round 0) + 2 per round × 3 rounds = 8 total
    assert len(messages) == 8

    # Check field name mapping: round_number → round_num
    assert all("round_num" in m for m in messages)
    assert all("sender_id" in m for m in messages)
    assert all("recipient_ids" in m for m in messages)
    assert all("content" in m for m in messages)
    assert all("sources_used" in m for m in messages)
    assert all("retrieval_events" in m for m in messages)


def test_bridge_converts_sources(tmp_path: Path, mock_discussion_state: DiscussionState):
    path = save_discussion_from_state(
        state=mock_discussion_state,
        output_dir=tmp_path,
    )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # tactical_analyst's round 0 message had a source
    tactical_msgs = [m for m in data["messages"]
                     if m["sender_id"] == "tactical_analyst" and m["round_num"] == 0]
    assert len(tactical_msgs) == 1
    msg = tactical_msgs[0]
    assert len(msg["sources_used"]) == 1
    assert msg["sources_used"][0]["score"] == 0.88
    assert "pressing" in msg["sources_used"][0]["content"].lower()


def test_bridge_converts_tool_calls_to_retrieval_events(tmp_path: Path, mock_discussion_state: DiscussionState):
    path = save_discussion_from_state(
        state=mock_discussion_state,
        output_dir=tmp_path,
    )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tactical_msgs = [m for m in data["messages"]
                     if m["sender_id"] == "tactical_analyst" and m["round_num"] == 0]
    msg = tactical_msgs[0]
    assert len(msg["retrieval_events"]) == 1
    event = msg["retrieval_events"][0]
    assert "high pressing" in event["query"].lower()
    assert event["num_results"] == 1
    assert event["metadata"]["tool_name"] == "knowledge_search"


def test_bridge_extracts_opinions(tmp_path: Path, mock_discussion_state: DiscussionState):
    path = save_discussion_from_state(
        state=mock_discussion_state,
        output_dir=tmp_path,
    )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    opinions = data["opinions"]
    # One opinion per message = 8
    assert len(opinions) == 8

    # Check round 0 context_analyst opinion was parsed
    initial_opinion = [o for o in opinions
                       if o["agent_id"] == "context_analyst" and o["round_num"] == 0]
    assert len(initial_opinion) == 1
    op = initial_opinion[0]
    assert "risky" in op["stance"].lower() or "fatigue" in op["stance"].lower()
    assert op["raw_text"]  # Always preserved
    assert op["reasoning"]  # Should have been parsed


def test_bridge_with_graph_router(tmp_path: Path, mock_discussion_state: DiscussionState):
    router = GraphRouter()
    path = save_discussion_from_state(
        state=mock_discussion_state,
        router=router,
        output_dir=tmp_path,
    )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = data["config"]["graph"]
    assert isinstance(graph, dict)
    assert len(graph) > 0
    # All 6 personas from the DiscussionGraph should be keys
    assert "tactical_analyst" in graph
    assert "context_analyst" in graph
    # Check edges exist
    assert len(graph["tactical_analyst"]) > 0


def test_bridge_roundtrip_with_load(tmp_path: Path, mock_discussion_state: DiscussionState):
    """Save via bridge, then load — verify the roundtrip works."""
    path = save_discussion_from_state(
        state=mock_discussion_state,
        output_dir=tmp_path,
        llm_model="qwen-3.6",
        duration_seconds=120.5,
    )

    loaded = load_discussion(path)
    assert loaded.config.discussion_id == mock_discussion_state.discussion_id
    assert loaded.config.topic == mock_discussion_state.topic
    assert len(loaded.messages) == 8
    assert len(loaded.opinions) == 8
    assert loaded.metadata.duration_seconds == 120.5
    assert loaded.metadata.total_messages == 8


def test_bridge_metadata(tmp_path: Path, mock_discussion_state: DiscussionState):
    path = save_discussion_from_state(
        state=mock_discussion_state,
        output_dir=tmp_path,
        duration_seconds=250.0,
        errors=["Rate limit hit on round 2"],
    )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]
    assert meta["duration_seconds"] == 250.0
    assert meta["total_messages"] == 8
    assert "Rate limit hit on round 2" in meta["errors"]


def test_extract_opinion_parser():
    """Test the opinion extraction regex directly."""
    content = (
        "STANCE: Japan's low block was effective.\n"
        "REASONING: They limited Spain's xG to 1.05 despite low possession.\n"
        "SOURCES USED: Match statistics from theanalyst.com"
    )
    result = _extract_opinion(content)
    assert "effective" in result["stance"].lower()
    assert "xG" in result["reasoning"] or "1.05" in result["reasoning"]
    assert "theanalyst" in result["sources_used"].lower()
    assert result["raw_text"] == content


def test_extract_opinion_missing_markers():
    """When agent doesn't follow format, raw_text is still preserved."""
    content = "I think high pressing works best in the first 15 minutes."
    result = _extract_opinion(content)
    assert result["raw_text"] == content
    # Stance/reasoning may be empty if markers aren't found
    assert isinstance(result["stance"], str)
    assert isinstance(result["reasoning"], str)
