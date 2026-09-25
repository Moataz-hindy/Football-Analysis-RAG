"""Load and cache saved discussions for the API."""

from threading import Lock
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import re
import logging

from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from fastapi import HTTPException
from src.api.schemas import StartDiscussionRequest, StartDiscussionResponse
from src.api.schemas import DiscussionStatusResponse
from src.discussion.persistence import load_discussion
from src.discussion.types import DiscussionResult


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
_runtime_status: dict[str, DiscussionStatusResponse] = {}
_status_lock = Lock()

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="discussion",
)

# At most two accepted jobs: one running and one waiting.
_runner_slots = BoundedSemaphore(2)
_worker_state = "ready"


def _file_version(path: Path) -> tuple[int, int, int, int]:
    """Identify the current version of a file without reading its contents."""
    info = path.stat()
    return (
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_size,
        info.st_ino,
    )


@lru_cache(maxsize=128)
def _load_cached(
    path: Path,
    version: tuple[int, int, int, int],
) -> DiscussionResult:
    """Read and parse a file only when its path or version changes."""
    return load_discussion(path)


def get_saved_discussion(
    discussion_id: str,
    output_dir: str | Path | None = None,
) -> DiscussionResult:
    """Return a saved discussion, reusing cached data when unchanged."""
    if not isinstance(discussion_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]+", discussion_id
    ):
        raise ValueError(
            "Discussion ID must contain only letters, numbers, "
            "underscores, or hyphens."
        )

    directory = (
        Path(output_dir) if output_dir is not None else OUTPUTS_DIR
    ).resolve()

    path = (directory / f"{discussion_id}.json").resolve()

    if path.parent != directory:
        raise ValueError("Discussion file must be inside the outputs directory.")

    # Retry if a checkpoint replaces the file while we are reading it.
    for _ in range(3):
        if not path.is_file():
            raise FileNotFoundError(f"Discussion '{discussion_id}' not found.")

        version = _file_version(path)
        discussion = _load_cached(path, version)

        if _file_version(path) != version:
            continue

        if discussion.config.discussion_id != discussion_id:
            raise ValueError("Discussion ID does not match the saved file.")

        # Prevent callers from modifying the shared cached object.
        return deepcopy(discussion)

    raise RuntimeError("Discussion is being updated. Please retry shortly.")


def list_saved_discussions(
    output_dir: str | Path | None = None,
) -> list[dict]:
    """List valid saved discussions, newest first."""
    directory = (
        Path(output_dir) if output_dir is not None else OUTPUTS_DIR
    ).resolve()

    if not directory.is_dir():
        return []

    summaries = []

    for path in directory.glob("*.json"):
        if path.name.startswith("."):
            continue

        try:
            discussion = get_saved_discussion(
                path.stem,
                output_dir=directory,
            )
        except (ValueError, OSError):
            # Analytics JSON, malformed discussions, or unavailable files.
            continue

        config = discussion.config

        summaries.append({
            "discussion_id": config.discussion_id,
            "topic": config.topic,
            "num_agents": len(config.agent_ids),
            "num_rounds": config.num_rounds,
            "num_messages": len(discussion.messages),
            "timestamp": config.timestamp,
        })

    return sorted(
        summaries,
        key=lambda item: item["timestamp"],
        reverse=True,
    )

def _set_runtime_status(
    discussion_id: str,
    status: str,
    *,
    total_rounds: int,
    current_round: int | None = None,
    message: str = "",
) -> None:
    """Update the status of a discussion managed by this server."""
    record = DiscussionStatusResponse(
        discussion_id=discussion_id,
        status=status,
        current_round=current_round,
        total_rounds=total_rounds,
        message=message,
    )

    with _status_lock:
        _runtime_status[discussion_id] = record


def get_runtime_status(
    discussion_id: str,
) -> DiscussionStatusResponse | None:
    """Return a copy of the tracked status, or None if not tracked."""
    with _status_lock:
        record = _runtime_status.get(discussion_id)

        if record is None:
            return None

        return record.model_copy(deep=True)



def _execute_discussion(
    discussion_id: str,
    request: StartDiscussionRequest,
) -> int:
    """Reuse the existing runner with explicit arguments."""
    from src.discussion.run_discussion import main as run_discussion

    cmd = [
        "--discussion-id", discussion_id,
        "--topic", request.topic.strip(),
        "--rounds", str(request.num_rounds),
        "--output-dir", str(OUTPUTS_DIR),
        "--personas-dir", str(PROJECT_ROOT / "personas"),
    ]
    if getattr(request, "dynamic_personas", True):
        cmd.append("--dynamic-personas")
    if getattr(request, "force_regenerate", False):
        cmd.append("--force-regenerate")

    return run_discussion(cmd)


