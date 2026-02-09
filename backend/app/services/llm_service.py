"""Enhanced LLM service with retry logic and comprehensive error handling."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import (
    ConfigurationError,
    ServiceUnavailableError,
    TimeoutError as CustomTimeoutError,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a medical education and triage support assistant. "
    "You do not diagnose or prescribe. You ask concise follow-up questions when needed, "
    "offer general education, and highlight red flags. "
    "Always remind users that your advice is for educational purposes only and not a "
    "substitute for professional medical care."
)


class LLMService:
    """LLM service with multiple provider support and error handling."""
    
    def __init__(self) -> None:
        self.provider = settings.llm_provider
        logger.info(f"LLM service initialized with provider: {self.provider}")
    
    def generate(self, user_message: str, context: str | None = None) -> dict[str, Any]:
        """Generate LLM response with retry logic.
        
        Args:
            user_message: The user's message
            context: Optional context from RAG
            
        Returns:
            dict: Response with 'message' and 'raw' keys
            
        Raises:
            ConfigurationError: If provider is misconfigured
            ServiceUnavailableError: If LLM service is unavailable
            CustomTimeoutError: If request times out
        """
        logger.debug(
            f"Generating LLM response | "
            f"Provider: {self.provider} | "
            f"Message length: {len(user_message)} | "
            f"Has context: {bool(context)}"
        )
        
        try:
            if self.provider == "openai":
                return self._call_with_retry(self._call_openai, user_message, context)
            
            if self.provider == "vllm":
                return self._call_with_retry(self._call_vllm, user_message, context)
            
            if self.provider == "lmstudio":
                return self._call_with_retry(self._call_lmstudio, user_message, context)
            
            if self.provider == "none":
                return self._demo_response(user_message, context)
            
            raise ConfigurationError(
                f"Unknown LLM provider: {self.provider}",
                details={"provider": self.provider},
            )
        
        except (ConfigurationError, ServiceUnavailableError, CustomTimeoutError):
            raise
        except Exception as exc:
            logger.error(f"LLM generation failed: {str(exc)}", exc_info=True)
            raise ServiceUnavailableError(
                "Failed to generate LLM response",
                details={"error": str(exc)},
            )
    
    def _call_with_retry(
        self,
        func,
        user_message: str,
        context: str | None,
    ) -> dict[str, Any]:
        """Execute function with exponential backoff retry.
        
        Args:
            func: Function to call
            user_message: User message
            context: Optional context
            
        Returns:
            dict: Function result
            
        Raises:
            ServiceUnavailableError: If all retries fail
            CustomTimeoutError: If request times out
        """
        last_exception = None
        
        for attempt in range(settings.max_retries):
            try:
                result = func(user_message, context)
                if attempt > 0:
                    logger.info(f"Request succeeded on attempt {attempt + 1}")
                return result
            
            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning(
                    f"Request timeout on attempt {attempt + 1}/{settings.max_retries}"
                )
                if attempt == settings.max_retries - 1:
                    raise CustomTimeoutError(
                        "LLM request timed out",
                        details={"attempts": attempt + 1},
                    )
            
            except httpx.HTTPStatusError as exc:
                last_exception = exc
                if exc.response.status_code >= 500:
                    # Retry on server errors
                    logger.warning(
                        f"Server error on attempt {attempt + 1}/{settings.max_retries}: "
                        f"{exc.response.status_code}"
                    )
                    if attempt < settings.max_retries - 1:
                        time.sleep(settings.retry_delay * (2 ** attempt))
                        continue
                else:
                    # Don't retry on client errors
                    raise ServiceUnavailableError(
                        f"LLM service error: {exc.response.status_code}",
                        details={
                            "status_code": exc.response.status_code,
                            "response": exc.response.text[:500],
                        },
                    )
            
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    f"Request failed on attempt {attempt + 1}/{settings.max_retries}: {str(exc)}"
                )
                if attempt < settings.max_retries - 1:
                    time.sleep(settings.retry_delay * (2 ** attempt))
                    continue
                break
        
        raise ServiceUnavailableError(
            "LLM service unavailable after retries",
            details={
                "attempts": settings.max_retries,
                "error": str(last_exception),
            },
        )
    
    def _call_openai(self, user_message: str, context: str | None) -> dict[str, Any]:
        """Call OpenAI API.
        
        Args:
            user_message: User message
            context: Optional context
            
        Returns:
            dict: Response data
            
        Raises:
            ConfigurationError: If API key is missing
            httpx.HTTPError: If request fails
        """
        if not settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured",
                details={"provider": "openai"},
            )
        
        payload = self._build_payload(user_message, context)
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        
        logger.debug("Calling OpenAI API")
        
        with httpx.Client(timeout=settings.llm_timeout) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        
        logger.debug("OpenAI API call successful")
        return self._parse_openai(data)
    
    def _call_vllm(self, user_message: str, context: str | None) -> dict[str, Any]:
        """Call vLLM API.
        
        Args:
            user_message: User message
            context: Optional context
            
        Returns:
            dict: Response data
            
        Raises:
            ConfigurationError: If vLLM URL is missing
            httpx.HTTPError: If request fails
        """
        if not settings.vllm_url:
            raise ConfigurationError(
                "VLLM_URL is not configured",
                details={"provider": "vllm"},
            )
        
        payload = self._build_payload(user_message, context)
        url = settings.vllm_url.rstrip("/") + "/v1/chat/completions"
        
        logger.debug(f"Calling vLLM at {url}")
        
        with httpx.Client(timeout=settings.llm_timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        
        logger.debug("vLLM API call successful")
        return self._parse_openai(data)
    
    def _call_lmstudio(self, user_message: str, context: str | None) -> dict[str, Any]:
        """Call LM Studio local API.
        
        LM Studio runs locally and provides an OpenAI-compatible API.
        This is perfect for running models like qwen3-medical-gguf locally.
        
        Args:
            user_message: User message
            context: Optional context
            
        Returns:
            dict: Response data
            
        Raises:
            ConfigurationError: If LM Studio URL is missing
            httpx.HTTPError: If request fails
        """
        if not settings.lmstudio_url:
            raise ConfigurationError(
                "LMSTUDIO_URL is not configured",
                details={"provider": "lmstudio"},
            )
        
        payload = self._build_payload(user_message, context)
        
        # LM Studio typically runs on localhost
        url = settings.lmstudio_url.rstrip("/") + "/v1/chat/completions"
        
        logger.debug(f"Calling LM Studio at {url}")
        logger.debug(f"Using model: {settings.llm_model}")
        
        try:
            with httpx.Client(timeout=settings.llm_timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            logger.debug("LM Studio API call successful")
            return self._parse_openai(data)
        
        except httpx.ConnectError as exc:
            logger.error(f"Cannot connect to LM Studio at {url}")
            raise ServiceUnavailableError(
                "LM Studio is not running or not accessible. "
                "Please ensure LM Studio is started and the model is loaded.",
                details={
                    "url": url,
                    "error": str(exc),
                    "help": "Start LM Studio and load the model, then try again."
                },
            )
        except Exception as exc:
            logger.error(f"LM Studio API error: {str(exc)}", exc_info=True)
            raise
    
    def _build_payload(self, user_message: str, context: str | None) -> dict[str, Any]:
        """Build request payload for OpenAI-compatible API.
        
        Args:
            user_message: User message
            context: Optional context
            
        Returns:
            dict: Request payload
        """
        prompt = user_message
        if context:
            prompt = (
                f"Context information from knowledge base:\n"
                f"{context}\n\n"
                f"---\n\n"
                f"Based on the context above and your medical knowledge, "
                f"please answer the following question:\n\n"
                f"{user_message}"
            )
        
        return {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1000,
        }
    
    def _parse_openai(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse OpenAI-compatible API response.
        
        Args:
            data: API response
            
        Returns:
            dict: Parsed response
        """
        choices = data.get("choices", [])
        if not choices:
            logger.warning("No choices in LLM response")
            return {
                "message": "I apologize, but I couldn't generate a response. Please try again.",
                "raw": data,
            }
        
        message = choices[0].get("message", {}).get("content", "")
        if not message or not message.strip():
            logger.warning("Empty message in LLM response")
            message = "I apologize, but I couldn't generate a proper response. Please try again."
        
        return {"message": message.strip(), "raw": data}
    
    def _demo_response(self, user_message: str, context: str | None) -> dict[str, Any]:
        """Generate demo response when no LLM is configured.
        
        Args:
            user_message: User message
            context: Optional context
            
        Returns:
            dict: Demo response
        """
        logger.debug("Generating demo response")
        
        summary = ""
        if context:
            summary = (
                "I found relevant information in the knowledge base and reviewed it. "
            )
        
        response = (
            f"{summary}Based on what you've shared, I can provide general medical education "
            "and triage guidance, but I cannot diagnose or prescribe treatment. "
            "\n\n"
            "To better assist you, could you please share:\n"
            "1. How long have the symptoms been present?\n"
            "2. Are you currently taking any medications?\n"
            "3. Have the symptoms been getting worse, staying the same, or improving?\n"
            "4. Are there any other symptoms you're experiencing?\n"
            "\n"
            "Remember: If you're experiencing severe symptoms or an emergency, "
            "please seek immediate medical care or call emergency services."
        )
        
        if settings.demo_mode:
            response = f"[DEMO MODE - No LLM configured]\n\n{response}"
        
        return {
            "message": response,
            "raw": {
                "provider": "demo",
                "demo_mode": settings.demo_mode,
            },
        }


llm_service = LLMService()
