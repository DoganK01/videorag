# src/app/api/routers/library_router.py
import logging
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import List, Optional
from pydantic import BaseModel

from app.api.dependencies import AppState
from app.core.storage import MetadataStore

logger = logging.getLogger(__name__)
router = APIRouter()

class VideoLibraryItem(BaseModel):
    id: str
    title: str
    duration: str
    indexedAt: str
    size: str
    status: str
    tags: List[str]
    description: Optional[str] = None


def get_app_state(request: Request) -> AppState:
    """A dependency to fetch the application's shared state."""
    return request.app.state.app_state

@router.get(
    "/library",
    response_model=List[VideoLibraryItem],
    summary="Get the library of all indexed videos"
)
async def get_video_library(
    app_state: AppState = Depends(get_app_state),
    search: Optional[str] = Query(None, description="Search term for video titles, descriptions, etc."),
):
    """
    Retrieves a summarized list of all unique videos that have been indexed,
    pulling data directly and efficiently from the metadata store.
    
    This endpoint uses a powerful database aggregation to avoid slow, in-memory processing,
    making it scalable for thousands of videos.
    """
    metadata_store: MetadataStore = app_state.metadata_store
    
    try:
        videos_summary = await metadata_store.get_all_videos_summary(search_query=search)
        
        library_items = []
        for summary in videos_summary:
            title = summary.get('title', 'Unknown Video').replace('_', ' ').replace('-', ' ').title()
            duration_sec = summary.get('duration_seconds', 0)
            duration_str = f"{int(duration_sec // 60)}:{int(duration_sec % 60):02d}"
            
            item = VideoLibraryItem(
                id=summary['id'],
                title=title,
                duration=duration_str,
                indexedAt=summary.get('indexedAt', '').isoformat() if summary.get('indexedAt') else 'N/A',
                size="N/A", # This info is not currently tracked, can be added later
                status="indexed", # All videos from this query are considered indexed
                tags=["AI", "Video"], # Tags can be generated and stored during indexing later
                description=f"A video containing {summary.get('clip_count', 0)} processed clips."
            )
            library_items.append(item)
            
        return library_items

    except Exception as e:
        logger.error(f"Failed to fetch video library: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving the video library."
        )