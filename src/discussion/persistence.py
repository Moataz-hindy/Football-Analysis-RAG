import json
import logging
import os
import re
from datetime import datetime, timezone
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


# ---------------------------------------------------------------------------
# Bridge: DiscussionState (orchestrator) → persistence JSON
# ---------------------------------------------------------------------------

def _extract_opinion(content: str) -> dict[str, str]:
    """Best-effort extraction of STANCE / REASONING / SOURCES USED from agent text.

    The orchestrator prompts agents to respond in this structured format.
    If markers are missing, the full content is stored as raw_text so
    Week 4 can still consume it.
    """
    stance = ""
    reasoning = ""
    sources_used = ""

    # Try to extract STANCE
    stance_match = re.search(
        r"STANCE\s*:\s*(.+?)(?=\nREASONING\s*:|$)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if stance_match:
        stance = stance_match.group(1).strip()

    # Try to extract REASONING
    reasoning_match = re.search(
        r"REASONING\s*:\s*(.+?)(?=\nSOURCES?\s*USED\s*:|$)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

    # Try to extract SOURCES USED
    sources_match = re.search(
        r"SOURCES?\s*USED\s*:\s*(.+)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if sources_match:
        sources_used = sources_match.group(1).strip()

    return {
        "stance": stance,
        "reasoning": reasoning,
        "sources_used": sources_used,
        "raw_text": content,
    }


def _graph_to_adjacency(graph_obj: Any) -> dict[str, list[str]]:
    """Convert a DiscussionGraph / NetworkX DiGraph to an adjacency dict."""
    # Accept GraphRouter, DiscussionGraph, or nx.DiGraph
    g = graph_obj
    if hasattr(g, "graph"):  # GraphRouter or DiscussionGraph wrapper
        g = g.graph
    if hasattr(g, "graph"):  # DiscussionGraph.graph → nx.DiGraph
        g = g.graph

    adjacency: dict[str, list[str]] = {}
    for node in g.nodes:
        adjacency[node] = list(g.successors(node))
    return adjacency


def save_discussion_from_state(
    state: Any,
    router: Any = None,
    output_dir: str | Path = "outputs",
    llm_model: str = "",
    llm_temperature: float = 0.0,
    duration_seconds: float = 0.0,
    errors: list[str] | None = None,
) -> str:
    """Bridge function: convert orchestrator DiscussionState → persistence JSON.

    Parameters
    ----------
    state : DiscussionState
        The completed discussion state returned by DiscussionOrchestrator.run().
    router : GraphRouter or DiscussionGraph, optional
        The graph/router used during the discussion. If provided, the
        adjacency list is serialized into the output config.
    output_dir : str or Path
        Directory for the output JSON file.
    llm_model : str
        Model identifier for reproducibility.
    llm_temperature : float
        Temperature used during the discussion.
    duration_seconds : float
        Wall-clock duration of the discussion run.
    errors : list[str] or None
        Any errors that occurred during the discussion.

    Returns
    -------
    str
        Path to the saved JSON file.
    """
    logger.info(
        "Converting DiscussionState %s to persistence format...",
        state.discussion_id,
    )

    # --- Build config ---
    graph_dict: dict[str, list[str]] = {}
    if router is not None:
        try:
            graph_dict = _graph_to_adjacency(router)
        except Exception as e:
            logger.warning("Could not serialize graph: %s", e)

    config = {
        "discussion_id": state.discussion_id,
        "topic": state.topic,
        "num_rounds": state.total_rounds,
        "agent_ids": list(state.agent_ids),
        "graph": graph_dict,
        "llm_model": llm_model,
        "llm_temperature": llm_temperature,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # --- Convert messages ---
    messages = []
    for msg in state.messages:
        # Convert sources (RetrievedSource objects) to dicts
        sources_used = []
        for s in getattr(msg, "sources", []):
            if hasattr(s, "content"):
                sources_used.append({
                    "content": s.content,
                    "source": getattr(s, "source", ""),
                    "score": getattr(s, "score", None),
                    "metadata": getattr(s, "metadata", {}),
                })
            elif isinstance(s, dict):
                sources_used.append(s)

        # Convert tool_calls to retrieval_events
        retrieval_events = []
        for tc in getattr(msg, "tool_calls", []):
            name = tc.name if hasattr(tc, "name") else tc.get("name", "")
            args = tc.arguments if hasattr(tc, "arguments") else tc.get("arguments", {})
            result = tc.result if hasattr(tc, "result") else tc.get("result")

            retrieval_events.append({
                "query": args.get("query", str(args)),
                "num_results": len(result) if isinstance(result, list) else 0,
                "timestamp": getattr(msg, "timestamp", ""),
                "metadata": {"tool_name": name, "arguments": args},
            })

        messages.append({
            "round_num": msg.round_number,
            "sender_id": msg.sender_id,
            "recipient_ids": list(msg.recipient_ids),
            "content": msg.content,
            "timestamp": getattr(msg, "timestamp", ""),
            "sources_used": sources_used,
            "retrieval_events": retrieval_events,
            "metadata": {
                "message_id": getattr(msg, "message_id", ""),
            },
        })

    # --- Extract opinions from messages ---
    opinions = []
    for msg in state.messages:
        parsed = _extract_opinion(msg.content)
        opinions.append({
            "agent_id": msg.sender_id,
            "round_num": msg.round_number,
            "stance": parsed["stance"],
            "reasoning": parsed["reasoning"],
            "sources_used": parsed["sources_used"],
            "raw_text": parsed["raw_text"],
            "timestamp": getattr(msg, "timestamp", ""),
        })

    # --- Build metadata ---
    total_retrieval = sum(
        len(m.get("retrieval_events", [])) if isinstance(m, dict)
        else len(getattr(m, "retrieval_events", []))
        for m in messages
    )

    metadata = {
        "duration_seconds": duration_seconds,
        "total_messages": len(messages),
        "total_retrieval_events": total_retrieval,
        "errors": errors or [],
    }

    # --- Assemble and save ---
    data = {
        "config": config,
        "messages": messages,
        "opinions": opinions,
        "metadata": metadata,
    }

    return save_discussion(data, output_dir=output_dir)
