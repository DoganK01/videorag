# videorag_project/core/storage/__init__.py
"""
This package provides production-level, persistent storage solutions for the VideoRAG
framework, including graph, vector, metadata, and key-value stores.

The design emphasizes abstraction, allowing business logic to be decoupled from
specific database technologies.

Key Components:
- GraphStore: Manages the knowledge graph of entities and relationships.
- VectorStore: Manages embeddings for video clips and text chunks.
- ChunkStore: Manages the raw textual content of processed video chunks.
- MetadataStore: Manages structured metadata for each video clip.
"""

from app.core.storage.chunk_store import ChunkStore, RedisChunkStore, ChunkStoreError
from app.core.storage.graph_store import GraphStore, Neo4jGraphStore, GraphStoreError
from app.core.storage.vector_store import VectorStore, MilvusVectorStore, VectorStoreError
from app.core.storage.metadata_store import MetadataStore, MongoMetadataStore, MetadataStoreError

__all__ = [
    "ChunkStore",
    "RedisChunkStore",
    "ChunkStoreError",
    "GraphStore",
    "Neo4jGraphStore",
    "GraphStoreError",
    "VectorStore",
    "MilvusVectorStore",
    "VectorStoreError",
    "MetadataStore",
    "MongoMetadataStore",
    "MetadataStoreError",
]