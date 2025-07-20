import asyncio
import logging
import os
from typing import List

from app.api.services.retrieval_service import RetrievedContext
from app.api.dependencies import AppState
from app.core.schemas import APIQueryResponse, CandidateClipInfo, APIResponseSource
from app.indexing.utils.video_processor import extract_frames

logger = logging.getLogger(__name__)

class GenerationService:
    def __init__(self, app_state: AppState):
        self.state = app_state
        self.llm = app_state.llm_client
        self.vlm = app_state.vlm_model
        self.config = app_state.config

    async def generate(self, query: str, retrieved_context: RetrievedContext) -> APIQueryResponse:
        """
        Generates the final response by synthesizing query-aware, enriched context.
        """
        logger.info(f"Starting generation for query: '{query}'")
        
        video_context_str  = await self._get_query_aware_content(query, retrieved_context.filtered_clips_info)
        
        chunk_context_list = [
            info.combined_text for info in retrieved_context.filtered_clips_info
        ]

        separator = "\n\n--- Next Retrieved Context ---\n\n"
        chunk_context_str = separator.join(chunk_context_list)

        final_prompt = f"""
        You are an expert assistant. Your task is to provide a comprehensive and detailed
        answer to the user's question based *exclusively* on the provided context.
        The context is composed of two parts:
        1. Detailed, query-focused descriptions of specific video clips.
        2. Broader context from the initial captions and transcripts of those same clips.
        Synthesize information from BOTH sources to form your answer.

        USER QUESTION:
        "{query}"

        ==============================================
        PART 1: DETAILED VISUALS (Query-Focused - V'_t):
        ==============================================
        {video_context_str}

        ==============================================
        PART 2: INITIAL CONTEXT (Captions & Transcripts - Ĥ):
        ==============================================
        {chunk_context_str}

        YOUR COMPREHENSIVE ANSWER:
        """
        
        final_answer = await self.llm.generate_for_final_answer_async(final_prompt, temperature=0.2)
        
        api_sources = []
        enriched_captions = {clip_id: content for clip_id, content in zip(
            [info.retrieved_source.clip_id for info in retrieved_context.filtered_clips_info],
            video_context_str.split("--- Context from Clip ID: ")[1:] # A way to get individual captions back
        )}
        
        for info in retrieved_context.filtered_clips_info:
            source = info.retrieved_source
            start_min, start_sec = divmod(int(source.start_time), 60)
            end_min, end_sec = divmod(int(source.end_time), 60)
            
            api_source = APIResponseSource(
                clip_id=source.clip_id,
                source_video_id=source.source_video_id,
                timestamp=f"{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}",
                # Use the newly generated query-aware caption as the content
                content=enriched_captions.get(source.clip_id, "Content not available.").strip(),
                retrieval_score=source.retrieval_score
            )
            api_sources.append(api_source)

        return APIQueryResponse(
            query=query,
            answer=final_answer.strip(),
            retrieved_sources=api_sources
        )

    async def _get_query_aware_content(self, query: str, filtered_clips_info: List[CandidateClipInfo]) -> str:
        """
        Implements the full two-stage content extraction from Section 3.3.
        This re-runs the VLM on filtered clips with query-specific prompts.
        """
        if not filtered_clips_info:
            return "No relevant context was found."
            
        logger.info(f"Performing query-aware VLM re-captioning for {len(filtered_clips_info)} clips.")
        
        keyword_prompt = f"Extract a concise list of 2-5 essential keywords from this query: '{query}'"
        keywords_str = await self.llm.generate_for_indexing_async(keyword_prompt, max_tokens=32)
        keywords = [k.strip() for k in keywords_str.split(',')]
        logger.debug(f"Extracted keywords for VLM prompt: {keywords}")

        async def enrich_one_clip(clip_info: CandidateClipInfo) -> str:
            clip_id = clip_info.retrieved_source.clip_id
            
            clip_path = self.config['paths']['shared_clip_storage'] + f"/{clip_info.retrieved_source.source_video_id}/clips/{clip_id}.mp4"
            
            k_prime = self.config['indexing']['query_aware_vlm_frames_k_prime']
            temp_frame_dir = self.config['paths']['temp_frame_dir']
            clip_frame_dir = os.path.join(temp_frame_dir, f"query_{clip_id}")
            
            try:
                if not os.path.exists(clip_path):
                    raise FileNotFoundError(f"Clip file not found at shared path: {clip_path}")
                
                frame_paths = await extract_frames(
                    video_path=clip_path,
                    output_dir=clip_frame_dir,
                    num_frames=k_prime
                )
                
                vlm_prompt = (
                    f"Given the transcript: '{clip_info.transcript}'. "
                    f"Focusing on keywords: {', '.join(keywords)}. "
                    f"Provide a highly detailed visual description based on the video frames."
                )
                
                query_aware_caption = await self.vlm.generate_caption_async(frame_paths, vlm_prompt)
                
                for path in frame_paths: os.remove(path)
                os.rmdir(clip_frame_dir)

                return (
                    f"--- Context from Clip ID: {clip_id} ---\n"
                    f"**Visuals (Query-Focused Description):** {query_aware_caption}\n"
                    f"**Spoken Transcript:** {clip_info.transcript}\n"
                )

            except Exception as e:
                logger.error(f"Failed query-aware re-captioning for clip {clip_id}: {e}")
                return (
                    f"--- Context from Clip ID: {clip_id} ---\n"
                    f"**Visuals (Initial Description):** {clip_info.initial_visual_caption}\n"
                    f"**Spoken Transcript:** {clip_info.transcript}\n"
                )
        
        enrichment_tasks = [enrich_one_clip(info) for info in filtered_clips_info]
        enriched_context_parts = await asyncio.gather(*enrichment_tasks)
        
        return "\n".join(enriched_context_parts)