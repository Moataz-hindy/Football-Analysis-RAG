import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.discussion.types import DiscussionResult

logger = logging.getLogger(__name__)


def save_discussion(
    result: DiscussionResult | dict[str, Any],
    output_dir: str | Path = "outputs",
) -> str:
    """
    Persist a completed discussion result to a JSON file.

    Parameters:
    -----------
    result: DiscussionResult or dict
        The completed discussion record to persist.
    output_dir: str or Path
        Directory where the discussion JSON file will be saved.
        Defaults to 'outputs'.

    Returns:
    --------
    str: Absolute or normalized path to the saved JSON file.

    Raises:
    -------
    ValueError: If required fields (e.g. discussion_id) are missing.
    IOError / OSError: If saving to disk fails.
    """
    output_path = Path(output_dir)

    # Convert to dict representation
    if isinstance(result, DiscussionResult):
        data = result.to_dict()
    elif isinstance(result, dict):
        data = result
    else:
        raise ValueError(
            f"Expected DiscussionResult or dict, got {type(result).__name__}"
        )

    config = data.get("config")
    if not isinstance(config, dict):
        raise ValueError("Missing or invalid 'config' section in discussion data")

    discussion_id = config.get("discussion_id")
    if not discussion_id or not str(discussion_id).strip():
        raise ValueError("Discussion 'discussion_id' must be a non-empty string")

    discussion_id = str(discussion_id).strip()
    num_messages = len(data.get("messages", []))
    num_agents = len(config.get("agent_ids", []))

    logger.info(
        "Saving discussion %s (%d messages, %d agents)...",
        discussion_id,
        num_messages,
        num_agents,
    )

    file_path = output_path / f"{discussion_id}.json"
    temp_file_path = output_path / f".{discussion_id}.tmp.{uuid4().hex}"

    try:
        output_path.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file then rename
        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        os.replace(temp_file_path, file_path)

        file_size = os.path.getsize(file_path)
        logger.info(
            "Discussion %s saved to %s (%d bytes)",
            discussion_id,
            file_path,
            file_size,
        )
        return str(file_path)

    except Exception as e:
        logger.error(
            "Failed to save discussion %s: %s",
            discussion_id,
            e,
            exc_info=True,
        )
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except OSError:
                pass
        raise


def load_discussion(path: str | Path) -> DiscussionResult:
    """
    Load and reconstruct a DiscussionResult from a persisted JSON file.

    Parameters:
    -----------
    path: str or Path
        Path to the JSON discussion file.

    Returns:
    --------
    DiscussionResult: Fully reconstructed discussion result object.

    Raises:
    -------
    FileNotFoundError: If the specified file does not exist.
    ValueError: If file content is invalid JSON or violates required schema.
    """
    file_path = Path(path)
    logger.info("Loading discussion from %s...", file_path)

    if not file_path.is_file():
        err_msg = f"Discussion file not found: {file_path}"
        logger.error("Failed to load %s: %s", file_path, err_msg)
        raise FileNotFoundError(err_msg)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        err_msg = f"Invalid JSON in {file_path}: {e}"
        logger.error("Failed to load %s: %s", file_path, err_msg)
        raise ValueError(err_msg) from e
    except Exception as e:
        logger.error("Failed to load %s: %s", file_path, e, exc_info=True)
        raise

    if not isinstance(data, dict):
        err_msg = f"Root of discussion file must be a JSON object, got {type(data).__name__}"
        logger.error("Failed to load %s: %s", file_path, err_msg)
        raise ValueError(err_msg)

    # Optional fields validation with warnings
    discussion_id = data.get("config", {}).get("discussion_id", "unknown")
    if "metadata" not in data:
        logger.warning(
            "Discussion %s: missing optional field 'metadata', defaulting to empty",
            discussion_id,
        )

    for idx, msg in enumerate(data.get("messages", [])):
        if isinstance(msg, dict) and "retrieval_events" not in msg:
            logger.warning(
                "Discussion %s: message index %d missing optional field 'retrieval_events', defaulting to empty",
                discussion_id,
                idx,
            )

    try:
        result = DiscussionResult.from_dict(data)
    except Exception as e:
        err_msg = f"Failed to parse discussion schema from {file_path}: {e}"
        logger.error("Failed to load %s: %s", file_path, err_msg)
        raise ValueError(err_msg) from e

    logger.info(
        "Loaded discussion %s: topic='%s', %d messages, %d rounds",
        result.config.discussion_id,
        result.config.topic,
        len(result.messages),
        result.config.num_rounds,
    )
    return result


def list_discussions(output_dir: str | Path = "outputs") -> list[dict[str, Any]]:
    """
    List summary metadata for all discussions found in output_dir.

    Parameters:
    -----------
    output_dir: str or Path
        Directory to scan for discussion JSON files.

    Returns:
    --------
    list[dict[str, Any]]: List of metadata summaries sorted newest first.
    """
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        logger.info(
            "Directory '%s' does not exist or is not a directory, returning empty list",
            output_dir,
        )
        return []

    summaries: list[dict[str, Any]] = []

    for file_path in output_path.glob("*.json"):
        if file_path.name.startswith("."):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            config = data.get("config", {})
            discussion_id = config.get("discussion_id", file_path.stem)
            topic = config.get("topic", "")
            timestamp = config.get("timestamp", "")
            num_agents = len(config.get("agent_ids", []))
            num_rounds = config.get("num_rounds", 0)
            num_messages = len(data.get("messages", []))

            summaries.append(
                {
                    "discussion_id": discussion_id,
                    "topic": topic,
                    "timestamp": timestamp,
                    "file_path": str(file_path),
                    "num_agents": num_agents,
                    "num_rounds": num_rounds,
                    "num_messages": num_messages,
                }
            )
        except Exception as e:
            logger.warning("Skipping %s: %s", file_path.name, e)
            continue

    # Sort descending by timestamp, falling back to discussion_id
    summaries.sort(
        key=lambda item: (item.get("timestamp") or "", item.get("discussion_id") or ""),
        reverse=True,
    )

    logger.info("Found %d discussion(s) in %s", len(summaries), output_dir)
    return summaries
