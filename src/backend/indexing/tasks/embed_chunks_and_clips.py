import logging
from typing import List

from app.core.models import OpenAITextEncoder, ImageBindEncoder
from app.core.schemas import TextChunk, VideoClip

logger = logging.getLogger(__name__)

async def embed_chunks_and_clips(
    text_chunks: List[TextChunk],
    video_clips: List[VideoClip],
    text_encoder: OpenAITextEncoder,
    multimodal_encoder: ImageBindEncoder,
):
    """
    Generates embeddings for all text chunks and video clips.

    Returns:
        A tuple containing (chunk_embeddings, clip_embeddings)
    """
    logger.info("Starting embedding generation for chunks and clips.")
    
    chunk_contents = [chunk.content for chunk in text_chunks]
    chunk_embeddings = await text_encoder.encode_async(chunk_contents)
    
    clip_paths = [clip.clip_path for clip in video_clips]
    multimodal_embeddings = await multimodal_encoder.encode_async(video_paths=clip_paths)
    clip_embeddings = multimodal_embeddings['vision']

    logger.info("Finished embedding generation.")
    
    chunk_embedding_map = {text_chunks[i].chunk_id: emb for i, emb in enumerate(chunk_embeddings)}
    clip_embedding_map = {video_clips[i].clip_id: emb for i, emb in enumerate(clip_embeddings)}
    
    return chunk_embedding_map, clip_embedding_map