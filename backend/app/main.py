"""Main FastAPI application with enhanced error handling and middleware."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.core.exceptions import (
    ConfigurationError,
    MediScopeException,
    ModelLoadError,
    ProcessingError,
    ServiceUnavailableError,
    TimeoutError,
    ValidationError,
)
from app.core.logging import setup_logging

# Setup logging
log_dir = settings.log_dir if settings.enable_file_logging else None
setup_logging(settings.log_level, log_dir)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Medical Voice + Vision AI Agent for education and triage support",
    docs_url="/docs" if not settings.is_production() else None,
    redoc_url="/redoc" if not settings.is_production() else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()
    request_id = id(request)
    
    logger.info(
        f"Request started: {request.method} {request.url.path} | ID: {request_id}"
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            f"Request completed: {request.method} {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Duration: {process_time:.3f}s | "
            f"ID: {request_id}"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = str(request_id)
        return response
    
    except Exception as exc:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} | "
            f"Error: {str(exc)} | "
            f"Duration: {process_time:.3f}s | "
            f"ID: {request_id}",
            exc_info=True,
        )
        raise


# Custom exception handlers
@app.exception_handler(MediScopeException)
async def mediscope_exception_handler(request: Request, exc: MediScopeException):
    """Handle custom MediScope exceptions."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    if isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, ConfigurationError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif isinstance(exc, ServiceUnavailableError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, TimeoutError):
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
    elif isinstance(exc, ModelLoadError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif isinstance(exc, ProcessingError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    logger.error(
        f"MediScope exception: {exc.message} | "
        f"Type: {type(exc).__name__} | "
        f"Details: {exc.details}",
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "details": exc.details if not settings.is_production() else {},
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": exc.errors() if not settings.is_production() else [],
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": str(exc) if not settings.is_production() else {},
        },
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run startup tasks."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"RAG Provider: {settings.rag_provider}")
    logger.info(f"Demo Mode: {settings.demo_mode}")
    
    # Verify required directories exist
    if not settings.static_dir.exists():
        logger.warning(f"Static directory not found: {settings.static_dir}")
    
    logger.info("Application startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run shutdown tasks."""
    logger.info("Shutting down application")


# Include API routes
app.include_router(router, prefix=settings.api_prefix)

# Serve static files
if settings.static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
    logger.info(f"Serving static files from: {settings.static_dir}")


# Root endpoint
@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    """Serve the main application page."""
    index_path = Path(settings.static_dir) / "index.html"
    
    if not index_path.exists():
        logger.error(f"Index file not found: {index_path}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "NotFound", "message": "Application frontend not found"},
        )
    
    return FileResponse(index_path)
