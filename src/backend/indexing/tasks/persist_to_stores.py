from typing import Dict, List
import logging
from app.core.schemas import VideoClip, TextChunk
from app.core.storage import VectorStore, ChunkStore


logger = logging.getLogger(__name__)

async def persist_to_stores(
    chunk_embeddings: Dict[str, List[float]],
    clip_embeddings: Dict[str, List[float]],
    text_chunks: Dict[str, TextChunk], # Assuming chunks are passed as a dict
    video_clips: Dict[str, VideoClip], # Assuming clips are passed as a dict
    vector_store: VectorStore,
    chunk_store: ChunkStore,
    chunk_collection_name: str,
    clip_collection_name: str
):
    """
    Persists embeddings to the vector store and raw chunks to the chunk store.
    """
    logger.info("Persisting embeddings and chunks to storage.")
    
    await chunk_store.add_chunks(text_chunks)
    
    chunk_ids = list(chunk_embeddings.keys())
    chunk_vectors = list(chunk_embeddings.values())
    chunk_metadatas = [{"source_video_id": text_chunks[cid].source_video_id} for cid in chunk_ids]
    await vector_store.add(chunk_collection_name, chunk_ids, chunk_vectors, chunk_metadatas)
    
    clip_ids = list(clip_embeddings.keys())
    clip_vectors = list(clip_embeddings.values())
    clip_metadatas = [{"source_video_id": video_clips[cid].source_video_id} for cid in clip_ids]
    await vector_store.add(clip_collection_name, clip_ids, clip_vectors, clip_metadatas)
    
    logger.info("Successfully persisted all data to storage.")