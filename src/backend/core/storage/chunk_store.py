"""
Interface and implementation for a key-value store to hold raw text chunks.
This store maps a chunk_id to its textual content.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict

import redis.asyncio as redis
from app.core.schemas import TextChunk

class ChunkStoreError(Exception):
    """Custom exception for chunk store operations."""
    pass

class ChunkStore(ABC):
    """Abstract Base Class for a chunk store."""
    @abstractmethod
    async def close(self):
        """Close the connection to the chunk store."""
        pass
    
    @abstractmethod
    async def add_chunks(self, chunks: Dict[str, TextChunk]):
        """Add a batch of chunks to the store."""
        pass

    @abstractmethod
    async def get_chunk(self, chunk_id: str) -> Optional[TextChunk]:
        """Retrieve a single chunk by its ID."""
        pass
    
    @abstractmethod
    async def get_many_chunks(self, chunk_ids: List[str]) -> Dict[str, Optional[TextChunk]]:
        """Retrieve multiple chunks by their IDs."""
        pass

class RedisChunkStore(ChunkStore):
    """
    A production-ready Redis implementation of the ChunkStore.
    It uses an async client and connection pooling for high performance.
    """
    def __init__(self, redis_url: str):
        try:
            self.pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)
            self.client = redis.Redis(connection_pool=self.pool)
        except Exception as e:
            raise ChunkStoreError(f"Failed to connect to Redis: {e}")

    async def close(self):
        """Closes the Redis connection pool."""
        await self.pool.disconnect()

    async def add_chunks(self, chunks: Dict[str, TextChunk]):
        """Uses a pipeline to add multiple chunks atomically and efficiently."""
        try:
            async with self.client.pipeline(transaction=True) as pipe:
                for chunk_id, chunk_data in chunks.items():
                    await pipe.set(f"chunk:{chunk_id}", chunk_data.model_dump_json())
                await pipe.execute()
        except Exception as e:
            raise ChunkStoreError(f"Failed to add chunks to Redis: {e}")

    async def get_chunk(self, chunk_id: str) -> Optional[TextChunk]:
        """Retrieves and deserializes a single chunk."""
        try:
            json_data = await self.client.get(f"chunk:{chunk_id}")
            if json_data:
                return TextChunk.model_validate_json(json_data)
            return None
        except Exception as e:
            raise ChunkStoreError(f"Failed to get chunk '{chunk_id}' from Redis: {e}")
            
    async def get_many_chunks(self, chunk_ids: List[str]) -> Dict[str, Optional[TextChunk]]:
        """Uses MGET for efficient batch retrieval of chunks."""
        if not chunk_ids:
            return {}
        
        prefixed_ids = [f"chunk:{cid}" for cid in chunk_ids]
        try:
            json_results = await self.client.mget(prefixed_ids)
            
            results_dict = {}
            for i, json_data in enumerate(json_results):
                original_id = chunk_ids[i]
                if json_data:
                    results_dict[original_id] = TextChunk.model_validate_json(json_data)
                else:
                    results_dict[original_id] = None
            return results_dict
        except Exception as e:
            raise ChunkStoreError(f"Failed to get multiple chunks from Redis: {e}")