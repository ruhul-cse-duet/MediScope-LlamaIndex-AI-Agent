"""Enhanced configuration with validation and error handling."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings with validation."""
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = "MediScope"
    app_version: str = "0.1.0"
    environment: str = "local"
    log_level: str = "INFO"
    
    # API settings
    api_prefix: str = "/api"
    allowed_origins_raw: str = Field(default="*", alias="allowed_origins", exclude=True)
    
    # Paths
    static_dir: Path = BASE_DIR / "frontend"
    data_dir: Path = BASE_DIR / "data"
    log_dir: Path = BASE_DIR / "logs"
    
    # Upload limits
    max_upload_mb: int = 20
    max_upload_bytes: int = Field(default=0, init=False)
    
    # Service providers
    rag_provider: str = "simple"  # simple, llamaindex
    llm_provider: str = "none"  # none, openai, vllm, lmstudio
    llm_model: str = "gpt-4o-mini"
    stt_provider: str = "none"  # none, faster_whisper, openai
    tts_provider: str = "none"  # none, gtts, coqui
    vision_provider: str = "none"  # none, internvl (direct from HuggingFace), vllm, lmstudio
    ocr_provider: str = "none"  # none, tesseract
    vision_model: str = "OpenGVLab/Mini-InternVL2-1B-DA-Medical"  # Model name (HuggingFace for internvl, or model name for vllm/lmstudio, e.g., "Qwen/Qwen3-VL-2B-Instruct")
    
    # API keys and URLs
    openai_api_key: str | None = None
    vllm_url: str | None = None
    lmstudio_url: str | None = None  # LM Studio local server URL
    lmstudio_url: str | None = None  # LM Studio local server URL
    
    # Feature flags
    demo_mode: bool = True
    enable_file_logging: bool = True
    
    # Timeouts (in seconds)
    llm_timeout: int = 60
    stt_timeout: int = 120
    tts_timeout: int = 60
    vision_timeout: int = 90
    http_timeout: int = 30
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    
    @property
    def allowed_origins(self) -> List[str]:
        """Get allowed origins as a list, splitting comma-separated string if needed."""
        if not self.allowed_origins_raw or not self.allowed_origins_raw.strip():
            return ["*"]
        return [item.strip() for item in self.allowed_origins_raw.split(",") if item.strip()]
    
    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        value = value.upper()
        if value not in valid_levels:
            raise ValueError(f"Invalid log level: {value}. Must be one of {valid_levels}")
        return value
    
    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        """Validate environment."""
        valid_envs = {"local", "development", "staging", "production"}
        value = value.lower()
        if value not in valid_envs:
            raise ValueError(f"Invalid environment: {value}. Must be one of {valid_envs}")
        return value
    
    @model_validator(mode="after")
    def _validate_providers(self) -> "Settings":
        """Validate provider configurations."""
        # Calculate max upload bytes
        self.max_upload_bytes = self.max_upload_mb * 1024 * 1024
        
        # Validate LLM provider configuration
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set when llm_provider is 'openai'")
        
        if self.llm_provider == "vllm" and not self.vllm_url:
            raise ValueError("VLLM_URL must be set when llm_provider is 'vllm'")
        
        if self.llm_provider == "lmstudio" and not self.lmstudio_url:
            raise ValueError("LMSTUDIO_URL must be set when llm_provider is 'lmstudio'")
        
        if self.llm_provider == "lmstudio" and not self.lmstudio_url:
            raise ValueError("LMSTUDIO_URL must be set when llm_provider is 'lmstudio'")
        
        # Validate STT provider configuration
        if self.stt_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set when stt_provider is 'openai'")
        
        # Validate Vision provider configuration
        if self.vision_provider == "vllm" and not self.vllm_url:
            raise ValueError("VLLM_URL must be set when vision_provider is 'vllm'")
        
        if self.vision_provider == "lmstudio" and not self.lmstudio_url:
            raise ValueError("LMSTUDIO_URL must be set when vision_provider is 'lmstudio'")
        
        # Note: internvl provider loads model directly from HuggingFace, no URL needed
        
        # Create necessary directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.enable_file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        return self
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def is_demo_mode(self) -> bool:
        """Check if demo mode is enabled."""
        return self.demo_mode


def get_settings() -> Settings:
    """Get settings with error handling."""
    try:
        return Settings()
    except Exception as exc:
        print(f"ERROR: Failed to load configuration: {exc}")
        print(f"Please check your .env file in the project root directory.")
        raise


settings = get_settings()
