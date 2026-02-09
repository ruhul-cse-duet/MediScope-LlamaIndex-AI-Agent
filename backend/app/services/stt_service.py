"""Enhanced STT service with error handling and validation."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.exceptions import (
    ConfigurationError,
    ModelLoadError,
    ProcessingError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class SttService:
    """Speech-to-text service with multiple provider support."""
    
    def __init__(self) -> None:
        """Initialize STT service."""
        self.provider = settings.stt_provider
        logger.info(f"STT service initialized with provider: {self.provider}")
    
    def transcribe(self, audio_bytes: bytes, content_type: str | None) -> str:
        """Transcribe audio to text.
        
        Args:
            audio_bytes: Audio data
            content_type: MIME type of audio
            
        Returns:
            str: Transcribed text
            
        Raises:
            ConfigurationError: If provider is misconfigured
            ProcessingError: If transcription fails
        """
        if not audio_bytes:
            raise ProcessingError("Empty audio data")
        
        logger.debug(
            f"Transcribing audio | "
            f"Provider: {self.provider} | "
            f"Size: {len(audio_bytes)} bytes | "
            f"Type: {content_type}"
        )
        
        if self.provider == "faster_whisper":
            return self._faster_whisper(audio_bytes)
        
        if self.provider == "openai":
            return self._openai(audio_bytes, content_type)
        
        if self.provider == "none":
            raise ConfigurationError(
                "STT provider is not configured",
                details={"provider": "none"},
            )
        
        raise ConfigurationError(
            f"Unknown STT provider: {self.provider}",
            details={"provider": self.provider},
        )
    
    def _faster_whisper(self, audio_bytes: bytes) -> str:
        """Transcribe using Faster Whisper.
        
        Args:
            audio_bytes: Audio data
            
        Returns:
            str: Transcribed text
            
        Raises:
            ModelLoadError: If dependencies are missing
            ProcessingError: If transcription fails
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            logger.error("faster-whisper not installed")
            raise ModelLoadError(
                "faster-whisper is not installed",
                details={"error": str(exc)},
            )
        
        temp_path = None
        try:
            # Write audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            logger.debug(f"Saved audio to temp file: {temp_path}")
            
            # Load model
            try:
                model = WhisperModel("base", device="cpu", compute_type="int8")
            except Exception as exc:
                logger.error(f"Failed to load Whisper model: {str(exc)}", exc_info=True)
                raise ModelLoadError(
                    "Failed to load Whisper model",
                    details={"error": str(exc)},
                )
            
            # Transcribe
            try:
                segments, info = model.transcribe(temp_path)
                transcript = " ".join(segment.text for segment in segments)
                
                logger.debug(
                    f"Whisper transcription complete | "
                    f"Duration: {info.duration:.2f}s | "
                    f"Text length: {len(transcript)} chars"
                )
                
                return transcript.strip()
            
            except Exception as exc:
                logger.error(f"Whisper transcription failed: {str(exc)}", exc_info=True)
                raise ProcessingError(
                    "Transcription failed",
                    details={"error": str(exc)},
                )
        
        finally:
            # Clean up temp file
            if temp_path:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as exc:
                    logger.warning(f"Failed to clean up temp file: {str(exc)}")
    
    def _openai(self, audio_bytes: bytes, content_type: str | None) -> str:
        """Transcribe using OpenAI Whisper API.
        
        Args:
            audio_bytes: Audio data
            content_type: MIME type
            
        Returns:
            str: Transcribed text
            
        Raises:
            ConfigurationError: If API key is missing
            ServiceUnavailableError: If API call fails
        """
        if not settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured",
                details={"provider": "openai"},
            )
        
        try:
            headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
            files = {
                "file": ("audio.wav", audio_bytes, content_type or "audio/wav")
            }
            data = {"model": "whisper-1"}
            
            logger.debug("Calling OpenAI Whisper API")
            
            with httpx.Client(timeout=settings.stt_timeout) as client:
                response = client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data,
                )
                response.raise_for_status()
                payload = response.json()
            
            transcript = payload.get("text", "").strip()
            
            logger.debug(
                f"OpenAI transcription complete | "
                f"Text length: {len(transcript)} chars"
            )
            
            return transcript
        
        except httpx.TimeoutException as exc:
            logger.error("OpenAI Whisper API timeout")
            raise ServiceUnavailableError(
                "Transcription service timed out",
                details={"timeout": settings.stt_timeout},
            )
        
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"OpenAI Whisper API error: {exc.response.status_code}",
                exc_info=True,
            )
            raise ServiceUnavailableError(
                "Transcription service error",
                details={
                    "status_code": exc.response.status_code,
                    "response": exc.response.text[:500],
                },
            )
        
        except Exception as exc:
            logger.error(f"OpenAI Whisper API failed: {str(exc)}", exc_info=True)
            raise ServiceUnavailableError(
                "Transcription service failed",
                details={"error": str(exc)},
            )


stt_service = SttService()
