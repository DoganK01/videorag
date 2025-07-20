import logging
from fastapi import APIRouter, Depends, Request

from app.core.schemas import APIQueryRequest, APIQueryResponse
from app.api.dependencies import AppState
from app.api.services.retrieval_service import RetrievalService
from app.api.services.generation_service import GenerationService

logger = logging.getLogger(__name__)
router = APIRouter()

def get_app_state(request: Request) -> AppState:
    """Dependency to get the application state from the request."""
    return request.app.state.app_state

@router.post("/query", response_model=APIQueryResponse)
async def process_query(
    request_data: APIQueryRequest,
    app_state: AppState = Depends(get_app_state),
):
    """
    The main endpoint for the VideoRAG framework.
    It takes a user query and returns a synthesized answer based on
    retrieved knowledge from a long-context video corpus.
    """
    logger.info(f"Received query: '{request_data.query}'")
    
    retrieval_service = RetrievalService(app_state)
    generation_service = GenerationService(app_state)
    
    retrieved_context = await retrieval_service.retrieve(request_data.query)
    
    if not retrieved_context.filtered_clips_info:
        logger.warning("No relevant clips found for the query. Returning a default response.")
        return APIQueryResponse(
            query=request_data.query,
            answer="I'm sorry, I couldn't find any relevant information in the video library to answer your question.",
            retrieved_sources=[]
        )
    
    final_response = await generation_service.generate(
        query=request_data.query,
        retrieved_context=retrieved_context
    )
    
    return final_response