import asyncio
import logging
import os
import yaml
from typing import Dict, Any

from app.core.models import (
    AzureWhisperASR,
    MiniCPMVLM,
    LLMClient,
    OpenAITextEncoder,
    ImageBindEncoder
)
from app.core.storage import (
    Neo4jGraphStore,
    MilvusVectorStore,
    RedisChunkStore,
    MongoMetadataStore
)


logger = logging.getLogger(__name__)


async def initialize_resources(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    A reusable, centralized function to initialize and set up all required
    models and data stores based on the application configuration.

    Args:
        config: The loaded application configuration dictionary.

    Returns:
        A dictionary containing initialized 'models' and 'stores'.
    """
    logger.info("Initializing application resources (models and data stores)...")
    
    azure_conf = config['models']['azure_whisper']
    models = {
        'asr': AzureWhisperASR(
            azure_endpoint=os.environ['AZURE_WHISPER_ENDPOINT'],
            api_key=os.environ['AZURE_WHISPER_API_KEY'],
            api_version=os.environ['AZURE_WHISPER_API_VERSION'],
            model_deployment_name=azure_conf['deployment_name'],
            language=azure_conf.get('language'),
            response_format=azure_conf.get('response_format', 'text'),
            temperature=azure_conf.get('temperature', 0.0)
        ),
        'vlm': MiniCPMVLM(model_name=config['models']['vlm']),
        'llm': LLMClient(
            indexer_model_name=config['models']['llm_indexer'],
            generator_model_name=config['models']['llm_generator']
        ),
        'text_encoder': OpenAITextEncoder(model_name=config['models']['text_encoder']),
        'multimodal_encoder': ImageBindEncoder(device=config.get('models', {}).get('device', 'cpu')),
    }
    logger.info("All models initialized.")

    stores = {
        'graph': Neo4jGraphStore(
            uri=os.environ['NEO4J_URI'],
            user=os.environ['NEO4J_USER'],
            password=os.environ['NEO4J_PASSWORD'],
            database=os.environ['NEO4J_DATABASE']
        ),
        'vector': MilvusVectorStore(
            uri=os.environ['MILVUS_URI'],
            token=os.environ.get('MILVUS_TOKEN', '')
        ),
        'chunk': RedisChunkStore(redis_url=os.environ['REDIS_TCP']),
        'metadata': MongoMetadataStore(
            mongo_uri=os.environ['MONGO_URI'],
            database_name=os.environ['MONGO_DATABASE'],
        )
    }
    logger.info("All storage clients initialized.")

    logger.info("Setting up storage schemas and indexes...")
    await asyncio.gather(
        stores['graph'].setup(),
        stores['metadata'].setup(),
        *[
            stores['vector'].setup(
                collection_name=coll_conf['name'],
                dimension=coll_conf['dimension']
            ) for _, coll_conf in config['storage']['vector_collections'].items()
        ]
    )
    logger.info("Storage setup complete.")
    
    return {'models': models, 'stores': stores}



async def close_all_resources(stores: Dict[str, Any]):
    """A reusable function to gracefully close all database connections."""
    logger.info("Closing all data store connections...")
    await asyncio.gather(*[store.close() for store in stores.values()])
    logger.info("All resources have been gracefully shut down.")