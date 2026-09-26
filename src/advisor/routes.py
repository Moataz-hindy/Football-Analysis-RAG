"""HTTP entry points for verified advisor jobs."""
from fastapi import APIRouter, HTTPException, Response
from src.advisor.models import AnalystRequest, StrictModel
from src.advisor.service import AdvisorJob, CapacityError, get_job, submit_job

router = APIRouter(prefix="/discussions/{discussion_id}/advisor", tags=["Advisor"])

class SubmitAdvisorRequest(StrictModel):
    request: AnalystRequest
    force: bool = False

@router.post("/jobs", response_model=AdvisorJob)
def create_advisor_job(discussion_id: str, body: SubmitAdvisorRequest, response: Response):
    if discussion_id != body.request.discussion_id:
        raise HTTPException(422, "The discussion ID must match the request.")
    try:
        job = submit_job(body.request, force=body.force)
        response.status_code = 200 if job.cached else 202
        return job
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except CapacityError as error:
        raise HTTPException(429, str(error), headers={"Retry-After": "3"}) from error
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error

@router.get("/jobs/{job_id}", response_model=AdvisorJob)
def read_advisor_job(discussion_id: str, job_id: str):
    try:
        return get_job(discussion_id, job_id)
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from error
