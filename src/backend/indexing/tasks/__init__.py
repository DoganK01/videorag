"""
This package contains the individual, atomic tasks that form the VideoRAG
indexing pipeline. Each task is an asynchronous function designed to be
executed by a pipeline orchestrator (e.g., Celery, ARQ, or a custom script).

The pipeline flow is as follows:
1.  `segment_video`: Splits a long video into smaller, manageable clips.
2.  `transcribe_audio`: Generates transcripts for each clip using ASR.
3.  `generate_initial_captions`: Generates visual captions for each clip using a VLM.
4.  `build_knowledge_graph`: Processes text chunks to extract entities/relations and updates the graph.
5.  `embed_chunks_and_clips`: Creates vector embeddings for raw text chunks and video clips.
6.  `persist_to_stores`: Saves the final embeddings and chunk data to the respective databases.
"""

from app.indexing.tasks.segment_video import segment_video
from app.indexing.tasks.transcribe_audio import transcribe_audio
from app.indexing.tasks.generate_initial_captions import generate_initial_captions
from app.indexing.tasks.build_knowledge_graph import build_knowledge_graph
from app.indexing.tasks.embed_chunks_and_clips import embed_chunks_and_clips
from app.indexing.tasks.persist_to_stores import persist_to_stores

__all__ = [
    "segment_video",
    "transcribe_audio",
    "generate_initial_captions",
    "build_knowledge_graph",
    "embed_chunks_and_clips",
    "persist_to_stores",
]