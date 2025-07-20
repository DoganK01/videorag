# src/app/core/storage/metadata_store.py
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timezone

import motor.motor_asyncio
from pymongo.errors import ConnectionFailure, OperationFailure

from app.core.schemas import CandidateClipInfo, RetrievedSource

logger = logging.getLogger(__name__)

class MetadataStoreError(Exception):
    """Custom exception for metadata store operations."""
    pass

class MetadataStore(ABC):
    """
    Abstract Base Class defining the contract for a metadata store.
    This store holds rich, structured information about each processed video clip.
    """
    @abstractmethod
    async def setup(self):
        """Prepare the store (e.g., create indexes)."""
        pass
        
    @abstractmethod
    async def close(self):
        """Close the connection to the store."""
        pass
    
    @abstractmethod
    async def add_clip_metadata(self, clip_info: Dict):
        """Adds or updates metadata for a single clip during indexing."""
        pass
    
    @abstractmethod
    async def get_clips_metadata(self, clip_ids: List[str]) -> List[Dict]:
        """Fetches full metadata documents for multiple clips by their IDs."""
        pass

    @abstractmethod
    async def get_all_videos_summary(self, search_query: Optional[str] = None) -> List[Dict]:
        """
        Fetches an efficient summary of all unique indexed videos,
        with optional full-text search.
        """
        pass

class MongoMetadataStore(MetadataStore):
    """
    A production-ready MongoDB implementation for storing and retrieving
    structured metadata for video clips.
    """
    def __init__(self, mongo_uri: str, database_name: str, collection_name: str):
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
        except ConnectionFailure as e:
            raise MetadataStoreError(f"Could not connect to MongoDB at {mongo_uri}: {e}")

    async def close(self):
        self.client.close()
        logger.info("MongoDB connection closed.")
        
    async def setup(self):
        """
        Creates essential indexes for performant queries. This is idempotent.
        """
        try:
            await self.collection.create_index("clip_id", unique=True)
            
            await self.collection.create_index(
                [
                    ("source_video_id", "text"),
                    ("initial_caption", "text"),
                    ("transcript", "text")
                ],
                name="search_text_index"
            )
            logger.info(f"Indexes on collection '{self.collection.name}' ensured.")
        except OperationFailure as e:
            logger.warning(f"Could not apply index on '{self.collection.name}' (might already exist): {e}")
        except Exception as e:
            raise MetadataStoreError(f"Failed to setup MongoDB indexes: {e}")

    async def add_clip_metadata(self, clip_data: Dict):
        """
        Adds or updates a document for a clip. It now automatically adds
        a `createdAt` timestamp on the first insertion.
        """
        clip_id = clip_data.get("clip_id")
        if not clip_id:
            raise ValueError("clip_data must contain a 'clip_id'")

        update_doc = {
            '$set': clip_data,
            '$setOnInsert': {'createdAt': datetime.now(timezone.utc)}
        }
        
        await self.collection.update_one(
            {'clip_id': clip_id},
            update_doc,
            upsert=True
        )

    async def get_clips_metadata(self, clip_ids: List[str]) -> List[Dict]:
        """Fetches full metadata documents for a list of clip IDs."""
        if not clip_ids:
            return []
        cursor = self.collection.find({'clip_id': {'$in': clip_ids}})
        return await cursor.to_list(length=len(clip_ids))

    async def get_all_videos_summary(self, search_query: Optional[str] = None) -> List[Dict]:
        """
        Fetches a summary for each unique source video using an aggregation pipeline.
        This is highly efficient as all processing is done inside the database.
        """
        pipeline = []

        if search_query:
            pipeline.append({
                '$match': { '$text': { '$search': search_query } }
            })
        pipeline.append({
            '$group': {
                '_id': '$source_video_id', # Group all clips by their parent video ID
                'clip_count': {'$sum': 1}, # Count how many clips are in each group
                'total_duration': {'$max': '$end_time'}, # Get the end time of the last clip
                'indexedAt': {'$min': '$createdAt'} # Get the timestamp of the first clip indexed for this video
            }
        })
        
        pipeline.append({
            '$project': {
                'id': '$_id',
                'title': '$_id',
                'clip_count': 1,
                'duration_seconds': '$total_duration',
                'indexedAt': 1,
                '_id': 0 # Exclude MongoDB's default _id field from the final output
            }
        })

        # Sort the final results, with the most recently indexed videos first.
        pipeline.append({
            '$sort': {'indexedAt': -1}
        })
        
        logger.debug(f"Executing MongoDB aggregation pipeline: {pipeline}")
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(length=None) # Fetch all results