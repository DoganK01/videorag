import asyncio
import logging
from typing import List, Dict
import os

from app.core.models import MiniCPMVLM
from app.core.schemas import VideoClip, AudioTranscript, VisualCaption
from app.indexing.utils.video_processor import extract_frames 

logger = logging.getLogger(__name__)

async def generate_initial_captions(
    video_clips: List[VideoClip],
    transcripts: Dict[str, AudioTranscript], 
    vlm_model: MiniCPMVLM,
    frames_per_clip: int,
    temp_frame_dir: str
) -> List[VisualCaption]:
    """
    Generates initial visual captions for a list of video clips concurrently,
    using their transcripts as context.

    Args:
        video_clips: A list of VideoClip objects.
        transcripts: A dictionary mapping clip_id to AudioTranscript objects.
        vlm_model: An initialized instance of the VLM model wrapper.
        frames_per_clip: The number of frames to sample (k in the paper).
        temp_frame_dir: Directory to temporarily store extracted frames.

    Returns:
        A list of VisualCaption objects.
    """
    logger.info(f"Starting initial caption generation for {len(video_clips)} clips.")

    async def caption_one_clip(clip: VideoClip) -> VisualCaption:
        try:
            clip_frame_dir = os.path.join(temp_frame_dir, clip.clip_id)
            os.makedirs(clip_frame_dir, exist_ok=True)
            frame_paths = await extract_frames(
                video_path=clip.clip_path,
                output_dir=clip_frame_dir,
                num_frames=frames_per_clip
            )

            transcript_text = transcripts.get(clip.clip_id, AudioTranscript(clip_id=clip.clip_id, text="")).text
            
            caption_text = await vlm_model.generate_caption_async(frame_paths, transcript_text)
            
            for path in frame_paths:
                os.remove(path)
            os.rmdir(clip_frame_dir)
            
            return VisualCaption(clip_id=clip.clip_id, text=caption_text)
        except Exception as e:
            logger.error(f"Failed to generate caption for clip {clip.clip_id}: {e}")
            return VisualCaption(clip_id=clip.clip_id, text="")

    tasks = [caption_one_clip(clip) for clip in video_clips]
    captions = await asyncio.gather(*tasks)

    logger.info("Finished initial caption generation for all clips.")
    return [c for c in captions if c is not None]