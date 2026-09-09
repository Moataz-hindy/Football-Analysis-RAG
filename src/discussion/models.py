"""Message and state models for the Week 3 discussion engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from src.agent.types import RetrievedSource, ToolCall

@dataclass 
class DiscussionMessage:
    """One agent response and its intended recipients."""

    round_number: int
    sender_id: str
    recipient_ids: list[str]
    content: str

    message_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    sources: list[RetrievedSource] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)

@dataclass
class DiscussionState:
    """The discussion history and messages available in each round."""
    
    topic:str
    agent_ids: list[str]
    total_rounds: int = 3

    discussion_id: str = field(default_factory=lambda: str(uuid4()))
    current_round: int = field(default=0, init=False)

    messages: list[DiscussionMessage] = field(default_factory=list, init=False)

    inboxes: dict[str, list[DiscussionMessage]] = field(default_factory=dict, init=False)

    next_inboxes: dict[str, list[DiscussionMessage]] = field(default_factory=dict, init=False
    )

    def __post_init__(self):
        """Validate configuration and create an inbox for each agent."""
        if not self.topic.strip():
            raise ValueError("Discussion topic cannot be empty.")

        if self.total_rounds < 3:
            raise ValueError("Total rounds must be at least 3.")

        if len(self.agent_ids) < 2:
            raise ValueError("At least two agents are required for a discussion.")

        if any(not agent_id.strip() for agent_id in self.agent_ids):
            raise ValueError("Agent IDs cannot be empty.")
        if len(set(self.agent_ids)) != len(self.agent_ids):
            raise ValueError("Agent IDs must be unique.")

        self.agent_ids = list(sorted(self.agent_ids))
        self.inboxes = {agent_id: [] for agent_id in self.agent_ids}
        self.next_inboxes = {agent_id: [] for agent_id in self.agent_ids}


    def record_and_queue(self, message:DiscussionMessage) -> None:
        """Save a message and queue it for its recipients' next round."""
        if message.round_number != self.current_round:
            raise ValueError("Message round number does not match current round")

        if message.sender_id not in self.inboxes:
            raise ValueError(f"Unknown sender: {message.sender_id}")

        for recipient_id in message.recipient_ids:
            if recipient_id not in self.next_inboxes:
                raise ValueError(f"Unknown recipient: {recipient_id}")

        if len(set(message.recipient_ids)) != len(message.recipient_ids):
            raise ValueError("A message cannot contain duplicate recipients.")

        self.messages.append(message)

        for recipient_id in message.recipient_ids:
            self.next_inboxes[recipient_id].append(message)

    def advance_round(self) -> None:
        """Make queued messages available and begin the next round."""
        if self.current_round >= self.total_rounds:
            raise ValueError("Cannot advance beyond the configured rounds.")

        self.inboxes = self.next_inboxes
        self.next_inboxes = {
            agent_id: [] for agent_id in self.agent_ids
        }
        self.current_round += 1