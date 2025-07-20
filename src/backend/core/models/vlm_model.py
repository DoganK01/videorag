"""
Wrapper for the MiniCPM-V model for vision-language tasks, such as generating
captions from video frames and associated text.
"""
import asyncio
from typing import List
from PIL import Image
from openai import OpenAI

class VLMError(Exception):
    """Custom exception for VLM failures."""
    pass

class MiniCPMVLM:
    """
    A wrapper for the MiniCPM-V model from OpenBMB.
    """
    def __init__(self, model_name: str):
        """
        Initializes and loads the VLM model and tokenizer.

        Args:
            model_name: The Hugging Face model identifier (e.g., 'openbmb/MiniCPM-Llama3-V-2_5').
            device: The device to run inference on.
        """
        self.model_name = model_name

        try:
            self.client = OpenAI(
                base_url="XX",
                api_key="EMPTY"
            )
            
        except Exception as e:
            raise VLMError(f"Failed to load VLM model '{model_name}': {e}")
    

    def _generate_caption_sync(self, image_paths: List[str], text_prompt: str) -> str:
        """
        Synchronous method to generate a caption from images and text.

        Args:
            image_paths: List of paths to image files.
            text_prompt: A textual prompt (e.g., transcript, keywords).

        Returns:
            The generated caption.
        """
        try:
            images = [Image.open(p).convert("RGB") for p in image_paths]

            prompt = f"Context from transcript: '{text_prompt}'. \nImages to focus: '{images}'. \nBased on the provided images and transcript, describe the key visual elements, actions, and overall scene."
            
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise VLMError(f"Error during VLM caption generation: {e}")

    async def generate_caption_async(self, image_paths: List[str], text_prompt: str) -> str:
        """
        Asynchronously generates a caption by running the sync method in a thread pool.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._generate_caption_sync, image_paths, text_prompt)