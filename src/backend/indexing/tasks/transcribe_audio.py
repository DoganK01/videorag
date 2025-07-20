import asyncio
import logging
from typing import List

from app.core.models import AzureWhisperASR
from app.core.schemas import VideoClip, AudioTranscript

logger = logging.getLogger(__name__)

async def transcribe_audio(
    video_clips: List[VideoClip],
    asr_model: AzureWhisperASR
) -> List[AudioTranscript]:
    """
    Generates audio transcripts for a list of video clips concurrently.

    Args:
        video_clips: A list of VideoClip objects.
        asr_model: An initialized instance of the ASR model wrapper.

    Returns:
        A list of AudioTranscript objects.
    """
    logger.info(f"Starting audio transcription for {len(video_clips)} clips.")
    
    async def transcribe_one_clip(clip: VideoClip) -> AudioTranscript:
        try:
            transcript_text = await asr_model.transcribe_async(clip.clip_path)
            await asyncio.sleep(60)
            return AudioTranscript(clip_id=clip.clip_id, text=transcript_text)
        except Exception as e:
            logger.error(f"Failed to transcribe clip {clip.clip_id}: {e}")
            await asyncio.sleep(60)
            return AudioTranscript(clip_id=clip.clip_id, text="")

    tasks = [transcribe_one_clip(clip) for clip in video_clips]
    transcripts = await asyncio.gather(*tasks)
    
    logger.info("Finished audio transcription for all clips.")
    return [t for t in transcripts if t is not None]