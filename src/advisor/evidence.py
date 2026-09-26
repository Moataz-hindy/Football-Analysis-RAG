# Replace the contents of src/advisor/evidence.py with this file.
"""Load discussion messages and their attached evidence for the analyst."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AwareDatetime, Field, model_validator

from src.advisor.models import (
    AnalystRequest,
    EvidenceItem,
    SnapshotHash,
    StrictModel,
    ResearchTrace,
)
from src.api.services.discussion_service import get_saved_discussion
from src.discussion.types import DiscussionResult


class MessageRecord(StrictModel):
    """One message from the saved discussion."""

    message_ref: str
    original_message_id: str | None = None
    round_num: int
    sender_id: str
    recipient_ids: list[str]
    content: str
    timestamp: AwareDatetime | None = None
    source_ids: list[str] = Field(default_factory=list)


# NEW: retain the metadata field that supplied a publication time.
# This is a recorded time, not independent verification of publication.
class PublicationRecord(StrictModel):
    message_ref: str | None
    metadata_field: str
    raw_value: str
    parsed_at: AwareDatetime


class EvidenceBundle(StrictModel):
    """Evidence built from one completed discussion snapshot."""

    request: AnalystRequest
    discussion_topic: str
    snapshot_sha256: SnapshotHash

    messages: list[MessageRecord]
    evidence: list[EvidenceItem]

    # One excerpt can have several message mentions.
    source_mentions: dict[str, list[str]] = Field(
        default_factory=dict
    )

    # CHANGED: keys are canonical source identities where available.
    # Different excerpts from one document appear in the same group.
    source_groups: dict[str, list[str]] = Field(
        default_factory=dict
    )

    # NEW: keep the original source names and recorded date provenance.
    source_aliases: dict[str, list[str]] = Field(
        default_factory=dict
    )
    source_publications: dict[
        str, list[PublicationRecord]
    ] = Field(default_factory=dict)

    # CHANGED: these describe different questions.
    has_sources: bool = False
    has_time_eligible_sources: bool | None = None

    excluded_message_count: int = 0
    excluded_source_count: int = 0
    missing_information: list[str] = Field(default_factory=list)
    research: ResearchTrace | None = None

    @model_validator(mode="after")
    def check_registry(self):
        message_refs = [m.message_ref for m in self.messages]
        evidence_ids = [item.id for item in self.evidence]

        if len(message_refs) != len(set(message_refs)):
            raise ValueError("Message references must be unique.")

        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence IDs must be unique.")

        messages_by_ref = {
            message.message_ref: message
            for message in self.messages
        }
        known_sources = {
            item.id
            for item in self.evidence
            if item.kind == "source"
        }

        for item in self.evidence:
            if item.message_ref is not None and item.message_ref not in messages_by_ref:
                raise ValueError(
                    f"Evidence {item.id} has an unknown message reference."
                )

        for message in self.messages:
            for source_id in message.source_ids:
                if source_id not in known_sources:
                    raise ValueError(
                        f"Message {message.message_ref} has "
                        f"an unknown source ID: {source_id}"
                    )

                if message.message_ref not in self.source_mentions.get(
                    source_id, []
                ):
                    raise ValueError(
                        f"Source {source_id} is missing a message mention."
                    )

        for source_id, mentions in self.source_mentions.items():
            if source_id not in known_sources:
                raise ValueError(f"Unknown source ID: {source_id}")

            for message_ref in mentions:
                message = messages_by_ref.get(message_ref)
                if (
                    message is None
                    or source_id not in message.source_ids
                ):
                    raise ValueError(
                        f"Invalid mention of {source_id} by "
                        f"{message_ref}."
                    )

        grouped_ids = [
            source_id
            for ids in self.source_groups.values()
            for source_id in ids
        ]

        if (
            set(grouped_ids) != known_sources
            or len(grouped_ids) != len(set(grouped_ids))
        ):
            raise ValueError(
                "Each source must occur in exactly one source group."
            )

        if set(self.source_aliases) != known_sources:
            raise ValueError(
                "Each source must preserve its original source name."
            )

        for source_id, aliases in self.source_aliases.items():
            if not aliases or not all(alias.strip() for alias in aliases):
                raise ValueError(
                    f"Source {source_id} has invalid source aliases."
                )

        for source_id, records in self.source_publications.items():
            if source_id not in known_sources:
                raise ValueError(
                    f"Unknown publication source ID: {source_id}"
                )

            for record in records:
                if record.message_ref is None:
                    item = next(item for item in self.evidence if item.id == source_id)
                    if item.origin == "discussion":
                        raise ValueError("Attached source publication must identify its message.")
                    continue
                if record.message_ref not in self.source_mentions[
                    source_id
                ]:
                    raise ValueError(
                        f"Publication record for {source_id} has "
                        "an unrelated message reference."
                    )

        if self.has_sources != bool(known_sources):
            raise ValueError(
                "has_sources does not match the evidence registry."
            )

        if self.request.mode == "match_preview":
            cutoff = self.request.evidence_cutoff

            for message in self.messages:
                if (
                    message.timestamp is None
                    or message.timestamp > cutoff
                ):
                    raise ValueError(
                        "A preview contains a message outside "
                        "its evidence cutoff."
                    )

            for item in self.evidence:
                if item.kind == "source" and (
                    item.published_at is None
                    or item.published_at > cutoff
                ):
                    raise ValueError(
                        "A preview contains a source outside "
                        "its evidence cutoff."
                    )

            if self.has_time_eligible_sources != bool(known_sources):
                raise ValueError(
                    "Preview source eligibility does not match "
                    "the evidence registry."
                )
        elif self.has_time_eligible_sources is not None:
            raise ValueError(
                "Time eligibility is only assessed for previews."
            )

        return self


def _aware_timestamp(value: Any) -> datetime | None:
    """Accept only timestamps with an explicit timezone."""

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(
                value.strip().replace("Z", "+00:00")
            )
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None

    return parsed.astimezone(timezone.utc)


def _recorded_publication(
    metadata: Any,
    message_ref: str,
) -> PublicationRecord | None:
    """Read only fields explicitly described as publication dates."""

    if not isinstance(metadata, dict):
        return None

    # CHANGED: generic metadata["date"] is deliberately excluded.
    for field_name in (
        "published_at",
        "publication_time",
        "publication_date",
        "published_date",
    ):
        raw_value = metadata.get(field_name)
        parsed = _aware_timestamp(raw_value)

        if parsed is not None:
            return PublicationRecord(
                message_ref=message_ref,
                metadata_field=field_name,
                raw_value=str(raw_value),
                parsed_at=parsed,
            )

    return None


def _canonical_url(value: str) -> str | None:
    """Normalize an article URL and remove common tracking parameters."""

    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return None

    if (
        parts.scheme.lower() not in {"http", "https"}
        or not parts.netloc
    ):
        return None

    tracking_parameters = {
        "fbclid",
        "gclid",
        "igshid",
        "mc_cid",
        "mc_eid",
    }

    query_items = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if (
            not key.casefold().startswith("utm_")
            and key.casefold() not in tracking_parameters
        )
    ]

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            urlencode(sorted(query_items)),
            "",
        )
    )


def _source_identity(
    source_name: str,
    metadata: Any,
) -> str:
    """Choose a stable document identity where one is available."""

    details = metadata if isinstance(metadata, dict) else {}

    canonical_candidate = details.get("canonical_url")
    if isinstance(canonical_candidate, str):
        canonical = _canonical_url(canonical_candidate)
        if canonical:
            return f"url:{canonical}"

    canonical = _canonical_url(source_name)
    if canonical:
        return f"url:{canonical}"

    document_id = details.get("doc_id")
    if document_id is not None and str(document_id).strip():
        return f"doc:{str(document_id).strip()}"

    return f"label:{source_name.strip()}"


def _source_key(
    identity: str,
    content: str,
) -> tuple[str, str]:
    """Combine repeat retrievals of the same document excerpt."""

    normalized_content = re.sub(r"\s+", " ", content).strip()
    content_hash = hashlib.sha256(
        normalized_content.encode("utf-8")
    ).hexdigest()

    return identity, content_hash


def _snapshot_hash(discussion: DiscussionResult) -> str:
    """Bind references and future reports to discussion content."""

    serialized = json.dumps(
        discussion.to_dict(),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def build_evidence_bundle(
    request: AnalystRequest,
    discussion: DiscussionResult,
) -> EvidenceBundle:
    """Build the evidence registry from the saved discussion."""

    if discussion.config.discussion_id != request.discussion_id:
        raise ValueError(
            "Discussion ID does not match the request."
        )

    metadata = discussion.config.metadata or {}
    status = metadata.get("status")

    if status and status != "completed":
        raise ValueError(
            f"Discussion is not completed; saved status is {status!r}."
        )

    is_preview = request.mode == "match_preview"
    cutoff = (
        request.evidence_cutoff.astimezone(timezone.utc)
        if is_preview and request.evidence_cutoff is not None
        else None
    )

    messages: list[MessageRecord] = []
    evidence: list[EvidenceItem] = []

    source_mentions: dict[str, list[str]] = {}
    source_groups: dict[str, list[str]] = {}
    source_aliases: dict[str, list[str]] = {}
    source_publications: dict[
        str, list[PublicationRecord]
    ] = {}

    source_ids_by_key: dict[tuple[str, str], str] = {}

    excluded_messages = 0
    excluded_sources = 0
    skipped_sources = 0

    for index, message in enumerate(
        discussion.messages,
        start=1,
    ):
        message_ref = f"M{index:03d}"
        message_time = _aware_timestamp(message.timestamp)

        if cutoff is not None and (
            message_time is None
            or message_time > cutoff
        ):
            excluded_messages += 1
            continue

        message_metadata = (
            message.metadata
            if isinstance(message.metadata, dict)
            else {}
        )
        original_id = str(
            message_metadata.get("message_id") or ""
        ).strip() or None

        content = (message.content or "").strip()

        if content:
            # This records what the agent said. Its factual claims
            # still need to be assessed by the analyst.
            evidence.append(
                EvidenceItem(
                    id=message_ref,
                    kind="message",
                    message_ref=message_ref,
                    excerpt=content,
                )
            )

        attached_source_ids: list[str] = []

        for source in message.sources_used:
            source_metadata = (
                source.metadata
                if isinstance(source.metadata, dict)
                else {}
            )
            source_name = str(
                source.source
                or source_metadata.get("canonical_url")
                or ""
            ).strip()
            source_content = str(
                source.content or ""
            ).strip()

            if (
                not source_name
                or source_name.casefold() == "unknown"
                or not source_content
            ):
                skipped_sources += 1
                continue

            publication = _recorded_publication(
                source_metadata,
                message_ref,
            )

            if cutoff is not None and (
                publication is None
                or publication.parsed_at > cutoff
            ):
                # Existing records without publication metadata remain
                # unavailable as dated evidence for predictions.
                excluded_sources += 1
                continue

            identity = _source_identity(
                source_name,
                source_metadata,
            )
            key = _source_key(
                identity,
                source_content,
            )
            source_id = source_ids_by_key.get(key)

            if source_id is None:
                source_id = (
                    f"S{len(source_ids_by_key) + 1:03d}"
                )
                source_ids_by_key[key] = source_id

                evidence.append(
                    EvidenceItem(
                        id=source_id,
                        kind="source",
                        message_ref=message_ref,
                        excerpt=source_content,
                        source=source_name,
                        published_at=(
                            publication.parsed_at
                            if publication is not None
                            else None
                        ),
                    )
                )

                source_groups.setdefault(
                    identity, []
                ).append(source_id)

            mentions = source_mentions.setdefault(
                source_id, []
            )
            if message_ref not in mentions:
                mentions.append(message_ref)

            aliases = source_aliases.setdefault(
                source_id, []
            )
            if source_name not in aliases:
                aliases.append(source_name)

            if publication is not None:
                records = source_publications.setdefault(
                    source_id, []
                )
                if publication not in records:
                    records.append(publication)

            if source_id not in attached_source_ids:
                attached_source_ids.append(source_id)

        messages.append(
            MessageRecord(
                message_ref=message_ref,
                original_message_id=original_id,
                round_num=message.round_num,
                sender_id=message.sender_id,
                recipient_ids=list(
                    message.recipient_ids
                ),
                content=content,
                timestamp=message_time,
                source_ids=attached_source_ids,
            )
        )

    missing_information: list[str] = []

    if excluded_messages:
        missing_information.append(
            f"{excluded_messages} discussion messages were "
            "excluded because their timestamp was missing "
            "or after the evidence cutoff."
        )

    if excluded_sources:
        missing_information.append(
            f"{excluded_sources} source attachments from "
            "eligible messages were excluded because their "
            "recorded publication time was missing or after "
            "the evidence cutoff."
        )

    if skipped_sources:
        missing_information.append(
            f"{skipped_sources} source attachments had no "
            "usable source name or excerpt."
        )

    if not any(
        item.kind == "message"
        for item in evidence
    ):
        missing_information.append(
            "No eligible discussion messages contain text."
        )

    has_sources = any(
        item.kind == "source"
        for item in evidence
    )

    if is_preview and not has_sources:
        missing_information.append(
            "No attached source has a recorded publication "
            "timestamp before the preview cutoff."
        )

    return EvidenceBundle(
        request=request,
        discussion_topic=discussion.config.topic,
        snapshot_sha256=_snapshot_hash(discussion),
        messages=messages,
        evidence=evidence,
        source_mentions=source_mentions,
        source_groups=source_groups,
        source_aliases=source_aliases,
        source_publications=source_publications,
        has_sources=has_sources,

        # CHANGED: None means time eligibility was not assessed.
        has_time_eligible_sources=(
            has_sources if is_preview else None
        ),

        excluded_message_count=excluded_messages,
        excluded_source_count=excluded_sources,
        missing_information=missing_information,
    )


def load_discussion_evidence(
    request: AnalystRequest,
) -> EvidenceBundle:
    """Load a completed discussion and build its evidence registry."""

    discussion = get_saved_discussion(
        request.discussion_id
    )
    return build_evidence_bundle(
        request,
        discussion,
    )
