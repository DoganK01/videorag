"""
Interface and implementation for the vector database store.
This module handles storing and searching high-dimensional vectors.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any

from pymilvus import (
    connections, utility,
    Collection, CollectionSchema, FieldSchema, DataType
)

class VectorStoreError(Exception):
    """Custom exception for vector store operations."""
    pass

class VectorStore(ABC):
    """Abstract Base Class for a vector store."""
    @abstractmethod
    async def setup(self, dimension: int, collection_name: str):
        """Prepare the vector store (e.g., create collections, indexes)."""
        pass
    
    @abstractmethod
    async def close(self):
        """Close the connection to the vector store."""
        pass
    
    @abstractmethod
    async def add(self, collection_name: str, ids: List[str], vectors: List[List[float]], metadatas: List[Dict[str, Any]]):
        """Add vectors and their metadata to a collection."""
        pass

    @abstractmethod
    async def search(self, collection_name: str, query_vector: List[float], top_k: int) -> List[Tuple[str, float]]:
        """Search for the most similar vectors in a collection."""
        pass

class MilvusVectorStore(VectorStore):
    """
    A production-ready Milvus implementation of the VectorStore.
    Manages multiple collections for different types of embeddings.
    """
    def __init__(self, uri: str, token: str = ""):
        try:
            self.alias = "default"
            connections.connect(alias=self.alias, uri=uri, token=token)
        except Exception as e:
            raise VectorStoreError(f"Failed to connect to Milvus: {e}")
    
    async def close(self):
        """Closes the Milvus connection."""
        connections.disconnect(self.alias)

    def _get_collection(self, collection_name: str) -> Collection:
        if not utility.has_collection(collection_name, using=self.alias):
            raise VectorStoreError(f"Collection '{collection_name}' does not exist.")
        return Collection(collection_name, using=self.alias)

    async def setup(self, dimension: int, collection_name: str):
        """Creates a Milvus collection with a schema and a vector index."""
        def _setup_sync():
            if utility.has_collection(collection_name, using=self.alias):
                # Collection already exists, maybe check if index is also there.
                return
            
            # Define schema. PK is varchar, embedding is float_vector.
            # We also add source_video_id for potential metadata filtering.
            fields = [
                FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, max_length=256),
                FieldSchema(name="source_video_id", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension)
            ]
            schema = CollectionSchema(fields, f"Schema for {collection_name}")
            
            # Create collection
            collection = Collection(collection_name, schema, using=self.alias)
            
            # Create index (HNSW is a great production choice for speed/accuracy trade-off).
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 64, "efConstruction": 200},
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            collection.load()

        await asyncio.to_thread(_setup_sync)

    async def add(self, collection_name: str, ids: List[str], vectors: List[List[float]], metadatas: List[Dict[str, Any]]):
        """Adds data in batches to the specified Milvus collection."""
        def _add_sync():
            collection = self._get_collection(collection_name)
            entities = [ids, [m['source_video_id'] for m in metadatas], vectors]
            try:
                collection.insert(entities)
                collection.flush() # Ensure data is written to disk
            except Exception as e:
                raise VectorStoreError(f"Failed to insert data into '{collection_name}': {e}")

        await asyncio.to_thread(_add_sync)

    async def search(self, collection_name: str, query_vector: List[float], top_k: int) -> List[Tuple[str, float]]:
        """Searches a Milvus collection and returns (id, score) tuples."""
        def _search_sync():
            collection = self._get_collection(collection_name)
            search_params = {"metric_type": "COSINE", "params": {"ef": 10}}
            
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["pk"]
            )
            
            hits = results[0]
            return [(hit.entity.get('pk'), hit.distance) for hit in hits]

        return await asyncio.to_thread(_search_sync)