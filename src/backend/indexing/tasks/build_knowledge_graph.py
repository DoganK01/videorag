import asyncio
import logging
from typing import List
import json

from app.core.models import LLMClient, OpenAITextEncoder 
from app.core.storage import GraphStore
from app.core.schemas import TextChunk, KnowledgeGraphNode, KnowledgeGraphRelationship, TaskError
from app.core.utils.decorators import async_retry

logger = logging.getLogger(__name__)


SEMANTIC_SYNTHESIS_PROMPT_TEMPLATE = """
You are a knowledge graph curator. Your task is to synthesize two descriptions of the
same entity into a single, more comprehensive, and coherent description. Do not lose
any unique information from either description. Combine them logically and concisely.

Existing Description in Knowledge Graph:
---
{existing_description}
---

New Information found in a video clip:
---
{new_description}
---

Synthesized, Comprehensive Description:
"""

KG_EXTRACTION_PROMPT_TEMPLATE = """
From the following text chunk, extract key entities and their relationships.
Entities should be concepts, people, places, or technologies.
Relationships should describe how entities are connected.
The text is derived from video clips and may contain both visual descriptions and spoken dialogue.
Your output MUST be a valid JSON object with two keys: "entities" and "relationships".
"entities" should be a list of objects, each with "entity_id", "label", and "description". The 'entity_id' should be a normalized, snake_case string.
"relationships" should be a list of objects, each with "source_id", "target_id", "type", and "description".

Example:
Text: "In the video, Jeff Dean explains how the Transformer architecture, developed at Google, is fundamental to large language models."
Output:
{{
  "entities": [
    {{"entity_id": "jeff_dean", "label": "Jeff Dean", "description": "A person who explains the Transformer architecture."}},
    {{"entity_id": "transformer_architecture", "label": "Transformer Architecture", "description": "A neural network architecture fundamental to LLMs, developed at Google."}},
    {{"entity_id": "google", "label": "Google", "description": "The company where the Transformer architecture was developed."}}
  ],
  "relationships": [
    {{"source_id": "jeff_dean", "target_id": "transformer_architecture", "type": "EXPLAINS", "description": "Jeff Dean explains the Transformer architecture."}},
    {{"source_id": "transformer_architecture", "target_id": "google", "type": "DEVELOPED_AT", "description": "The Transformer architecture was developed at Google."}}
  ]
}}

Now, process the following text:
---
{text_chunk}
---
"""

async def build_knowledge_graph(
    text_chunks: List[TextChunk],
    llm_client: LLMClient,
    text_encoder: OpenAITextEncoder,
    graph_store: GraphStore
):
    """
    Processes text chunks to extract a knowledge graph, synthesizes entity
    descriptions with existing knowledge, and persists all data.
    """
    logger.info(f"Starting knowledge graph construction for {len(text_chunks)} chunks.")

    @async_retry(max_retries=3, delay=5)
    async def process_one_chunk(chunk: TextChunk):
        try:
            async with graph_store.get_session() as session:
                await session.run("MERGE (c:Chunk {chunk_id: $chunk_id})", chunk_id=chunk.chunk_id)

                prompt = KG_EXTRACTION_PROMPT_TEMPLATE.format(text_chunk=chunk.content)
                response_json_str = await llm_client.generate_for_indexing_async(prompt, response_format="json_object") 
                kg_data = json.loads(response_json_str)

                newly_extracted_entities = [KnowledgeGraphNode(**e) for e in kg_data.get("entities", [])]
                newly_extracted_relationships = [KnowledgeGraphRelationship(**r) for r in kg_data.get("relationships", [])]

                if not newly_extracted_entities:
                    logger.debug(f"No entities extracted from chunk {chunk.chunk_id}.")
                    return

                new_entity_descriptions = [entity.description for entity in newly_extracted_entities]
                new_description_embeddings = await text_encoder.encode_async(new_entity_descriptions)
                for i, entity in enumerate(newly_extracted_entities):
                    entity.description_embedding = new_description_embeddings[i]
                
                for entity in newly_extracted_entities:
                    existing_description = await graph_store.add_or_update_entity(session, entity)
                    
                    if existing_description:
                        logger.info(f"Synthesizing description for existing entity: '{entity.entity_id}'")
                        
                        synthesis_prompt = SEMANTIC_SYNTHESIS_PROMPT_TEMPLATE.format(
                            existing_description=existing_description,
                            new_description=entity.description
                        )
                        
                        synthesized_description = await llm_client.generate_for_indexing_async(synthesis_prompt)
                        synthesized_embedding = (await text_encoder.encode_async([synthesized_description]))[0]
                        
                        entity.description = synthesized_description
                        entity.description_embedding = synthesized_embedding
                        
                        await graph_store.add_or_update_entity(session, entity)

                    await graph_store.add_relationship(session, KnowledgeGraphRelationship(
                        source_id=entity.entity_id,
                        target_id=chunk.chunk_id,
                        type="SOURCED_FROM",
                        description=f"Entity '{entity.label}' was sourced from chunk {chunk.chunk_id}."
                    ))

                for rel in newly_extracted_relationships:
                    await graph_store.add_relationship(session, rel)

        except Exception as e:
            logger.error(f"Failed to process chunk {chunk.chunk_id} for KG after all retries.", exc_info=True)
            raise

    tasks = [process_one_chunk(chunk) for chunk in text_chunks]
    await asyncio.gather(*tasks, return_exceptions=True) # return_exceptions=True prevents one failed task from stopping all others

    logger.info("Finished knowledge graph construction.")