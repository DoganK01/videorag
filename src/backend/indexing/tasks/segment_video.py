import os
import logging
import asyncio
from typing import List
from pathlib import Path

from app.core.schemas import VideoClip, TaskError  

logger = logging.getLogger(__name__)

async def segment_video(
    source_video_path: str,
    output_dir: str,
    clip_duration_seconds: int = 30
) -> List[VideoClip]:
    """
    Splits a source video into fixed-duration clips using FFmpeg.

    Args:
        source_video_path: The absolute path to the source video file.
        output_dir: The directory where video clips will be saved.
        clip_duration_seconds: The duration of each segment in seconds.

    Returns:
        A list of VideoClip objects containing metadata for each created clip.
    
    Raises:
        TaskError: If FFmpeg fails or the source video is not found.
    """
    if not os.path.exists(source_video_path):
        raise TaskError(f"Source video not found at: {source_video_path}")
    
    video_id = Path(source_video_path).stem
    clip_output_dir = os.path.join(output_dir, video_id, "clips")
    os.makedirs(clip_output_dir, exist_ok=True)
    
    output_template = os.path.join(clip_output_dir, f"{video_id}_clip_%04d.mp4")
    
    command = [
        "ffmpeg",
        "-i", source_video_path,
        "-c", "copy",
        "-map", "0",
        "-segment_time", str(clip_duration_seconds),
        "-f", "segment",
        "-reset_timestamps", "1",
        "-y", # Overwrite existing files
        output_template,
    ]
    
    logger.info(f"Running FFmpeg to segment video: {source_video_path}")
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise TaskError(f"FFmpeg failed with code {process.returncode}: {stderr.decode()}")
        
        logger.info(f"Successfully segmented video '{video_id}'")

        video_clips: List[VideoClip] = []
        for i, clip_file in enumerate(sorted(os.listdir(clip_output_dir))):
            start_time = i * clip_duration_seconds
            end_time = (i + 1) * clip_duration_seconds
            video_clips.append(VideoClip(
                clip_id=Path(clip_file).stem,
                source_video_id=video_id,
                start_time=start_time,
                end_time=end_time,
                clip_path=os.path.join(clip_output_dir, clip_file)
            ))
        
        return video_clips

    except Exception as e:
        logger.error(f"Error during video segmentation for {source_video_path}: {e}")
        raise TaskError(f"Video segmentation failed: {e}")