import logging
from typing import Dict, Any
from dataclasses import dataclass, field

from app.core.resources import initialize_resources, close_all_resources
from app.core.models import (
    LLMClient, OpenAITextEncoder, MiniCPMVLM, ImageBindEncoder, AzureWhisperASR
)
from app.core.storage import (
    GraphStore, VectorStore, ChunkStore, MetadataStore
)
logger = logging.getLogger(__name__)

@dataclass
class AppState:
    """
    A clean, typed container for all application-wide shared resources.
    This is attached to the main FastAPI app state.
    """
    config: Dict[str, Any]
    models: Dict[str, Any] = field(default_factory=dict)
    stores: Dict[str, Any] = field(default_factory=dict)
    
    # Provide typed properties for easy access in services
    @property
    def llm_client(self) -> LLMClient:
        return self.models['llm']
    
    @property
    def text_encoder(self) -> OpenAITextEncoder:
        return self.models['text_encoder']
        
    @property
    def vlm_model(self) -> MiniCPMVLM:
        return self.models['vlm']
        
    @property
    def multimodal_encoder(self) -> ImageBindEncoder:
        return self.models['multimodal_encoder']

    @property
    def asr_model(self) -> AzureWhisperASR: 
        return self.models['asr']

    @property
    def graph_store(self) -> GraphStore:
        return self.stores['graph']
        
    @property
    def vector_store(self) -> VectorStore:
        return self.stores['vector']
        
    @property
    def chunk_store(self) -> ChunkStore:
        return self.stores['chunk']
        
    @property
    def metadata_store(self) -> MetadataStore:
        return self.stores['metadata']


async def init_dependencies(config: Dict[str, Any]) -> AppState:
    """
    Initializes all dependencies at application startup by calling the
    centralized resource initializer.
    """
    logger.info("Initializing API dependencies...")
    
    resources = await initialize_resources(config)
    
    logger.info("Dependencies initialized successfully for API.")
    
    return AppState(config=config, **resources)

async def close_dependencies(app_state: AppState):
    """
    Closes all connections gracefully on application shutdown by calling
    the centralized resource closer.
    """
    logger.info("Closing API dependencies...")
    await close_all_resources(app_state.stores)