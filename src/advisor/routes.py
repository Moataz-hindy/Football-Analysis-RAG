"""GET only reads; POST generates at most once for a completed snapshot."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from src.advisor import service

router = APIRouter(tags=["Advisor"])


class AdvisorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retry_failed: bool = False


def _call(function, *args):
    try:
        return function(*args)
    except FileNotFoundError:
        raise HTTPException(404, "Discussion not found.")
    except service.NotReady as exc:
        raise HTTPException(409, str(exc))
    except service.Busy as exc:
        raise HTTPException(429, str(exc))
    except ValueError:
        raise HTTPException(422, "Invalid discussion ID or data.")


@router.get("/discussions/{discussion_id}/advisor")
def read_advisor(discussion_id: str):
    return _call(service.get_opinion, discussion_id)


@router.post("/discussions/{discussion_id}/advisor")
def generate_advisor(discussion_id: str, request: AdvisorRequest):
    # FastAPI runs this synchronous endpoint in its thread pool. Polls stay read-only.
    return _call(service.create_opinion, discussion_id, request.retry_failed)


@router.get("/discussions/{discussion_id}/advisor/decision")
def read_decision(discussion_id: str):
    return _call(service.get_opinion, discussion_id, "decision")


@router.post("/discussions/{discussion_id}/advisor/decision")
def generate_decision(discussion_id: str, request: AdvisorRequest):
    return _call(service.create_opinion, discussion_id, request.retry_failed, "decision")
