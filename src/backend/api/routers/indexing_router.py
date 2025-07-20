import asyncio
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Literal, Optional

from app.indexing.pipeline import IndexingPipeline
from app.api.dependencies import AppState

logger = logging.getLogger(__name__)
router = APIRouter()


class IndexingRequest(BaseModel):
    video_path: str = Field(
        ...,
        description="Absolute path to the video file or directory ON THE SERVER where the API is running.",
        examples=["/data/source_videos/my_lecture.mp4"]
    )

class IndexingResponse(BaseModel):
    job_id: str
    message: str
    status_endpoint: str

class JobStatus(BaseModel):
    id: str
    status: Literal["pending", "processing", "completed", "error"]
    progress: float
    error: Optional[str] = None


async def run_background_indexing(job_id: str, video_path: str, app_state: AppState):
    """
    The actual indexing function that runs as a background task.
    It uses the shared resources from the FastAPI AppState.
    """
    redis_client = app_state.stores['chunk'].client
    try:
        logger.info(f"Background job {job_id} started for path: {video_path}")
        
        pipeline = IndexingPipeline(
            job_id=job_id,
            config=app_state.config,
            models=app_state.models,
            stores=app_state.stores
        )
        

        await pipeline.run_for_video(video_path)
        
    except Exception as e:
        logger.error(f"Background job {job_id} failed catastrophically: {e}", exc_info=True)
        final_error_status = JobStatus(id=job_id, status="error", progress=-1, error=str(e)).model_dump_json()
        await redis_client.set(f"job_status:{job_id}", final_error_status, ex=3600)


def get_app_state(request: Request) -> AppState:
    """A dependency to fetch the application's shared state."""
    return request.app.state.app_state


@router.post(
    "/indexing/start",
    response_model=IndexingResponse,
    summary="Start a new video indexing job"
)
async def start_indexing_job(
    request: IndexingRequest,
    app_state: AppState = Depends(get_app_state)
):
    """
    Accepts a path to a video file or directory on the server and starts
    the indexing process as a background task. It immediately returns a job ID
    which can be used to poll for the status of the job.
    """
    job_id = f"job:{hash(request.video_path + str(asyncio.get_event_loop().time()))}"
    
    redis_client = app_state.stores['chunk'].client
    
    initial_status = JobStatus(id=job_id, status="pending", progress=0.0).model_dump_json()
    await redis_client.set(f"job_status:{job_id}", initial_status, ex=3600)
    
    asyncio.create_task(run_background_indexing(job_id, request.video_path, app_state))
    
    return IndexingResponse(
        job_id=job_id,
        message="Indexing job successfully queued.",
        status_endpoint=f"/api/v1/indexing/status/{job_id}"
    )


@router.get(
    "/indexing/status/{job_id}",
    response_model=JobStatus,
    summary="Get the status of an indexing job"
)
async def get_indexing_status(job_id: str, app_state: AppState = Depends(get_app_state)):
    """
    Retrieves the current status (pending, processing, completed, error) and
    progress of a specific indexing job from Redis.
    """
    redis_client = app_state.stores['chunk'].client
    status_json = await redis_client.get(f"job_status:{job_id}")
    
    if not status_json:
        raise HTTPException(
            status_code=404,
            detail=f"Job with ID '{job_id}' not found. It may have expired or never existed."
        )
    
    return JobStatus(**json.loads(status_json))