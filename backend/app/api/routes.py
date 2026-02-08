"""API routes with comprehensive error handling and validation."""

from __future__ import annotations

import logging
from uuid import uuid4

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.core.config import settings
from app.core.exceptions import (
    ModelLoadError,
    ProcessingError,
    ServiceUnavailableError,
    ValidationError,
)
from app.schemas.chat import ChatRequest, ChatResponse, IngestRequest
from app.schemas.health import HealthResponse
from app.schemas.media import SttResponse, TtsRequest, VisionResponse
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.safety import assess
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service
from app.services.vision_service import vision_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _enforce_size(payload: bytes, context: str = "upload") -> None:
    """Enforce upload size limits.
    
    Args:
        payload: The bytes to check
        context: Context for error message
        
    Raises:
        HTTPException: If payload exceeds size limit
    """
    if len(payload) > settings.max_upload_bytes:
        size_mb = len(payload) / (1024 * 1024)
        logger.warning(
            f"Upload size exceeded: {size_mb:.2f}MB > {settings.max_upload_mb}MB ({context})"
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Upload exceeds {settings.max_upload_mb}MB limit. Received {size_mb:.2f}MB.",
        )


def _validate_content_type(content_type: str | None, allowed_types: list[str], context: str) -> None:
    """Validate content type.
    
    Args:
        content_type: The content type to validate
        allowed_types: List of allowed content type prefixes
        context: Context for error message
        
    Raises:
        HTTPException: If content type is not allowed
    """
    if not content_type:
        return
    
    if not any(content_type.startswith(allowed) for allowed in allowed_types):
        logger.warning(f"Invalid content type: {content_type} ({context})")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type: {content_type}. Allowed types: {', '.join(allowed_types)}",
        )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint with detailed status.
    
    Returns:
        HealthResponse: Current health status
    """
    try:
        health_status = HealthResponse(
            status="ok",
            version=settings.app_version,
            environment=settings.environment,
        )
        logger.debug(f"Health check successful: {health_status}")
        return health_status
    
    except Exception as exc:
        logger.error(f"Health check failed: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed",
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process chat message with RAG context and safety checks.
    
    Args:
        request: Chat request with message and optional image data
        
    Returns:
        ChatResponse: Response with message, safety notices, and citations
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        # Validate input
        if not request.message or not request.message.strip():
            raise ValidationError("Message cannot be empty")
        
        if len(request.message) > 10000:
            raise ValidationError("Message is too long (max 10000 characters)")
        
        session_id = request.session_id or uuid4().hex
        logger.info(f"Processing chat request | Session: {session_id}")
        
        # Safety assessment
        safety = assess(request.message)
        if safety.is_red_flag:
            logger.warning(
                f"Red flag detected in message | Session: {session_id} | "
                f"Message preview: {request.message[:100]}..."
            )
        
        # Query RAG
        try:
            context_docs = rag_service.query(request.message)
            context_snippets = [doc.text for doc in context_docs if doc.text]
            logger.debug(f"Retrieved {len(context_snippets)} context snippets")
        except Exception as exc:
            logger.error(f"RAG query failed: {str(exc)}", exc_info=True)
            context_docs = []
            context_snippets = []
        
        # Add image context
        if request.image_text:
            context_snippets.append(f"Image OCR: {request.image_text}")
            logger.debug("Added OCR text to context")
        
        if request.image_answer:
            context_snippets.append(f"Image answer: {request.image_answer}")
            logger.debug("Added image answer to context")
        
        # Generate LLM response
        context = "\n\n".join(context_snippets) if context_snippets else None
        try:
            llm_output = llm_service.generate(request.message, context=context)
            response_message = llm_output.get("message", "")
            
            if not response_message:
                logger.warning("LLM returned empty response")
                response_message = "I apologize, but I couldn't generate a proper response. Please try again."
            
        except Exception as exc:
            logger.error(f"LLM generation failed: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to generate response",
                details={"error": str(exc)},
            )
        
        # Build response
        response = ChatResponse(
            session_id=session_id,
            message=response_message,
            disclaimer=safety.disclaimer,
            urgent_notice=safety.urgent_notice,
            red_flag=safety.is_red_flag,
            citations=[doc.metadata for doc in context_docs],
            rag_context=context,
        )
        
        logger.info(
            f"Chat request completed | Session: {session_id} | "
            f"Red flag: {safety.is_red_flag} | "
            f"Citations: {len(context_docs)}"
        )
        
        return response
    
    except ValidationError:
        raise
    except ProcessingError:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in chat endpoint: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your message",
        )


@router.post("/rag/ingest")
async def ingest(request: IngestRequest) -> dict:
    """Ingest document into RAG store.
    
    Args:
        request: Document text and metadata
        
    Returns:
        dict: Document ID
        
    Raises:
        HTTPException: If ingestion fails
    """
    try:
        # Validate input
        if not request.text or not request.text.strip():
            raise ValidationError("Document text cannot be empty")
        
        if len(request.text) > 100000:
            raise ValidationError("Document is too large (max 100000 characters)")
        
        logger.info(f"Ingesting document | Length: {len(request.text)} chars")
        
        doc = rag_service.ingest(text=request.text, metadata=request.metadata)
        
        logger.info(f"Document ingested successfully | ID: {doc.doc_id}")
        return {"doc_id": doc.doc_id, "status": "success"}
    
    except ValidationError:
        raise
    except Exception as exc:
        logger.error(f"Document ingestion failed: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest document",
        )


@router.post("/stt", response_model=SttResponse)
async def stt(file: UploadFile = File(...)) -> SttResponse:
    """Convert speech to text.
    
    Args:
        file: Audio file upload
        
    Returns:
        SttResponse: Transcribed text
        
    Raises:
        HTTPException: If transcription fails
    """
    try:
        # Validate file
        if not file.filename:
            raise ValidationError("No file provided")
        
        _validate_content_type(
            file.content_type,
            ["audio/"],
            f"STT upload: {file.filename}",
        )
        
        # Read file
        audio_bytes = await file.read()
        _enforce_size(audio_bytes, f"STT file: {file.filename}")
        
        logger.info(
            f"Processing STT request | "
            f"File: {file.filename} | "
            f"Size: {len(audio_bytes) / 1024:.2f}KB | "
            f"Type: {file.content_type}"
        )
        
        # Transcribe
        try:
            transcript = stt_service.transcribe(audio_bytes, file.content_type)
            
            if not transcript:
                logger.warning("STT returned empty transcript")
                transcript = ""
            
        except Exception as exc:
            logger.error(f"STT transcription failed: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to transcribe audio",
                details={"error": str(exc)},
            )
        
        logger.info(f"STT completed | Transcript length: {len(transcript)} chars")
        return SttResponse(text=transcript)
    
    except ValidationError:
        raise
    except ProcessingError:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in STT endpoint: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process audio file",
        )


@router.post("/tts")
async def tts(request: TtsRequest) -> Response:
    """Convert text to speech.
    
    Args:
        request: Text to synthesize
        
    Returns:
        Response: Audio file
        
    Raises:
        HTTPException: If synthesis fails
    """
    try:
        # Validate input
        if not request.text or not request.text.strip():
            raise ValidationError("Text cannot be empty")
        
        if len(request.text) > 5000:
            raise ValidationError("Text is too long (max 5000 characters)")
        
        logger.info(f"Processing TTS request | Length: {len(request.text)} chars")
        
        # Synthesize
        try:
            audio_bytes, media_type = tts_service.synthesize(request.text)
            
            if not audio_bytes:
                raise ProcessingError("TTS returned empty audio")
            
        except ModelLoadError as exc:
            logger.error(f"TTS model/dependency not available: {str(exc)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"TTS service is not available: {exc.message}. Please install required dependencies.",
            )
        except ProcessingError as exc:
            logger.error(f"TTS synthesis failed: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to synthesize speech",
                details={"error": str(exc)},
            )
        except Exception as exc:
            logger.error(f"Unexpected TTS error: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to synthesize speech",
                details={"error": str(exc)},
            )
        
        logger.info(
            f"TTS completed | "
            f"Size: {len(audio_bytes) / 1024:.2f}KB | "
            f"Type: {media_type}"
        )
        
        return Response(content=audio_bytes, media_type=media_type)
    
    except ValidationError:
        raise
    except ProcessingError:
        raise
    except ModelLoadError as exc:
        logger.error(f"TTS model/dependency not available: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"TTS service is not available: {exc.message}. Please install required dependencies.",
        )
    except Exception as exc:
        logger.error(f"Unexpected error in TTS endpoint: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate speech",
        )


@router.post("/vision", response_model=VisionResponse)
async def vision(
    file: UploadFile | None = File(None),
    image_url: str | None = Form(None),
    question: str | None = Form(None),
) -> VisionResponse:
    """Extract text and answer questions about images.
    
    Args:
        file: Image file upload (optional)
        image_url: Image URL (optional)
        question: Question about the image (optional)
        
    Returns:
        VisionResponse: OCR text and optional answer
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        # Validate input
        if not file and not image_url:
            raise ValidationError("Provide either an image file or image_url")
        
        if file and image_url:
            logger.warning("Both file and URL provided, using file")
        
        # Get image bytes
        image_bytes = b""
        source = ""
        
        if file:
            _validate_content_type(
                file.content_type,
                ["image/"],
                f"Vision upload: {file.filename}",
            )
            image_bytes = await file.read()
            source = f"file: {file.filename}"
        
        elif image_url:
            # Validate URL format
            if not image_url.startswith(("http://", "https://")):
                raise ValidationError("Invalid image URL format")
            
            try:
                async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
                    response = await client.get(image_url)
                    response.raise_for_status()
                    image_bytes = response.content
                    source = f"URL: {image_url}"
            
            except httpx.TimeoutException:
                raise ServiceUnavailableError("Image download timed out")
            except httpx.HTTPError as exc:
                raise ServiceUnavailableError(
                    f"Failed to download image: {str(exc)}"
                )
        
        _enforce_size(image_bytes, f"Vision {source}")
        
        logger.info(
            f"Processing vision request | "
            f"Source: {source} | "
            f"Size: {len(image_bytes) / 1024:.2f}KB | "
            f"Has question: {bool(question)}"
        )
        
        # Extract text
        try:
            ocr_text = vision_service.extract_text(image_bytes)
            logger.debug(f"OCR extracted {len(ocr_text)} characters")
        except ModelLoadError as exc:
            logger.warning(f"OCR not available: {exc.message}")
            ocr_text = ""
        except Exception as exc:
            logger.error(f"OCR failed: {str(exc)}", exc_info=True)
            ocr_text = ""
        
        # Answer question - if no question provided, use default description prompt
        answer = None
        question_text = question.strip() if question else None
        
        # If no question provided, use default description prompt
        if not question_text:
            question_text = "Please describe this medical image in detail. What do you see? What are the key features, findings, or observations?"
            logger.debug("No question provided, using default description prompt")
        
        if question_text:
            if len(question_text) > 1000:
                raise ValidationError("Question is too long (max 1000 characters)")
            
            try:
                answer = vision_service.answer_question(image_bytes, question_text)
                logger.debug(f"Generated answer: {len(answer or '')} characters")
            except ModelLoadError as exc:
                logger.warning(f"Vision model not available: {exc.message}")
                answer = None  # Model not loaded, can't answer questions
            except Exception as exc:
                logger.error(f"Vision QA failed: {str(exc)}", exc_info=True)
                answer = None
        
        logger.info(
            f"Vision completed | "
            f"OCR length: {len(ocr_text)} | "
            f"Answer length: {len(answer or '')}"
        )
        
        return VisionResponse(ocr_text=ocr_text, answer=answer)
    
    except ValidationError:
        raise
    except ServiceUnavailableError:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in vision endpoint: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process image",
        )