def _run_discussion_job(
    discussion_id: str,
    request: StartDiscussionRequest,
) -> None:
    """Execute an accepted job and record its final status."""
    try:
        _set_runtime_status(
            discussion_id,
            "running",
            total_rounds=request.num_rounds,
            current_round=0,
            message="Discussion execution started.",
        )

        exit_code = _execute_discussion(discussion_id, request)

        if exit_code == 0:
            try:
                _set_runtime_status(
                    discussion_id,
                    "running",
                    total_rounds=request.num_rounds,
                    current_round=request.num_rounds,
                    message="Deliberation concluded. Precomputing intelligence analytics...",
                )
                from src.api.services.analytics_service import _load_or_compute_analytics
                _load_or_compute_analytics(discussion_id)
            except Exception as err:
                logger.warning("Auto-precomputing analytics for %s failed: %s", discussion_id, err)

            _set_runtime_status(
                discussion_id,
                "completed",
                total_rounds=request.num_rounds,
                current_round=request.num_rounds,
                message="Discussion completed and saved.",
            )
        else:
            _set_runtime_status(
                discussion_id,
                "failed",
                total_rounds=request.num_rounds,
                message=(
                    "Discussion execution failed. Check the saved "
                    "partial discussion and server logs."
                ),
            )

    except Exception:
        logger.exception("Discussion %s failed", discussion_id)

        _set_runtime_status(
            discussion_id,
            "failed",
            total_rounds=request.num_rounds,
            message="Discussion execution failed. Check the server logs.",
        )

    finally:
        _runner_slots.release()



async def enqueue_discussion(
    discussion_id: str,
    request: StartDiscussionRequest,
) -> StartDiscussionResponse:
    """Accept a job promptly without waiting for the debate to finish."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", discussion_id):
        raise HTTPException(
            status_code=422,
            detail="Invalid discussion ID.",
        )

    if not request.topic.strip():
        raise HTTPException(
            status_code=422,
            detail="Topic cannot be blank.",
        )

    job_request = request.model_copy(deep=True)
    job_request.topic = job_request.topic.strip()

    with _status_lock:
        if _worker_state != "ready":
            raise HTTPException(
                status_code=503,
                detail="Discussion worker is shutting down or stopped.",
            )

        if (
            discussion_id in _runtime_status
            or (OUTPUTS_DIR / f"{discussion_id}.json").exists()
        ):
            raise HTTPException(
                status_code=409,
                detail="That discussion ID already exists. Choose another ID.",
            )

        if not _runner_slots.acquire(blocking=False):
            raise HTTPException(
                status_code=503,
                detail="Discussion queue is full. Please retry later.",
            )

        _runtime_status[discussion_id] = DiscussionStatusResponse(
            discussion_id=discussion_id,
            status="queued",
            total_rounds=request.num_rounds,
            message="Waiting for the discussion worker.",
        )

        try:
            _executor.submit(
                _run_discussion_job,
                discussion_id,
                job_request,
            )
        except Exception:
            _runtime_status.pop(discussion_id, None)
            _runner_slots.release()
            logger.exception("Could not schedule discussion %s", discussion_id)

            raise HTTPException(
                status_code=503,
                detail="Discussion worker is unavailable.",
            )

    return StartDiscussionResponse(
        discussion_id=discussion_id,
        status="queued",
        message="Discussion accepted. Poll its status endpoint for progress.",
    )



def get_discussion_status_record(
    discussion_id: str,
) -> DiscussionStatusResponse:
    """Combine runtime state with progress from saved checkpoints."""
    try:
        discussion = get_saved_discussion(discussion_id)
    except FileNotFoundError:
        # A queued or newly started job may not have saved a file yet.
        tracked = get_runtime_status(discussion_id)

        if tracked is not None:
            return tracked

        return DiscussionStatusResponse(
            discussion_id=discussion_id,
            status="not_found",
            message="Discussion not found.",
        )

    metadata = discussion.config.metadata
    current_round = metadata.get("current_round")

    if not isinstance(current_round, int):
        current_round = max(
            (message.round_num for message in discussion.messages),
            default=None,
        )

    # Read the tracker after loading the file to get its latest state.
    tracked = get_runtime_status(discussion_id)

    if tracked is not None:
        if tracked.status != "queued" and current_round is not None:
            tracked.current_round = current_round

        if tracked.status == "running" and current_round is not None:
            tracked.message = (
                f"Discussion is running. Latest saved round: {current_round}."
            )

        return tracked

    # No live record: interpret the saved execution status.
    saved_status = metadata.get("status")

    if discussion.metadata.errors or saved_status in {
        "failed",
        "failed_partial",
        "interrupted",
        "error",
    }:
        status = "failed"
        message = "Saved discussion failed or was interrupted."

    elif saved_status == "completed" or (saved_status is None and not discussion.metadata.errors):
        status = "completed"
        message = "Saved discussion completed."

    else:
        status = "unknown"
        message = (
            "Saved discussion found, but this server is not tracking "
            "its execution and completion is not confirmed."
        )

    return DiscussionStatusResponse(
        discussion_id=discussion_id,
        status=status,
        current_round=current_round,
        total_rounds=discussion.config.num_rounds,
        message=message,
    )


def start_discussion_worker() -> None:
    """Prepare the worker when the API starts."""
    global _executor, _worker_state

    with _status_lock:
        if _worker_state == "stopping":
            raise RuntimeError("Discussion worker is still shutting down.")

        if _worker_state == "closed":
            _executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="discussion",
            )

        _worker_state = "ready"


def shutdown_discussion_worker() -> None:
    """Reject new work and finish accepted jobs before closing."""
    global _worker_state

    with _status_lock:
        if _worker_state == "closed":
            return

        _worker_state = "stopping"
        executor = _executor

    # Do not hold _status_lock while waiting.
    # Running jobs need that lock to publish their final status.
    executor.shutdown(wait=True)

    with _status_lock:
        _worker_state = "closed"