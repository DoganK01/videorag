"""
Utilities for processing video files using FFmpeg.

This module provides asynchronous, production-ready functions for common
video operations like frame extraction, which are required by the indexing pipeline.
"""
import asyncio
import os
import logging
from typing import List

from app.core.schemas import TaskError

logger = logging.getLogger(__name__)

async def extract_frames(
    video_path: str,
    output_dir: str,
    num_frames: int
) -> List[str]:
    """
    Extracts a specified number of frames, evenly spaced, from a video file.

    This function calculates the duration of the video, determines the timestamps
    for evenly spaced frames, and uses FFmpeg to extract them.

    Args:
        video_path: The absolute path to the video file.
        output_dir: The directory where the extracted frames will be saved.
        num_frames: The total number of frames to extract.

    Returns:
        A list of absolute paths to the extracted frame image files.

    Raises:
        TaskError: If FFprobe or FFmpeg commands fail.
    """
    if not os.path.exists(video_path):
        raise TaskError(f"Video file not found: {video_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Get video duration using ffprobe
    ffprobe_command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *ffprobe_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise TaskError(f"ffprobe failed: {stderr.decode()}")
        duration = float(stdout.decode().strip())
    except Exception as e:
        raise TaskError(f"Failed to get video duration for {video_path}: {e}")

    if duration <= 0:
        logger.warning(f"Video {video_path} has zero or negative duration. Skipping frame extraction.")
        return []

    # 2. Calculate timestamps for evenly spaced frames
    interval = duration / (num_frames + 1)
    timestamps = [interval * (i + 1) for i in range(num_frames)]
    
    # 3. Use FFmpeg to extract frames at the calculated timestamps
    output_paths = []
    extraction_tasks = []

    async def extract_one_frame(timestamp: float, frame_index: int):
        output_filename = os.path.join(output_dir, f"frame_{frame_index:04d}.jpg")
        ffmpeg_command = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2", # High-quality JPEG
            "-y", # Overwrite if exists
            output_filename,
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise TaskError(f"ffmpeg frame extraction failed at timestamp {timestamp}: {stderr.decode()}")
        
        output_paths.append(output_filename)

    for i, ts in enumerate(timestamps):
        extraction_tasks.append(extract_one_frame(ts, i))
        
    try:
        await asyncio.gather(*extraction_tasks)
    except Exception as e:
        # Clean up partially extracted frames on failure
        for path in output_paths:
            if os.path.exists(path):
                os.remove(path)
        raise TaskError(f"One or more frame extractions failed for {video_path}: {e}")

    logger.info(f"Successfully extracted {len(output_paths)} frames from {video_path}")
    
    # Return sorted list to ensure consistent order
    return sorted(output_paths)