"""Persistent Long-Term Profile Memory Service & Agent Memory Adapter.

Provides durable memory storage for profile-level facts and preferences,
distinguishing explicit user settings from inferred patterns, and seamlessly
linking into the agent execution pipeline.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from src.agent.interfaces import MemoryInterface
from src.agent.memory import ConversationMemory
from src.platform.db import get_db_cursor
from src.platform.models import MemoryCreate, MemoryOut

logger = logging.getLogger(__name__)


class ProfileMemoryService:
    """Service for managing long-term profile facts and preferences."""

    @staticmethod
    def get_memories(
        profile_id: str,
        memory_type: Optional[str] = None,
    ) -> list[MemoryOut]:
        """Fetch all persistent memories belonging to a profile."""
        with get_db_cursor() as cur:
            if memory_type:
                cur.execute(
                    "SELECT * FROM profile_memory WHERE profile_id = ? AND memory_type = ? ORDER BY created_at DESC",
                    (profile_id, memory_type),
                )
            else:
                cur.execute(
                    "SELECT * FROM profile_memory WHERE profile_id = ? ORDER BY created_at DESC",
                    (profile_id,),
                )
            rows = cur.fetchall()
            return [
                MemoryOut(
                    id=r["id"],
                    profile_id=r["profile_id"],
                    memory_type=r["memory_type"],
                    key=r["key"],
                    value=r["value"],
                    source=r["source"],
                    confidence=float(r["confidence"] or 1.0),
                    created_at=str(r["created_at"]),
                    updated_at=str(r["updated_at"]),
                )
                for r in rows
            ]

    @staticmethod
    def add_memory(
        profile_id: str,
        memory_type: str,
        key: str,
        value: str,
        source: str = "explicit",
        confidence: float = 1.0,
    ) -> MemoryOut:
        """Add a persistent memory item for a profile."""
        mem_id = f"mem-{uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()

        with get_db_cursor() as cur:
            # Check if key already exists for this profile; update if source is explicit
            cur.execute(
                "SELECT id, source FROM profile_memory WHERE profile_id = ? AND key = ?",
                (profile_id, key.strip()),
            )
            existing = cur.fetchone()
            if existing:
                e_id = existing["id"]
                e_source = existing["source"]
                # Inferred memories cannot overwrite explicit user memory
                if e_source == "explicit" and source == "inferred":
                    logger.info("Ignoring inferred memory update over explicit user key '%s'", key)
                    return ProfileMemoryService.get_memory_by_id(profile_id, e_id)

                cur.execute(
                    """UPDATE profile_memory
                       SET value = ?, source = ?, confidence = ?, updated_at = ?
                       WHERE id = ?""",
                    (value.strip(), source, confidence, now_str, e_id),
                )
                mem_id = e_id
            else:
                cur.execute(
                    """INSERT INTO profile_memory (id, profile_id, memory_type, key, value, source, confidence, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (mem_id, profile_id, memory_type.strip(), key.strip(), value.strip(), source, confidence, now_str, now_str),
                )

        return ProfileMemoryService.get_memory_by_id(profile_id, mem_id)

    @staticmethod
    def get_memory_by_id(profile_id: str, memory_id: str) -> Optional[MemoryOut]:
        """Fetch a specific memory item ensuring ownership."""
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM profile_memory WHERE id = ? AND profile_id = ?",
                (memory_id, profile_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return MemoryOut(
                id=row["id"],
                profile_id=row["profile_id"],
                memory_type=row["memory_type"],
                key=row["key"],
                value=row["value"],
                source=row["source"],
                confidence=float(row["confidence"] or 1.0),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )

    @staticmethod
    def delete_memory(profile_id: str, memory_id: str) -> bool:
        """Delete a memory item belonging to the specified profile."""
        with get_db_cursor() as cur:
            cur.execute(
                "DELETE FROM profile_memory WHERE id = ? AND profile_id = ?",
                (memory_id, profile_id),
            )
            return cur.rowcount > 0

    @staticmethod
    def get_relevant_memories(
        profile_id: str,
        query: str = "",
        limit: int = 6,
    ) -> list[MemoryOut]:
        """Retrieve relevant memories matching query terms or high-priority explicit keys."""
        all_mems = ProfileMemoryService.get_memories(profile_id)
        if not all_mems:
            return []

        if not query.strip():
            # Return most confident explicit memories first
            return sorted(all_mems, key=lambda m: (1 if m.source == "explicit" else 0, m.confidence), reverse=True)[:limit]

        query_tokens = set(query.lower().split())

        def score_memory(m: MemoryOut) -> float:
            score = 0.0
            if m.source == "explicit":
                score += 2.0
            score += m.confidence
            text = f"{m.key} {m.value}".lower()
            matches = sum(1 for t in query_tokens if t in text)
            score += matches * 1.5
            return score

        scored = sorted(all_mems, key=score_memory, reverse=True)
        return scored[:limit]

    @staticmethod
    def get_profile_context(profile_id: str, query: str = "") -> str:
        """Produce formatted context string for LLM injection."""
        memories = ProfileMemoryService.get_relevant_memories(profile_id, query=query, limit=5)
        if not memories:
            return ""

        lines = ["### PERSISTENT USER MEMORY & PREFERENCES"]
        for m in memories:
            prefix = "[Explicit Preference]" if m.source == "explicit" else "[Observed Pattern]"
            lines.append(f"- {prefix} {m.key}: {m.value}")
        return "\n".join(lines)


class ProfileAwareMemory(MemoryInterface):
    """Adapter combining persistent Profile Memory with ConversationMemory sliding window.

    Satisfies the existing Agent `MemoryInterface` seamlessly while enabling
    cross-session durable profile awareness.
    """

    def __init__(
        self,
        profile_id: Optional[str] = None,
        short_term: Optional[ConversationMemory] = None,
        max_turns: int = 5,
        llm=None,
    ):
        self.profile_id = profile_id
        self.short_term = short_term or ConversationMemory(max_turns=max_turns, llm=llm)

    def add(self, data: Any) -> None:
        """Record turn in short-term conversation memory and optionally infer preferences."""
        self.short_term.add(data)

    def get_context(self) -> str:
        """Combine persistent profile memory and short-term dialogue context."""
        parts = []

        # 1. Long-term persistent memory
        if self.profile_id:
            profile_ctx = ProfileMemoryService.get_profile_context(self.profile_id)
            if profile_ctx:
                parts.append(profile_ctx)

        # 2. Short-term dialogue context
        st_ctx = self.short_term.get_context()
        if st_ctx:
            parts.append(st_ctx)

        return "\n\n".join(parts) if parts else ""
