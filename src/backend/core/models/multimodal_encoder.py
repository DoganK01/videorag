"""
Wrapper for the ImageBind model for creating shared multi-modal embeddings.
"""
import asyncio
from typing import List, Dict, Union, Any
import torch
from ImageBind.imagebind.models import imagebind_model
from ImageBind.imagebind.models.imagebind_model import ModalityType
from ImageBind.imagebind import data

class EncoderError(Exception):
    """Custom exception for multi-modal encoding failures."""
    pass

class ImageBindEncoder:
    """
    A wrapper for Meta's ImageBind model to encode video, text, and audio
    into a common embedding space.
    """
    def __init__(self, device: Union[str, torch.device]):
        """
        Initializes and loads the ImageBind model.

        Args:
            device: The device to run inference on.
        """
        self.device = torch.device(device)
        try:
            self.model = imagebind_model.imagebind_huge(pretrained=True).to(self.device)
            self.model.eval()
        except Exception as e:
            raise EncoderError(f"Failed to load ImageBind model: {e}")

    def _encode_sync(self, video_paths: List[str] = [], text_list: List[str] = []) -> Dict[str, Any]:
        """
        Synchronous method to encode video and text data.

        Args:
            video_paths: A list of paths to video files.
            text_list: A list of strings.

        Returns:
            A dictionary containing embeddings keyed by modality.
            Example: {'video': tensor, 'text': tensor}
        """
        inputs = {}
        if not video_paths and not text_list:
            raise ValueError("At least one of video_paths or text_list must be provided.")

        try:
            if video_paths:
                inputs[ModalityType.VISION] = data.load_and_transform_video_data(video_paths, self.device)
            if text_list:
                inputs[ModalityType.TEXT] = data.load_and_transform_text(text_list, self.device)

            with torch.no_grad():
                embeddings = self.model(inputs)
            
            return {
                modality: embedding.cpu().numpy().tolist() 
                for modality, embedding in embeddings.items()
            }
        except Exception as e:
            raise EncoderError(f"Error during ImageBind encoding: {e}")

    async def encode_async(self, video_paths: List[str] = [], text_list: List[str] = []) -> Dict[str, Any]:
        """
        Asynchronously encodes data by running the sync method in a thread pool.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._encode_sync, video_paths, text_list)
    


async def main():
    encoder = ImageBindEncoder(device="cuda:0")

    text_inputs = ["This is a cat.", "This is a dog."]

    embeddings = await encoder.encode_async(text_list=text_inputs)

    print(embeddings)

if __name__ == "__main__":
    asyncio.run(main())