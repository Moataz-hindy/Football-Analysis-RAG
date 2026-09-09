from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.agent.types import RetrievedSource


@dataclass
class RetrievalEvent:
    """
    Records an explicit retrieval action taken by an agent during discussion.
    """

    query: str
    num_results: int
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "num_results": self.num_results,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RetrievalEvent":
        return cls(
            query=data.get("query", ""),
            num_results=data.get("num_results", 0),
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DiscussionConfig:
    """
    Configuration and execution parameters for a multi-agent discussion run.
    """

    discussion_id: str
    topic: str
    num_rounds: int
    agent_ids: list[str]
    graph: dict[str, list[str]]
    llm_model: str
    llm_temperature: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "discussion_id": self.discussion_id,
            "topic": self.topic,
            "num_rounds": self.num_rounds,
            "agent_ids": list(self.agent_ids),
            "graph": {k: list(v) for k, v in self.graph.items()},
            "llm_model": self.llm_model,
            "llm_temperature": self.llm_temperature,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiscussionConfig":
        return cls(
            discussion_id=data["discussion_id"],
            topic=data["topic"],
            num_rounds=data.get("num_rounds", 3),
            agent_ids=data.get("agent_ids", []),
            graph=data.get("graph", {}),
            llm_model=data.get("llm_model", ""),
            llm_temperature=data.get("llm_temperature", 0.0),
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DiscussionMessage:
    """
    A single message sent by an agent during a discussion round.
    """

    round_num: int
    sender_id: str
    recipient_ids: list[str]
    content: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sources_used: list[RetrievedSource] = field(default_factory=list)
    retrieval_events: list[RetrievalEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        serialized_sources = []
        for s in self.sources_used:
            if isinstance(s, RetrievedSource):
                serialized_sources.append(
                    {
                        "content": s.content,
                        "source": s.source,
                        "score": s.score,
                        "metadata": s.metadata,
                    }
                )
            elif isinstance(s, dict):
                serialized_sources.append(s)
            else:
                serialized_sources.append(asdict(s))

        serialized_retrievals = []
        for r in self.retrieval_events:
            if isinstance(r, RetrievalEvent):
                serialized_retrievals.append(r.to_dict())
            elif isinstance(r, dict):
                serialized_retrievals.append(r)
            else:
                serialized_retrievals.append(asdict(r))

        return {
            "round_num": self.round_num,
            "sender_id": self.sender_id,
            "recipient_ids": list(self.recipient_ids),
            "content": self.content,
            "timestamp": self.timestamp,
            "sources_used": serialized_sources,
            "retrieval_events": serialized_retrievals,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiscussionMessage":
        sources = []
        for s in data.get("sources_used", []):
            if isinstance(s, dict):
                sources.append(
                    RetrievedSource(
                        content=s.get("content", ""),
                        source=s.get("source", ""),
                        score=s.get("score"),
                        metadata=s.get("metadata", {}),
                    )
                )
            elif isinstance(s, RetrievedSource):
                sources.append(s)

        retrievals = []
        for r in data.get("retrieval_events", []):
            if isinstance(r, dict):
                retrievals.append(RetrievalEvent.from_dict(r))
            elif isinstance(r, RetrievalEvent):
                retrievals.append(r)

        return cls(
            round_num=data.get("round_num", 0),
            sender_id=data.get("sender_id", ""),
            recipient_ids=data.get("recipient_ids", []),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
            sources_used=sources,
            retrieval_events=retrievals,
            metadata=data.get("metadata", {}),
        )


@dataclass
class OpinionSnapshot:
    """
    Snapshot of an agent's opinion/stance at round 0 (initial) or after round N.

    Requirement 4.7 (Opinion Evolution): in addition to the stance/reasoning
    captured for a single round, each snapshot records whether the stance
    changed relative to that same agent's previous snapshot, and (when it
    did) a short, best-effort reason for the change. Comparing consecutive
    snapshots for one `agent_id` across increasing `round_num` values yields
    that agent's full opinion history, from initial opinion (round_num == 0)
    to final opinion (the snapshot with the highest round_num).
    """

    agent_id: str
    round_num: int
    stance: str
    reasoning: str
    sources_used: str = ""
    raw_text: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    changed_from_previous: bool = False
    change_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "round_num": self.round_num,
            "stance": self.stance,
            "reasoning": self.reasoning,
            "sources_used": self.sources_used,
            "raw_text": self.raw_text,
            "timestamp": self.timestamp,
            "changed_from_previous": self.changed_from_previous,
            "change_reason": self.change_reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpinionSnapshot":
        return cls(
            agent_id=data.get("agent_id", ""),
            round_num=data.get("round_num", 0),
            stance=data.get("stance", ""),
            reasoning=data.get("reasoning", ""),
            sources_used=data.get("sources_used", ""),
            raw_text=data.get("raw_text", ""),
            timestamp=data.get("timestamp", ""),
            changed_from_previous=bool(data.get("changed_from_previous", False)),
            change_reason=data.get("change_reason", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DiscussionMetadata:
    """
    Aggregated operational metadata for the discussion execution.
    """

    duration_seconds: float = 0.0
    total_messages: int = 0
    total_retrieval_events: int = 0
    errors: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "duration_seconds": self.duration_seconds,
            "total_messages": self.total_messages,
            "total_retrieval_events": self.total_retrieval_events,
            "errors": list(self.errors),
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiscussionMetadata":
        return cls(
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            total_messages=int(data.get("total_messages", 0)),
            total_retrieval_events=int(data.get("total_retrieval_events", 0)),
            errors=list(data.get("errors", [])),
            extra=data.get("extra", {}),
        )


@dataclass
class DiscussionResult:
    """
    Complete persistent record of a multi-agent discussion.
    """

    config: DiscussionConfig
    messages: list[DiscussionMessage] = field(default_factory=list)
    opinions: list[OpinionSnapshot] = field(default_factory=list)
    metadata: DiscussionMetadata = field(default_factory=DiscussionMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict()
            if hasattr(self.config, "to_dict")
            else asdict(self.config),
            "messages": [
                m.to_dict() if hasattr(m, "to_dict") else asdict(m)
                for m in self.messages
            ],
            "opinions": [
                o.to_dict() if hasattr(o, "to_dict") else asdict(o)
                for o in self.opinions
            ],
            "metadata": self.metadata.to_dict()
            if hasattr(self.metadata, "to_dict")
            else asdict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiscussionResult":
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")

        if "config" not in data:
            raise ValueError("Missing required key 'config' in discussion data")

        config_data = data["config"]
        if not isinstance(config_data, dict):
            raise ValueError("'config' must be a dictionary")

        if "discussion_id" not in config_data or not config_data["discussion_id"]:
            raise ValueError("Missing or empty 'discussion_id' in config")

        if "topic" not in config_data:
            raise ValueError("Missing required key 'topic' in config")

        config = DiscussionConfig.from_dict(config_data)

        messages = [
            DiscussionMessage.from_dict(m) if isinstance(m, dict) else m
            for m in data.get("messages", [])
        ]

        opinions = [
            OpinionSnapshot.from_dict(o) if isinstance(o, dict) else o
            for o in data.get("opinions", [])
        ]

        metadata_dict = data.get("metadata", {})
        metadata = (
            DiscussionMetadata.from_dict(metadata_dict)
            if isinstance(metadata_dict, dict)
            else DiscussionMetadata()
        )

        return cls(
            config=config,
            messages=messages,
            opinions=opinions,
            metadata=metadata,
        )
