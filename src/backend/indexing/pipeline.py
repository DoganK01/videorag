import asyncio
import logging
from typing import List, Dict, Any, Optional
import json

from app.core.models import (
    AzureWhisperASR, MiniCPMVLM, LLMClient,
    OpenAITextEncoder, ImageBindEncoder
)
from app.core.storage import (
    GraphStore, VectorStore, ChunkStore, MetadataStore
)
from app.core.schemas import (
    VideoClip, AudioTranscript, VisualCaption, TextChunk
)
from app.indexing.tasks import (
    segment_video, transcribe_audio, generate_initial_captions,
    build_knowledge_graph, embed_chunks_and_clips, persist_to_stores
)

logger = logging.getLogger(__name__)

class IndexingPipeline:
    """
    Orchestrates the entire VideoRAG indexing pipeline as a stateful process.
    It manages resources, task execution, data flow, and reports progress
    for background job observability.
    """
    def __init__(
        self,
        config: Dict[str, Any],
        models: Dict[str, Any],
        stores: Dict[str, Any],
        job_id: Optional[str] = None
    ):
        """
        Initializes the pipeline with all necessary configurations, models,
        storage clients, and an optional job ID for status tracking.
        """
        self.config = config
        self.models = models
        self.stores = stores
        self.job_id = job_id
        self.redis_client = self.stores['chunk'].client

    async def _update_job_status(self, progress: float, status: str = "processing"):
        """
        Updates the job's status and progress in Redis if a job_id is present.
        The status is stored as a JSON string with a 1-hour expiration.
        """
        if not self.job_id:
            return 

        status_data = {
            "id": self.job_id,
            "status": status,
            "progress": progress,
            "error": None
        }
        await self.redis_client.set(
            f"job_status:{self.job_id}",
            json.dumps(status_data),
            ex=3600 
        )
        logger.info(f"Job {self.job_id} status updated: {status}, progress: {progress}%")

    async def run_for_video(self, video_path: str):
        """
        Executes the full indexing pipeline for a single video file,
        reporting progress along the way.
        """
        logger.info(f"--- Starting Pipeline for: {video_path} (Job ID: {self.job_id}) ---")
        try:
            await self._update_job_status(progress=5.0, status="processing")

            output_dir = self.config['paths']['processing_output_dir']
            clip_duration = self.config['indexing']['clip_duration_seconds']
            video_clips: List[VideoClip] = await segment_video(
                source_video_path=video_path,
                output_dir=output_dir,
                clip_duration_seconds=clip_duration
            )
            if not video_clips:
                raise ValueError(f"No clips were generated for {video_path}.")
            await self._update_job_status(progress=15.0)

            asr_model: AzureWhisperASR = self.models['asr']
            transcripts: List[AudioTranscript] = await transcribe_audio(video_clips, asr_model)
            transcripts_map = {t.clip_id: t for t in transcripts}
            await self._update_job_status(progress=30.0)

            vlm_model: MiniCPMVLM = self.models['vlm']
            frames_per_clip = self.config['indexing']['initial_vlm_frames_k']
            temp_frame_dir = self.config['paths']['temp_frame_dir']
            captions: List[VisualCaption] = await generate_initial_captions(
                video_clips, transcripts_map, vlm_model, frames_per_clip, temp_frame_dir
            )
            captions_map = {c.clip_id: c for c in captions}
            await self._update_job_status(progress=50.0)

            text_chunks = self._create_text_chunks(video_clips, captions_map, transcripts_map)
            llm_client: LLMClient = self.models['llm']
            text_encoder: OpenAITextEncoder = self.models['text_encoder']
            graph_store: GraphStore = self.stores['graph']
            await build_knowledge_graph(text_chunks, llm_client, text_encoder, graph_store)
            await self._update_job_status(progress=75.0)

            multimodal_encoder: ImageBindEncoder = self.models['multimodal_encoder']
            chunk_embedding_map, clip_embedding_map = await embed_chunks_and_clips(
                text_chunks, video_clips, text_encoder, multimodal_encoder
            )
            await self._update_job_status(progress=90.0)

            vector_store: VectorStore = self.stores['vector']
            chunk_store: ChunkStore = self.stores['chunk']
            await persist_to_stores(
                chunk_embedding_map, clip_embedding_map,
                {chunk.chunk_id: chunk for chunk in text_chunks},
                {clip.clip_id: clip for clip in video_clips},
                vector_store, chunk_store,
                self.config['storage']['vector_collections']['chunks']['name'],
                self.config['storage']['vector_collections']['clips']['name']
            )
            await self._persist_clip_metadata(video_clips, captions_map, transcripts_map)
            
            await self._update_job_status(progress=100.0, status="completed")
            logger.info(f"--- Successfully Completed Pipeline for: {video_path} ---")

        except Exception as e:
            logger.critical(f"--- Pipeline FAILED for: {video_path} (Job ID: {self.job_id}) ---", exc_info=True)
            if self.job_id:
                error_status = {
                    "id": self.job_id, "status": "error", "progress": -1, "error": f"{type(e).__name__}: {e}"
                }
                await self.redis_client.set(f"job_status:{self.job_id}", json.dumps(error_status), ex=3600)
            raise  # Re-raise the exception to be handled by the background task runner

    def _create_text_chunks(
        self,
        video_clips: List[VideoClip],
        captions: Dict[str, VisualCaption],
        transcripts: Dict[str, AudioTranscript]
    ) -> List[TextChunk]:
        """
        Combines captions and transcripts into larger text chunks for KG extraction.
        A simple strategy is to combine text from N consecutive clips.
        """
        chunks = []
        chunk_size_clips = self.config['indexing']['chunk_size_in_clips']
        video_id = video_clips[0].source_video_id if video_clips else "unknown"
        
        for i in range(0, len(video_clips), chunk_size_clips):
            clip_batch = video_clips[i:i + chunk_size_clips]
            chunk_content = []
            source_clip_ids = []
            
            for clip in clip_batch:
                caption_text = captions.get(clip.clip_id, VisualCaption(clip_id=clip.clip_id, text="")).text
                transcript_text = transcripts.get(clip.clip_id, AudioTranscript(clip_id=clip.clip_id, text="")).text
                
                # Combine them into a structured string
                combined_text = f"CLIP_ID: {clip.clip_id}\nVISUALS: {caption_text}\nAUDIO: {transcript_text}\n"
                chunk_content.append(combined_text)
                source_clip_ids.append(clip.clip_id)
            
            if not chunk_content:
                continue
                
            chunk_id = f"{video_id}_chunk_{i // chunk_size_clips:04d}"
            chunks.append(TextChunk(
                chunk_id=chunk_id,
                source_video_id=video_id,
                content="\n---\n".join(chunk_content),
                source_clip_ids=source_clip_ids
            ))
        return chunks

    async def _persist_clip_metadata(self, video_clips, captions_map, transcripts_map):
        """Persists the complete, structured metadata for each clip, now with a timestamp."""
        metadata_store: MetadataStore = self.stores['metadata']
        logger.info(f"Persisting rich metadata for {len(video_clips)} clips.")
        
        tasks = []
        for clip in video_clips:
            clip_data = {
                "clip_id": clip.clip_id,
                "source_video_id": clip.source_video_id,
                "clip_path": clip.clip_path,
                "start_time": clip.start_time,
                "end_time": clip.end_time,
                "initial_caption": captions_map.get(clip.clip_id, VisualCaption(clip_id=clip.clip_id, text="")).text,
                "transcript": transcripts_map.get(clip.clip_id, AudioTranscript(clip_id=clip.clip_id, text="")).text,
                # The storage layer will add the 'createdAt' timestamp
            }
            tasks.append(metadata_store.add_clip_metadata(clip_data))
        
        await asyncio.gather(*tasks)
        logger.info("Successfully persisted all clip metadata.")