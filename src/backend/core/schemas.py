"""
Pydantic schemas for data validation and serialization across the VideoRAG application.

These models serve as the single source of truth for the structure of data objects,
ensuring consistency between the indexing pipeline, storage layers, and the API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class TaskError(Exception):
    """Custom exception for pipeline task failures."""
    def __init__(self, message: str, task_name: Optional[str] = None):
        self.message = message
        self.task_name = task_name
        super().__init__(f"Task '{task_name}' failed: {message}")

class VideoClip(BaseModel):
    """
    Represents a single segmented clip from a source video.
    This is the fundamental unit of processing.
    """
    clip_id: str = Field(..., description="Unique identifier for the clip, e.g., 'video1_clip_0001'.")
    source_video_id: str = Field(..., description="Identifier of the original video file.")
    clip_path: str = Field(..., description="Absolute path to the saved clip file. For distributed systems, this must be a shared path (NFS/S3).")
    start_time: float = Field(..., description="Start time of the clip in seconds from the beginning of the source video.")
    end_time: float = Field(..., description="End time of the clip in seconds.")

class AudioTranscript(BaseModel):
    """Represents the ASR-generated transcript for a single video clip."""
    clip_id: str = Field(..., description="The ID of the corresponding video clip.")
    text: str = Field(..., description="The transcribed text content.")

class VisualCaption(BaseModel):
    """Represents the VLM-generated visual caption for a single video clip."""
    clip_id: str = Field(..., description="The ID of the corresponding video clip.")
    text: str = Field(..., description="The generated caption describing the visual content.")


class KnowledgeGraphNode(BaseModel):
    """
    Represents an entity (a node) in the knowledge graph.
    The `id` should be a normalized, unique string.
    """
    entity_id: str = Field(..., description="Normalized, unique identifier for the entity, e.g., 'transformer_architecture'.")
    label: str = Field(..., description="Human-readable label for the entity, e.g., 'Transformer Architecture'.")
    description: str = Field(..., description="A detailed, synthesized description of the entity.")
    description_embedding: Optional[List[float]] = Field(None, description="Vector embedding of the entity's description for semantic search.")

class KnowledgeGraphRelationship(BaseModel):
    """Represents a relationship (an edge) between two entities in the knowledge graph."""
    source_id: str = Field(..., description="The ID of the source entity node.")
    target_id: str = Field(..., description="The ID of the target entity node.")
    type: str = Field(..., description="The type of the relationship, e.g., 'EXPLAINS', 'DEVELOPED_AT'.")
    description: str = Field(..., description="A natural language sentence describing the relationship.")



class TextChunk(BaseModel):
    """
    Represents a chunk of combined textual data (transcripts + captions)
    that is used for KG extraction and embedding.
    """
    chunk_id: str = Field(..., description="Unique identifier for the text chunk.")
    source_video_id: str = Field(..., description="Identifier of the original video file.")
    content: str = Field(..., description="The raw textual content of the chunk.")
    source_clip_ids: List[str] = Field(..., description="List of clip_ids that contributed to this chunk.")



class APIQueryRequest(BaseModel):
    """Request model for the main /query endpoint."""
    query: str = Field(..., min_length=3, max_length=512, description="The user's question about the video content.")
    # Optional parameters to control retrieval can be added here
    # e.g., top_k: int = 5

class RetrievedSource(BaseModel):
    """Represents a single piece of retrieved evidence to be shown to the user."""
    clip_id: str
    source_video_id: str
    start_time: float
    end_time: float
    retrieval_score: float = Field(..., description="The similarity or relevance score from the retrieval process.")
    source_type: str = Field(..., description="Type of retrieval, e.g., 'textual_graph' or 'visual_embedding'.")


class CandidateClipInfo(BaseModel):
    """
    A rich data object representing a candidate clip found during initial retrieval.
    It contains all information needed for LLM filtering and final generation.
    """
    retrieved_source: RetrievedSource
    initial_visual_caption: str
    transcript: str

    @property
    def combined_text(self) -> str:
        """A helper to get the full textual representation for LLM judging."""
        return f"Visual Caption: {self.initial_visual_caption}\nTranscript: {self.transcript}"
    

class APIResponseSource(BaseModel):
    """
    A clean, public-facing model for a retrieved source, designed specifically for the UI.
    This is what the user/frontend will receive.
    """
    id: str = Field(..., description="The unique clip ID.", alias="clip_id")
    source_video: str = Field(..., description="The name of the source video.", alias="source_video_id")
    timestamp: str = Field(..., description="A formatted timestamp string, e.g., '02:30 - 03:00'.")
    content: str = Field(..., description="A synthesized, query-aware description of the clip's content.")
    score: float = Field(..., description="The relevance score of this source to the query.", alias="retrieval_score")

    class Config:
        # Allows creating this model from an object that has 'clip_id', etc.
        populate_by_name = True 

class APIQueryResponse(BaseModel):
    """The final response model for the /query endpoint."""
    query: str = Field(..., description="The original user query.")
    answer: str = Field(..., description="The final answer generated by the LLM.")
    retrieved_sources: List[APIResponseSource] = Field(
        ...,
        description="A list of sources used to generate the answer, formatted for UI display."
    )