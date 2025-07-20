"""
This package contains production-level wrappers for all machine learning models
used in the VideoRAG framework. Each module provides a class that encapsulates
model loading, inference, and necessary data preprocessing.

The design principles are:
1.  **Abstraction:** Each model is a self-contained class.
2.  **Configuration-Driven:** Model identifiers and devices are configurable.
3.  **Asynchronous Compatibility:** CPU/GPU-bound synchronous inference is
    wrapped in async methods to be compatible with asynchronous frameworks
    like FastAPI without blocking the event loop.
"""

from app.core.models.asr_model import AzureWhisperASR, ASRError
from app.core.models.llm_client import LLMClient, LLMInferenceError
from app.core.models.multimodal_encoder import ImageBindEncoder, EncoderError
from app.core.models.text_encoder import OpenAITextEncoder, TextEmbeddingError
from app.core.models.vlm_model import MiniCPMVLM, VLMError

__all__ = [
    "AzureWhisperASR",
    "ASRError",
    "LLMClient",
    "LLMInferenceError",
    "ImageBindEncoder",
    "EncoderError",
    "OpenAITextEncoder",
    "TextEmbeddingError",
    "MiniCPMVLM",
    "VLMError",
]