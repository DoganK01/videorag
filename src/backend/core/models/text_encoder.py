"""
Client for generating text embeddings using the OpenAI API.
This client is asynchronous and handles batching to respect API limits.
"""
import os
from typing import List, Optional

from openai import AsyncAzureOpenAI, APIError

class TextEmbeddingError(Exception):
    """Custom exception for text embedding failures."""
    pass

class OpenAITextEncoder:
    """
    An asynchronous client for OpenAI's text embedding models, specifically
    'text-embedding-3-small' as per the paper.
    """
    def __init__(self, model_name: str, api_key: Optional[str] = None, batch_size: int = 2048):
        """
        Initializes the asynchronous OpenAI client for embeddings.

        Args:
            model_name: The name of the embedding model (e.g., 'text-embedding-3-small').
            api_key: OpenAI API key. If None, it's read from the OPENAI_API_KEY environment variable.
            batch_size: The number of texts to process in a single API call.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        api_key = api_key or os.getenv("AZURE_EMBEDDING_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required. Set it via OPENAI_API_KEY env var or pass it directly.")
        
        self.client = AsyncAzureOpenAI(api_key=api_key,
                                       azure_endpoint=os.getenv("AZURE_EMBEDDING_ENDPOINT"),
                                       api_version=os.getenv("AZURE_EMBEDDING_API_VERSION"))

    async def encode_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of texts asynchronously, handling batching.

        Args:
            texts: A list of strings to be embedded.

        Returns:
            A list of embedding vectors.

        Raises:
            TextEmbeddingError: If the API call fails.
        """
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            try:
                response = await self.client.embeddings.create(
                    model=self.model_name,
                    input=batch
                )
                embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(embeddings)
            except APIError as e:
                raise TextEmbeddingError(f"OpenAI Embedding API call failed: {e}")
            except Exception as e:
                raise TextEmbeddingError(f"An unexpected error occurred during text embedding: {e}")
        return all_embeddings