"""Enhanced vision service with comprehensive error handling."""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import Tuple

import httpx

from app.core.config import settings
from app.core.exceptions import (
    ConfigurationError,
    ModelLoadError,
    ProcessingError,
    ServiceUnavailableError,
    TimeoutError as CustomTimeoutError,
)

logger = logging.getLogger(__name__)


class VisionService:
    """Vision service for OCR and VLM question answering."""
    
    def __init__(self) -> None:
        """Initialize vision service."""
        self.provider = settings.vision_provider
        self.ocr_provider = settings.ocr_provider
        self._pipeline = None
        
        logger.info(
            f"Vision service initialized | "
            f"Vision provider: {self.provider} | "
            f"OCR provider: {self.ocr_provider}"
        )
    
    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image using OCR.
        
        Args:
            image_bytes: Image data
            
        Returns:
            str: Extracted text
            
        Raises:
            ConfigurationError: If OCR provider is misconfigured
            ProcessingError: If OCR fails
        """
        if self.ocr_provider == "tesseract":
            return self._tesseract(image_bytes)
        
        if self.ocr_provider == "none":
            logger.debug("OCR provider is 'none', returning empty string")
            return ""
        
        raise ConfigurationError(
            f"Unknown OCR provider: {self.ocr_provider}",
            details={"provider": self.ocr_provider},
        )
    
    def answer_question(self, image_bytes: bytes, question: str) -> str:
        """Answer question about image using VLM.
        
        Args:
            image_bytes: Image data
            question: Question to answer
            
        Returns:
            str: Answer
            
        Raises:
            ConfigurationError: If vision provider is misconfigured
            ProcessingError: If VLM fails
        """
        if self.provider == "internvl":
            return self._internvl(image_bytes, question)
        
        if self.provider == "vllm":
            return self._vllm_vision(image_bytes, question)
        
        if self.provider == "lmstudio":
            return self._lmstudio_vision(image_bytes, question)
        
        if self.provider == "none":
            raise ConfigurationError(
                "Vision provider is not configured",
                details={"provider": "none"},
            )
        
        raise ConfigurationError(
            f"Unknown vision provider: {self.provider}",
            details={"provider": self.provider},
        )
    
    def _tesseract(self, image_bytes: bytes) -> str:
        """Extract text using Tesseract OCR.
        
        Args:
            image_bytes: Image data
            
        Returns:
            str: Extracted text
            
        Raises:
            ModelLoadError: If dependencies are missing
            ProcessingError: If OCR fails
        """
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            logger.error("Tesseract dependencies not installed")
            raise ModelLoadError(
                "pytesseract or Pillow is not installed",
                details={"error": str(exc)},
            )
        
        try:
            # Check if Tesseract is available before processing
            try:
                pytesseract.get_tesseract_version()
            except (pytesseract.TesseractNotFoundError, FileNotFoundError, Exception) as exc:
                logger.error("Tesseract OCR executable not found")
                raise ModelLoadError(
                    "Tesseract OCR is not installed or not in PATH. "
                    "Please install Tesseract OCR: "
                    "Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki "
                    "or use: choco install tesseract "
                    "Linux: sudo apt-get install tesseract-ocr "
                    "macOS: brew install tesseract",
                    details={"error": str(exc)},
                )
            
            image = Image.open(io.BytesIO(image_bytes))
            
            # Validate image
            if image.size[0] == 0 or image.size[1] == 0:
                raise ProcessingError("Invalid image dimensions")
            
            logger.debug(f"Running Tesseract OCR on {image.size[0]}x{image.size[1]} image")
            
            text = pytesseract.image_to_string(image).strip()
            
            logger.debug(f"Tesseract extracted {len(text)} characters")
            return text
        
        except ModelLoadError:
            raise
        except pytesseract.TesseractNotFoundError as exc:
            logger.error("Tesseract OCR executable not found")
            raise ModelLoadError(
                "Tesseract OCR is not installed or not in PATH. "
                "Please install Tesseract OCR: "
                "Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki "
                "or use: choco install tesseract "
                "Linux: sudo apt-get install tesseract-ocr "
                "macOS: brew install tesseract",
                details={"error": str(exc)},
            )
        except ProcessingError:
            raise
        except Exception as exc:
            logger.error(f"Tesseract OCR failed: {str(exc)}", exc_info=True)
            # Check if it's a TesseractNotFoundError wrapped in another exception
            error_str = str(exc).lower()
            if "tesseract" in error_str and ("not found" in error_str or "not installed" in error_str):
                raise ModelLoadError(
                    "Tesseract OCR is not installed or not in PATH. "
                    "Please install Tesseract OCR: "
                    "Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki "
                    "or use: choco install tesseract "
                    "Linux: sudo apt-get install tesseract-ocr "
                    "macOS: brew install tesseract",
                    details={"error": str(exc)},
                )
            raise ProcessingError(
                "OCR processing failed",
                details={"error": str(exc)},
            )
    
    def _lmstudio_vision(self, image_bytes: bytes, question: str) -> str:
        """Answer question using LM Studio vision model (e.g., Qwen3-VL-2B-Instruct).
        
        Args:
            image_bytes: Image data
            question: Question
            
        Returns:
            str: Answer
            
        Raises:
            ConfigurationError: If LM Studio URL is missing
            ProcessingError: If inference fails
        """
        if not settings.lmstudio_url:
            raise ConfigurationError(
                "LMSTUDIO_URL is not configured",
                details={"provider": "lmstudio"},
            )
        
        try:
            from PIL import Image
        except ImportError as exc:
            logger.error("Pillow not installed")
            raise ModelLoadError(
                "Pillow is not installed",
                details={"error": str(exc)},
            )
        
        try:
            # Validate image
            image = Image.open(io.BytesIO(image_bytes))
            if image.size[0] == 0 or image.size[1] == 0:
                raise ProcessingError("Invalid image dimensions")
            
            # Convert image to base64
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Determine image MIME type
            image_format = image.format or "PNG"
            mime_type = f"image/{image_format.lower()}"
            
            logger.debug(
                f"Calling LM Studio vision API | "
                f"Image: {image.size[0]}x{image.size[1]} | "
                f"Question: {question[:100]}..."
            )
            
            # Build LM Studio API request (OpenAI-compatible format)
            url = settings.lmstudio_url.rstrip("/") + "/v1/chat/completions"
            
            # LM Studio vision models (like Qwen3-VL) use OpenAI-compatible format
            payload = {
                "model": settings.vision_model,  # e.g., "Qwen/Qwen3-VL-2B-Instruct"
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": question
                            }
                        ]
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
            }
            
            # Make API call with retry logic
            last_exception = None
            for attempt in range(settings.max_retries):
                try:
                    with httpx.Client(timeout=settings.vision_timeout) as client:
                        response = client.post(url, json=payload)
                        response.raise_for_status()
                        data = response.json()
                    
                    # Parse response
                    choices = data.get("choices", [])
                    if not choices:
                        logger.warning("No choices in LM Studio vision response")
                        return ""
                    
                    message = choices[0].get("message", {}).get("content", "")
                    if not message or not message.strip():
                        logger.warning("Empty message in LM Studio vision response")
                        return ""
                    
                    logger.debug(f"LM Studio vision generated {len(message)} characters")
                    return message.strip()
                
                except httpx.TimeoutException as exc:
                    last_exception = exc
                    logger.warning(
                        f"LM Studio vision timeout on attempt {attempt + 1}/{settings.max_retries}"
                    )
                    if attempt == settings.max_retries - 1:
                        raise CustomTimeoutError(
                            "Vision model request timed out",
                            details={"attempts": attempt + 1},
                        )
                
                except httpx.HTTPStatusError as exc:
                    last_exception = exc
                    if exc.response.status_code >= 500:
                        logger.warning(
                            f"LM Studio vision server error on attempt {attempt + 1}/{settings.max_retries}: "
                            f"{exc.response.status_code}"
                        )
                        if attempt < settings.max_retries - 1:
                            time.sleep(settings.retry_delay * (2 ** attempt))
                            continue
                    else:
                        error_detail = exc.response.text[:500] if exc.response.text else "No error details"
                        raise ServiceUnavailableError(
                            f"LM Studio vision service error: {exc.response.status_code}",
                            details={
                                "status_code": exc.response.status_code,
                                "response": error_detail,
                                "help": "Ensure LM Studio is running with the vision model loaded (e.g., Qwen3-VL-2B-Instruct)"
                            },
                        )
                
                except httpx.ConnectError as exc:
                    last_exception = exc
                    logger.error(f"Cannot connect to LM Studio at {url}")
                    raise ServiceUnavailableError(
                        "LM Studio is not running or not accessible. "
                        "Please ensure LM Studio is started and the vision model is loaded.",
                        details={
                            "url": url,
                            "error": str(exc),
                            "help": "Start LM Studio, load the vision model (e.g., Qwen3-VL-2B-Instruct), then try again."
                        },
                    )
                
                except Exception as exc:
                    last_exception = exc
                    logger.warning(
                        f"LM Studio vision request failed on attempt {attempt + 1}/{settings.max_retries}: {str(exc)}"
                    )
                    if attempt < settings.max_retries - 1:
                        time.sleep(settings.retry_delay * (2 ** attempt))
                        continue
                    break
            
            raise ServiceUnavailableError(
                "LM Studio vision service unavailable after retries",
                details={
                    "attempts": settings.max_retries,
                    "error": str(last_exception),
                },
            )
        
        except (ConfigurationError, ServiceUnavailableError, CustomTimeoutError, ProcessingError):
            raise
        except Exception as exc:
            logger.error(f"LM Studio vision inference failed: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Vision model inference failed",
                details={"error": str(exc)},
            )
    
    def _vllm_vision(self, image_bytes: bytes, question: str) -> str:
        """Answer question using vLLM vision model.
        
        Args:
            image_bytes: Image data
            question: Question
            
        Returns:
            str: Answer
            
        Raises:
            ConfigurationError: If vLLM URL is missing
            ProcessingError: If inference fails
        """
        if not settings.vllm_url:
            raise ConfigurationError(
                "VLLM_URL is not configured",
                details={"provider": "vllm"},
            )
        
        try:
            from PIL import Image
        except ImportError as exc:
            logger.error("Pillow not installed")
            raise ModelLoadError(
                "Pillow is not installed",
                details={"error": str(exc)},
            )
        
        try:
            # Validate image
            image = Image.open(io.BytesIO(image_bytes))
            if image.size[0] == 0 or image.size[1] == 0:
                raise ProcessingError("Invalid image dimensions")
            
            # Convert image to base64
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Determine image MIME type
            image_format = image.format or "PNG"
            mime_type = f"image/{image_format.lower()}"
            
            logger.debug(
                f"Calling vLLM vision API | "
                f"Image: {image.size[0]}x{image.size[1]} | "
                f"Question: {question[:100]}..."
            )
            
            # Build vLLM API request
            url = settings.vllm_url.rstrip("/") + "/v1/chat/completions"
            
            # vLLM vision models use a specific format for vision inputs
            payload = {
                "model": settings.vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": question
                            }
                        ]
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
            }
            
            # Make API call with retry logic
            last_exception = None
            for attempt in range(settings.max_retries):
                try:
                    with httpx.Client(timeout=settings.vision_timeout) as client:
                        response = client.post(url, json=payload)
                        response.raise_for_status()
                        data = response.json()
                    
                    # Parse response
                    choices = data.get("choices", [])
                    if not choices:
                        logger.warning("No choices in vLLM vision response")
                        return ""
                    
                    message = choices[0].get("message", {}).get("content", "")
                    if not message or not message.strip():
                        logger.warning("Empty message in vLLM vision response")
                        return ""
                    
                    logger.debug(f"vLLM vision generated {len(message)} characters")
                    return message.strip()
                
                except httpx.TimeoutException as exc:
                    last_exception = exc
                    logger.warning(
                        f"vLLM vision timeout on attempt {attempt + 1}/{settings.max_retries}"
                    )
                    if attempt == settings.max_retries - 1:
                        raise CustomTimeoutError(
                            "Vision model request timed out",
                            details={"attempts": attempt + 1},
                        )
                
                except httpx.HTTPStatusError as exc:
                    last_exception = exc
                    if exc.response.status_code >= 500:
                        logger.warning(
                            f"vLLM vision server error on attempt {attempt + 1}/{settings.max_retries}: "
                            f"{exc.response.status_code}"
                        )
                        if attempt < settings.max_retries - 1:
                            time.sleep(settings.retry_delay * (2 ** attempt))
                            continue
                    else:
                        raise ServiceUnavailableError(
                            f"vLLM vision service error: {exc.response.status_code}",
                            details={
                                "status_code": exc.response.status_code,
                                "response": exc.response.text[:500],
                            },
                        )
                
                except Exception as exc:
                    last_exception = exc
                    logger.warning(
                        f"vLLM vision request failed on attempt {attempt + 1}/{settings.max_retries}: {str(exc)}"
                    )
                    if attempt < settings.max_retries - 1:
                        time.sleep(settings.retry_delay * (2 ** attempt))
                        continue
                    break
            
            raise ServiceUnavailableError(
                "vLLM vision service unavailable after retries",
                details={
                    "attempts": settings.max_retries,
                    "error": str(last_exception),
                },
            )
        
        except (ConfigurationError, ServiceUnavailableError, CustomTimeoutError, ProcessingError):
            raise
        except Exception as exc:
            logger.error(f"vLLM vision inference failed: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Vision model inference failed",
                details={"error": str(exc)},
            )
    
    def _internvl(self, image_bytes: bytes, question: str) -> str:
        """Answer question using InternVL model directly from HuggingFace.
        
        Args:
            image_bytes: Image data
            question: Question
            
        Returns:
            str: Answer
            
        Raises:
            ModelLoadError: If dependencies are missing or model load fails
            ProcessingError: If inference fails
        """
        # Load model on first use (lazy loading)
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                logger.error("Transformers library not installed")
                raise ModelLoadError(
                    "transformers is not installed. Install with: pip install transformers",
                    details={"error": str(exc)},
                )
            
            try:
                model_name = settings.vision_model
                logger.info(f"Loading vision model from HuggingFace: {model_name} (this may take a while)...")
                
                # Try loading with pipeline
                try:
                    self._pipeline = pipeline(
                        "image-text-to-text",
                        model=model_name,
                        trust_remote_code=True,
                        device_map="auto",
                    )
                    logger.info(f"Vision model '{model_name}' loaded successfully")
                
                except (KeyError, AttributeError) as config_exc:
                    # Configuration error - likely a bug in the model's config code
                    error_msg = str(config_exc)
                    logger.error(
                        f"Vision model configuration error: {error_msg}. "
                        "This is likely a compatibility issue with the model's configuration code."
                    )
                    
                    # Provide helpful error message with solutions
                    if "'architectures'" in error_msg or "architectures" in error_msg.lower():
                        raise ModelLoadError(
                            "Failed to load vision model due to configuration compatibility issue. "
                            "The model's configuration code has a bug. Solutions:\n"
                            "1. Clear HuggingFace cache: Delete the cached model files\n"
                            "2. Update transformers: pip install --upgrade transformers\n"
                            "3. Use a different vision provider (e.g., vllm) if available\n"
                            "4. Try setting VISION_PROVIDER=none to disable vision features temporarily",
                            details={
                                "model": settings.vision_model,
                                "error": error_msg,
                                "error_type": "Configuration compatibility issue",
                                "suggestions": [
                                    "Clear cache: Delete ~/.cache/huggingface/hub/models--OpenGVLab--Mini-InternVL2-1B-DA-Medical",
                                    "Update transformers: pip install --upgrade transformers",
                                    "Use vLLM provider instead if available",
                                    "Set VISION_PROVIDER=none to disable vision temporarily"
                                ],
                            },
                        )
                    else:
                        raise ModelLoadError(
                            f"Failed to load vision model due to configuration error: {error_msg}. "
                            "Try updating transformers or clearing the model cache.",
                            details={
                                "model": settings.vision_model,
                                "error": error_msg,
                            },
                        )
            
            except ModelLoadError:
                raise
            except Exception as exc:
                logger.error(f"Failed to load vision model: {str(exc)}", exc_info=True)
                raise ModelLoadError(
                    "Failed to load vision model from HuggingFace",
                    details={"model": settings.vision_model, "error": str(exc)},
                )
        
        try:
            from PIL import Image
        except ImportError as exc:
            logger.error("Pillow not installed")
            raise ModelLoadError(
                "Pillow is not installed",
                details={"error": str(exc)},
            )
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # Validate image
            if image.size[0] == 0 or image.size[1] == 0:
                raise ProcessingError("Invalid image dimensions")
            
            logger.debug(
                f"Running vision model inference | "
                f"Image: {image.size[0]}x{image.size[1]} | "
                f"Question: {question[:100]}..."
            )
            
            # Format for InternVL2 models
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": question},
                    ],
                }
            ]
            
            # Run inference
            outputs = self._pipeline(text=messages)
            
            # Parse response - handle different output formats
            answer = ""
            if isinstance(outputs, str):
                answer = outputs.strip()
            elif isinstance(outputs, list) and outputs:
                # Handle list of outputs
                first_output = outputs[0]
                if isinstance(first_output, str):
                    answer = first_output.strip()
                elif isinstance(first_output, dict):
                    answer = str(first_output.get("generated_text", first_output.get("text", ""))).strip()
            elif isinstance(outputs, dict):
                answer = str(outputs.get("generated_text", outputs.get("text", ""))).strip()
            
            if answer:
                logger.debug(f"Vision model generated {len(answer)} characters")
                return answer
            
            logger.warning("Vision model returned empty output")
            return ""
        
        except ProcessingError:
            raise
        except Exception as exc:
            logger.error(f"InternVL inference failed: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Vision model inference failed",
                details={"error": str(exc)},
            )


vision_service = VisionService()
