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
