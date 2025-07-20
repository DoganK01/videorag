"""
Interface and implementation for the graph database store.
This module handles storing and retrieving entities and their relationships.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, EagerResult, AsyncSession
from app.core.schemas import KnowledgeGraphNode, KnowledgeGraphRelationship

class GraphStoreError(Exception):
    """Custom exception for graph store operations."""
    pass

class GraphStore(ABC):
    """Abstract Base Class for a graph store."""
    @abstractmethod
    async def setup(self):
        """Prepare the graph store (e.g., create indexes, constraints)."""
        pass
    
    @abstractmethod
    async def close(self):
        """Close the connection to the graph store."""
        pass

    @abstractmethod
    async def add_or_update_entity(self, entity: KnowledgeGraphNode):
        """Add a new entity or update it if it exists."""
        pass

    @abstractmethod
    async def add_relationship(self, relationship: KnowledgeGraphRelationship):
        """Add a relationship between two entities."""
        pass
    
    @abstractmethod
    async def get_entities_by_ids(self, entity_ids: List[str]) -> List[KnowledgeGraphNode]:
        """Retrieve a list of entities by their IDs."""
        pass

class Neo4jGraphStore(GraphStore):
    """
    A production-ready Neo4j implementation of the GraphStore with managed sessions.
    """
    def __init__(self, uri: str, user: str, password: str, database: str):
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    async def close(self):
        """Closes the Neo4j driver connection."""
        await self._driver.close()

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """
        Provides a managed Neo4j session that is automatically closed.
        This is the PREFERRED way to interact with the database.
        """
        session: Optional[AsyncSession] = None
        try:
            session = self._driver.session(database=self.database)
            yield session
        finally:
            if session:
                await session.close()
    
    async def setup(self):
        """Creates necessary constraints and vector indexes in Neo4j."""
        constraint_query = "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE"
        chunk_constraint_query = "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE"
        vector_index_query = """
        CREATE VECTOR INDEX `entity-description-index` IF NOT EXISTS FOR (e:Entity) ON (e.descriptionEmbedding)
        OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }}
        """
        async with self.get_session() as session:
            await session.run(constraint_query)
            await session.run(chunk_constraint_query)
            await session.run(vector_index_query)

    # This private helper can remain for cases outside a session, like the retrieval service query.
    async def _execute_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> EagerResult:
        """Helper to execute a Cypher query with a new session."""
        async with self.get_session() as session:
            result = await session.run(query, params)
            return await result.consume()

    async def add_or_update_entity(self, session: AsyncSession, entity: KnowledgeGraphNode) -> Optional[str]:
        """
        Adds or updates an entity WITHIN A GIVEN SESSION. Returns the existing description on match.
        """
        query = """
        MERGE (e:Entity {entity_id: $entity_id})
        ON CREATE SET 
            e.label = $label, e.description = $description, 
            e.descriptionEmbedding = $embedding, e.last_updated_timestamp = timestamp()
        WITH e, CASE WHEN e.description = $description THEN true ELSE false END AS is_creation
        WITH e, is_creation, CASE WHEN NOT is_creation THEN e.description ELSE null END as old_description
        SET e.label = $label, e.description = $description, e.descriptionEmbedding = $embedding
        RETURN old_description
        """
        params = {
            "entity_id": entity.entity_id, "label": entity.label,
            "description": entity.description, "embedding": entity.description_embedding
        }
        result = await session.run(query, params)
        record = await result.single()
        if record and record["old_description"] and record["old_description"] != entity.description:
            return record["old_description"]
        return None

    async def add_relationship(self, session: AsyncSession, rel: KnowledgeGraphRelationship):
        """
        Creates a relationship between two existing nodes WITHIN A GIVEN SESSION.
        This query is now robust enough to handle both Entity-Entity and Entity-Chunk relationships.
        """
        entity_rel_query = """
        MATCH (source:Entity {entity_id: $source_id})
        MATCH (target:Entity {entity_id: $target_id})
        MERGE (source)-[r:RELATED_TO {type: $rel_type}]->(target)
        ON CREATE SET r.description = $rel_description
        """
        chunk_rel_query = """
        MATCH (source:Entity {entity_id: $source_id})
        MATCH (target:Chunk {chunk_id: $target_id})
        MERGE (source)-[r:SOURCED_FROM]->(target)
        """
        
        if rel.type == "SOURCED_FROM":
            params = {"source_id": rel.source_id, "target_id": rel.target_id}
            await session.run(chunk_rel_query, params)
        else:
            params = {
                "source_id": rel.source_id, "target_id": rel.target_id,
                "rel_type": rel.type, "rel_description": rel.description
            }
            await session.run(entity_rel_query, params)

    async def get_entities_by_ids(self, session: AsyncSession, entity_ids: List[str]) -> List[KnowledgeGraphNode]:
        """Retrieves full entity data for a list of IDs WITHIN A GIVEN SESSION."""
        query = "MATCH (e:Entity) WHERE e.entity_id IN $entity_ids RETURN e"
        params = {"entity_ids": entity_ids}
        result = await session.run(query, params)
        return [KnowledgeGraphNode(**record["e"]) async for record in result]