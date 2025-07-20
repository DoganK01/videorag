"""
Client for interacting with Large Language Models (LLMs) via the OpenAI API.
This client is asynchronous, making it suitable for high-performance, concurrent
applications. It supports different models for different tasks as specified in the paper.
"""

import os
from typing import Any

from async_lru import alru_cache
from openai import AsyncAzureOpenAI, APIError

from app.core.utils.decorators import async_retry


class LLMInferenceError(Exception):
    """Custom exception for LLM inference failures."""
    pass

class LLMClient:
    """
    An asynchronous client for OpenAI's Chat Completion models.
    """
    def __init__(
        self,
        indexer_model_name: str,
        generator_model_name: str,
    ):
        """
        Initializes the asynchronous OpenAI client.

        Args:
            indexer_model_name: The name of the model for indexing tasks (e.g., 'gpt-4o-mini').
            generator_model_name: The name of the model for final response generation (e.g., 'gpt-4-turbo').
            api_key: OpenAI API key. If None, it's read from the OPENAI_API_KEY environment variable.
        """
        self.indexer_model_name = indexer_model_name
        self.generator_model_name = generator_model_name
        api_key = os.getenv("AZURE_OPENAI_API_KEY_GPT")
        api_key_mini = os.getenv("AZURE_MINI_API_KEY")
        if not api_key or not api_key_mini:
            raise ValueError("OpenAI API key is required. Set it via AZURE_OPENAI_API_KEY_GPT and AZURE_MINI_API_KEY env var.")
        
        self.client = AsyncAzureOpenAI(api_key=api_key,
                                       azure_endpoint=os.getenv("AZURE_GPT_ENDPOINT"),
                                       api_version=os.getenv("AZURE_GPT_API_VERSION"))
        
        self.client_mini = AsyncAzureOpenAI(api_key=api_key_mini,
                                            azure_endpoint=os.getenv("AZURE_MINI_ENDPOINT"),
                                            api_version=os.getenv("AZURE_MINI_API_VERSION"))
    @alru_cache(maxsize=256)
    @async_retry(max_retries=3, delay=2, backoff=2)
    async def _generate_response_async(
        self,
        client: AsyncAzureOpenAI,
        model_name: str,
        prompt: str,
        system_prompt: str = "You are a helpful AI assistant.",
        **kwargs: Any,
    ) -> str:
        """
        Generic private method to generate a response from a specified model.

        Args:
            model_name: The OpenAI model to use.
            prompt: The user-facing prompt.
            system_prompt: The system instruction for the model.
            **kwargs: Additional parameters for the OpenAI API call (e.g., temperature, max_tokens).

        Returns:
            The generated text content from the model.
        
        Raises:
            LLMInferenceError: If the API call fails.
        """

        response_format = kwargs.pop("response_format", None)

        if response_format=="json_object":
            kwargs["response_format"] = { "type": "json_object" }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                **kwargs,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMInferenceError("API returned a null response content.")
            return content
        except APIError as e:
            raise LLMInferenceError(f"OpenAI API call failed: {e}")
        except Exception as e:
            raise LLMInferenceError(f"An unexpected error occurred during LLM inference: {e}")

    async def generate_for_indexing_async(self, prompt: str, **kwargs: Any) -> str:
        """
        Generates a response using the specified model for indexing tasks (e.g., entity extraction).
        Follows the paper's use of GPT-4o-mini for such tasks.
        """
        return await self._generate_response_async(
            client=self.client_mini,
            model_name=self.indexer_model_name,
            prompt=prompt,
            system_prompt="You are a precise data processing engine. Follow the user's instructions exactly.",
            **kwargs
        )

    async def generate_for_final_answer_async(self, prompt: str, **kwargs: Any) -> str:
        """
        Generates the final user-facing answer using the powerful generator model.
        """
        return await self._generate_response_async(
            client=self.client,
            model_name=self.generator_model_name,
            prompt=prompt,
            system_prompt="You are a helpful assistant that synthesizes information from provided context to answer questions comprehensively.",
            **kwargs
        )