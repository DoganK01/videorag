import asyncio
import json
import logging
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass

from app.api.dependencies import AppState
from app.core.schemas import RetrievedSource, CandidateClipInfo
from app.core.storage.metadata_store import MetadataStore
from app.core.storage.graph_store import GraphStore 

logger = logging.getLogger(__name__)

@dataclass
class RetrievedContext:
    query: str
    filtered_clips_info: List[CandidateClipInfo]

class RetrievalService:
    def __init__(self, app_state: AppState):
        self.state = app_state
        self.llm = app_state.llm_client
        self.graph_store: GraphStore = app_state.graph_store
        self.vector_store = app_state.vector_store
        self.chunk_store = app_state.chunk_store
        self.metadata_store: MetadataStore = app_state.metadata_store # Add the new store
        self.text_encoder = app_state.text_encoder
        self.multimodal_encoder = app_state.multimodal_encoder
        self.config = app_state.config

    async def retrieve(self, query: str) -> RetrievedContext:
        """Orchestrates the complete, high-fidelity multi-modal retrieval process."""
        textual_retrieval_task = self._textual_semantic_matching(query)
        visual_retrieval_task = self._visual_content_retrieval(query)
        
        textual_candidates, visual_candidates = await asyncio.gather(textual_retrieval_task, visual_retrieval_task)
        
        candidate_clips: Dict[str, CandidateClipInfo] = {res.retrieved_source.clip_id: res for res in textual_candidates}
        for res in visual_candidates:
            clip_id = res.retrieved_source.clip_id
            if clip_id not in candidate_clips:
                candidate_clips[clip_id] = res
            else:
                candidate_clips[clip_id].retrieved_source.retrieval_score = max(
                    candidate_clips[clip_id].retrieved_source.retrieval_score,
                    res.retrieved_source.retrieval_score
                )
        
        if not candidate_clips:
            return RetrievedContext(query=query, filtered_clips_info=[])

        logger.info(f"Found {len(candidate_clips)} unique candidate clips. Proceeding to LLM filtering.")
        filtered_clips_info = await self._llm_filter_clips(query, list(candidate_clips.values()))
        logger.info(f"LLM filtering complete. Retained {len(filtered_clips_info)} relevant clips.")

        return RetrievedContext(query=query, filtered_clips_info=filtered_clips_info)

    async def _textual_semantic_matching(self, query: str) -> List[CandidateClipInfo]:
        """
        Implements the full, uncompromised graph-based retrieval pipeline,
        now using the session-based context manager for database interaction.
        """
        logger.info(f"Performing full textual retrieval for: '{query}'")
        
        reformulation_prompt = f"Reformulate the question into a declarative sentence for semantic search: '{query}'"
        declarative_query = await self.llm.generate_for_indexing_async(reformulation_prompt)
        query_embedding = (await self.text_encoder.encode_async([declarative_query]))[0]
        
        try:
            async with self.graph_store.get_session() as session:
                logger.debug("Step (ii): Finding seed entities via vector search in graph.")
                entity_match_query = """
                CALL db.index.vector.queryNodes('entity-description-index', $top_k, $query_embedding) YIELD node
                RETURN node.entity_id AS entityId
                """
                top_k_entities = self.config['retrieval']['graph_top_k_entities']
                result = await session.run(
                    entity_match_query,
                    {"top_k": top_k_entities, "query_embedding": query_embedding}
                )
                seed_entity_ids = [record["entityId"] async for record in result]
                
                if not seed_entity_ids:
                    logger.warning("No seed entities found in graph for the query.")
                    return []
                logger.debug("Step (iii): Performing graph traversal and community detection.")
                community_detection_query = """
                MATCH (seed:Entity) WHERE seed.entity_id IN $seed_ids
                CALL {
                    WITH seed
                    MATCH (seed)-[r*1..2]-(neighbor)
                    WITH collect(seed) + collect(neighbor) AS all_nodes
                    UNWIND all_nodes as n
                    RETURN collect(DISTINCT n) as nodes
                }
                CALL gds.graph.project.subgraph('communityGraph', [node IN nodes | id(node)], '*') YIELD graphName
                CALL gds.louvain.stream('communityGraph') YIELD nodeId, communityId
                WITH gds.util.asNode(nodeId) AS node, communityId
                WITH communityId, node WHERE node.entity_id IN $seed_ids
                WITH DISTINCT communityId AS relevantCommunityIds
                CALL gds.louvain.stream('communityGraph') YIELD nodeId, communityId
                WHERE communityId IN relevantCommunityIds
                WITH gds.util.asNode(nodeId) AS communityNode
                MATCH (communityNode)-[:SOURCED_FROM]->(chunk:Chunk)
                RETURN DISTINCT chunk.chunk_id AS chunkId
                """
                chunk_result = await session.run(community_detection_query, {"seed_ids": seed_entity_ids})
                relevant_chunk_ids = [record["chunkId"] async for record in chunk_result]

        except Exception as e:
            logger.error(f"Graph retrieval failed: {e}. Ensure GDS is installed and graph schema is correct.", exc_info=True)
            return []

        if not relevant_chunk_ids:
            logger.warning("Graph traversal found no relevant source chunks.")
            return []
            
        logger.info(f"Found {len(relevant_chunk_ids)} relevant chunks from graph community.")

        relevant_chunks_map = await self.chunk_store.get_many_chunks(relevant_chunk_ids)
        chunk_texts = [chunk.content for chunk in relevant_chunks_map.values() if chunk]
        all_source_clip_ids: Set[str] = {
            clip_id for chunk in relevant_chunks_map.values() if chunk for clip_id in chunk.source_clip_ids
        }
        
        if not all_source_clip_ids:
            return []
        
        candidate_info_list = await self._fetch_candidate_info(list(all_source_clip_ids), "textual_graph")
        return candidate_info_list

    async def _visual_content_retrieval(self, query: str) -> List[CandidateClipInfo]:
        """Implements visual retrieval and fetches full clip context."""
        logger.info(f"Performing visual retrieval for: '{query}'")
        scene_extraction_prompt = f"Describe the core visual scene for this query: '{query}'."
        scene_description = await self.llm.generate_for_indexing_async(scene_extraction_prompt)
        query_vector = (await self.multimodal_encoder.encode_async(text_list=[scene_description]))['text'][0]
        
        top_k = self.config['retrieval']['visual_top_k']
        collection_name = self.config['storage']['vector_collections']['clips']
        search_results = await self.vector_store.search(collection_name, query_vector, top_k)
        
        clip_ids = [clip_id for clip_id, _ in search_results]
        candidate_info_list = await self._fetch_candidate_info(clip_ids, "visual_embedding")

        scores_map = {clip_id: score for clip_id, score in search_results}
        for info in candidate_info_list:
            info.retrieved_source.retrieval_score = scores_map.get(info.retrieved_source.clip_id, 0.0)
        return candidate_info_list

    async def _fetch_candidate_info(self, clip_ids: List[str], source_type: str) -> List[CandidateClipInfo]:
        """
        **NO MOCK.** Fetches all necessary data for a list of clip IDs by querying the real MetadataStore.
        """
        if not clip_ids:
            return []
        logger.debug(f"Fetching full candidate info for {len(clip_ids)} clips from MetadataStore.")
        
        metadata_docs = await self.metadata_store.get_clips_metadata(clip_ids)
        
        if not metadata_docs:
            logger.warning(f"MetadataStore returned no results for clip_ids: {clip_ids}")
            return []
            
        results = []
        for doc in metadata_docs:
            try:
                results.append(CandidateClipInfo(
                    retrieved_source=RetrievedSource(
                        clip_id=doc['clip_id'],
                        source_video_id=doc['source_video_id'],
                        start_time=doc['start_time'],
                        end_time=doc['end_time'],
                        retrieval_score=0.0, # Will be populated by the caller
                        source_type=source_type
                    ),
                    initial_visual_caption=doc['initial_caption'],
                    transcript=doc['transcript']
                ))
            except KeyError as e:
                logger.error(f"Metadata document for clip {doc.get('clip_id')} is missing field: {e}")
                continue # Skip malformed documents
        return results

    async def _llm_filter_clips(self, query: str, candidates: List[CandidateClipInfo]) -> List[CandidateClipInfo]:
        """Uses an LLM to judge the relevance of each candidate clip."""
        judge_prompt_template = """
        You are an expert relevance judge. Your task is to determine if a video clip is
        vitally important for answering the given user query. Base your judgment solely on
        the provided clip's visual caption and transcript.

        User Query: "{query}"

        Clip Content:
        ---
        {clip_content}
        ---

        Is this clip essential to answer the query? Respond with a single JSON object
        containing one key, "is_relevant", with a boolean value (true or false).
        """ 
        
        async def judge_one_clip(candidate: CandidateClipInfo) -> Tuple[CandidateClipInfo, bool]:
            prompt = judge_prompt_template.format(query=query, clip_content=candidate.combined_text)
            try:
                response_str = await self.llm.generate_for_indexing_async(
                    prompt, response_format="json_object", temperature=0.0
                )
                is_relevant = json.loads(response_str).get("is_relevant", False)
                return candidate, is_relevant
            except Exception as e:
                return candidate, False

        tasks = [judge_one_clip(clip) for clip in candidates]
        results = await asyncio.gather(*tasks)
        return [candidate for candidate, is_relevant in results if is_relevant]