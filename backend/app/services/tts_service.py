"""Enhanced TTS service with error handling and validation."""

from __future__ import annotations

import io
import logging
from typing import Tuple

from app.core.config import settings
from app.core.exceptions import ConfigurationError, ModelLoadError, ProcessingError

logger = logging.getLogger(__name__)


class TtsService:
    """Text-to-speech service with multiple provider support."""
    
    def __init__(self) -> None:
        """Initialize TTS service."""
        self.provider = settings.tts_provider
        logger.info(f"TTS service initialized with provider: {self.provider}")
    
    def synthesize(self, text: str) -> Tuple[bytes, str]:
        """Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Tuple[bytes, str]: Audio bytes and media type
            
        Raises:
            ConfigurationError: If provider is misconfigured
            ProcessingError: If synthesis fails
        """
        if not text or not text.strip():
            raise ProcessingError("Empty text for synthesis")
        
        logger.debug(
            f"Synthesizing speech | "
            f"Provider: {self.provider} | "
            f"Text length: {len(text)} chars"
        )
        
        if self.provider == "gtts":
            return self._gtts(text)
        
        if self.provider == "coqui":
            return self._coqui(text)
        
        if self.provider == "none":
            raise ConfigurationError(
                "TTS provider is not configured",
                details={"provider": "none"},
            )
        
        raise ConfigurationError(
            f"Unknown TTS provider: {self.provider}",
            details={"provider": self.provider},
        )
    
    def _gtts(self, text: str) -> Tuple[bytes, str]:
        """Synthesize using gTTS.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Tuple[bytes, str]: Audio bytes and media type
            
        Raises:
            ModelLoadError: If dependencies are missing
            ProcessingError: If synthesis fails
        """
        try:
            from gtts import gTTS
        except ImportError as exc:
            logger.error("gTTS not installed")
            raise ModelLoadError(
                "gTTS is not installed",
                details={"error": str(exc)},
            )
        
        try:
            audio_stream = io.BytesIO()
            tts = gTTS(text=text, lang="en")
            tts.write_to_fp(audio_stream)
            audio_bytes = audio_stream.getvalue()
            
            if not audio_bytes:
                raise ProcessingError("gTTS returned empty audio")
            
            logger.debug(f"gTTS synthesis complete | Size: {len(audio_bytes)} bytes")
            return audio_bytes, "audio/mpeg"
        
        except ProcessingError:
            raise
        except Exception as exc:
            logger.error(f"gTTS synthesis failed: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Speech synthesis failed",
                details={"error": str(exc)},
            )
    
    def _coqui(self, text: str) -> Tuple[bytes, str]:
        """Synthesize using Coqui TTS.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Tuple[bytes, str]: Audio bytes and media type
            
        Raises:
            ModelLoadError: If dependencies are missing or model load fails
            ProcessingError: If synthesis fails
        """
        try:
            from TTS.api import TTS
        except ImportError as exc:
            logger.error("Coqui TTS not installed")
            raise ModelLoadError(
                "Coqui TTS is not installed",
                details={"error": str(exc)},
            )
        
        try:
            # Load model
            try:
                logger.debug("Loading Coqui TTS model...")
                tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
                logger.debug("Coqui TTS model loaded")
            except Exception as exc:
                logger.error(f"Failed to load Coqui TTS model: {str(exc)}", exc_info=True)
                raise ModelLoadError(
                    "Failed to load TTS model",
                    details={"error": str(exc)},
                )
            
            # Synthesize
            try:
                wav = tts.tts(text)
                
                # Save to bytes
                audio_stream = io.BytesIO()
                # Note: Coqui TTS returns numpy array, need to convert
                import numpy as np
                from scipy.io import wavfile
                
                sample_rate = 22050  # Default sample rate for Coqui TTS
                wavfile.write(audio_stream, sample_rate, np.array(wav, dtype=np.float32))
                audio_bytes = audio_stream.getvalue()
                
                if not audio_bytes:
                    raise ProcessingError("Coqui TTS returned empty audio")
                
                logger.debug(f"Coqui TTS synthesis complete | Size: {len(audio_bytes)} bytes")
                return audio_bytes, "audio/wav"
            
            except Exception as exc:
                logger.error(f"Coqui TTS synthesis failed: {str(exc)}", exc_info=True)
                raise ProcessingError(
                    "Speech synthesis failed",
                    details={"error": str(exc)},
                )
        
        except (ModelLoadError, ProcessingError):
            raise
        except Exception as exc:
            logger.error(f"Unexpected Coqui TTS error: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "TTS processing failed",
                details={"error": str(exc)},
            )


tts_service = TtsService()
