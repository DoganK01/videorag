"""
Production-grade wrapper for the Azure OpenAI Whisper model for ASR.

This module provides a robust, asynchronous client that handles audio extraction
from video files and performs transcription using the cloud-based Whisper API.
It avoids intermediate disk I/O by processing audio streams entirely in-memory.
"""
import asyncio
import logging
import os
from typing import Optional, Literal, Tuple, Union

import subprocess
from openai import AsyncAzureOpenAI, APIError


from dotenv import load_dotenv
import argparse

logger = logging.getLogger(__name__)

class ASRError(Exception):
    """Custom exception for ASR failures."""
    pass

class AzureWhisperASR:
    """
    An advanced, asynchronous client for Azure OpenAI's Whisper-1 model.
    """
    def __init__(
        self,
        azure_endpoint: str,
        api_key: str,
        api_version: str,
        model_deployment_name: str,
        language: Optional[str] = "en",
        prompt: Optional[str] = None,
        response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] = "text",
        temperature: float = 0.0,
        timestamp_granularities: Optional[list[Literal["word", "segment"]]] = None
    ):
        """
        Initializes the asynchronous Azure OpenAI client for Whisper.
        (Constructor logic remains the same)
        """
        if not all([azure_endpoint, api_key, api_version, model_deployment_name]):
            raise ValueError("Azure endpoint, API key, API version, and model deployment name are required.")

        self.model_deployment_name = model_deployment_name
        
        self.transcription_options = {
            "language": language,
            "prompt": prompt,
            "response_format": response_format,
            "temperature": temperature,
        }
        if timestamp_granularities:
            self.transcription_options["timestamp_granularities"] = timestamp_granularities

        try:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version,
            )
        except Exception as e:
            raise ASRError(f"Failed to initialize Azure OpenAI client: {e}")

    def _extract_audio_with_ffmpeg(self, video_path: str) -> Tuple[bytes, str]:
        """
        Extracts audio from a video file directly using ffmpeg and returns it as bytes.
        This is a robust, synchronous, CPU-bound function.
        """
        try:
            logger.debug(f"Extracting audio from {video_path} with ffmpeg.")
            
            command = [
                'ffmpeg',
                '-i', video_path,
                '-vn',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-f', 'wav',
                'pipe:1'
            ]

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            audio_bytes, stderr = process.communicate()
            
            if process.returncode != 0:
                error_message = stderr.decode('utf-8', errors='ignore')
                raise ASRError(f"FFmpeg failed with code {process.returncode}: {error_message}")
            
            if not audio_bytes:
                raise ValueError("FFmpeg produced empty audio output.")

            filename = f"{os.path.basename(video_path)}.wav"
            
            return audio_bytes, filename

        except FileNotFoundError:
             raise ASRError(f"FFmpeg executable not found. Please ensure it is installed and in your system's PATH.")
        except Exception as e:
            raise ASRError(f"Failed to extract audio using ffmpeg for '{video_path}': {e}") from e


    async def transcribe_async(self, video_path: str) -> Union[str, dict]:
        """
        Asynchronously transcribes a video by extracting its audio via ffmpeg
        and sending it to the Azure Whisper API.
        """
        loop = asyncio.get_running_loop()
        
        try:
            audio_bytes, filename = await loop.run_in_executor(
                None, self._extract_audio_with_ffmpeg, video_path
            )
            
            in_memory_file_tuple = (filename, audio_bytes)
            
            logger.debug(f"Sending audio from {video_path} to Azure Whisper API.")
            transcription = await self.client.audio.transcriptions.create(
                model=self.model_deployment_name,
                file=in_memory_file_tuple,
                **self.transcription_options
            )
            
            if isinstance(transcription, str):
                return transcription.strip()
            elif hasattr(transcription, 'text') and transcription.text:
                text_content = transcription.text
                return text_content.strip() if text_content else ""
            else:
                return transcription

        except APIError as e:
            logger.error(f"Azure Whisper API call failed for '{video_path}': {e.status_code} - {e.response}")
            raise ASRError(f"Azure API error during transcription for '{video_path}': {e.message}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during transcription for '{video_path}': {e}", exc_info=True)
            raise ASRError(f"Transcription failed for '{video_path}'.") from e
        


async def test_transcription(video_file_path: str):
    """
    Bu modülü tek başına test etmek için bir async test fonksiyonu.
    """
    print("--- Azure Whisper ASR Test Başlatılıyor ---")
    
    print("Ortam değişkenleri yükleniyor...")
    load_dotenv()
    
    required_vars = ['AZURE_WHISPER_ENDPOINT', 'AZURE_WHISPER_API_KEY', 'AZURE_WHISPER_API_VERSION']
    if not all(os.getenv(var) for var in required_vars):
        print(f"Hata: Lütfen .env dosyanızda şu değişkenleri tanımlayın: {', '.join(required_vars)}")
        return

    print("AzureWhisperASR istemcisi oluşturuluyor...")
    try:
        asr_client = AzureWhisperASR(
            azure_endpoint=os.environ['AZURE_WHISPER_ENDPOINT'],
            api_key=os.environ['AZURE_WHISPER_API_KEY'],
            api_version=os.environ['AZURE_WHISPER_API_VERSION'],
            model_deployment_name="whisper"
        )
        
        print(f"'{video_file_path}' için transkripsiyon başlatılıyor. Bu işlem biraz sürebilir...")
        
        transcript = await asr_client.transcribe_async(video_file_path)
        
        print("\n--- TRANSKRİPSİYON SONUCU ---")
        if isinstance(transcript, str):
            print(transcript)
        else:
            import json
            print(json.dumps(transcript, indent=2))
        print("-----------------------------\n")

    except Exception as e:
        print(f"\n!!! BİR HATA OLUŞTU !!!")
        print(f"Hata Tipi: {type(e).__name__}")
        print(f"Hata Mesajı: {e}")
        
    finally:
        print("--- Test Tamamlandı ---")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Azure Whisper ASR modülünü test et.")
    parser.add_argument(
        "--video_path",
        type=str,
        required=True,
        help="Transkripti oluşturulacak video dosyasının tam yolu."
    )
    args = parser.parse_args()
    
    asyncio.run(test_transcription(args.video_path))