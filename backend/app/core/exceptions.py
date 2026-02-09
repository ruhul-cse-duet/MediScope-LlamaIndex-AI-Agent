"""Custom exceptions for MediScope application."""

from __future__ import annotations


class MediScopeException(Exception):
    """Base exception for all MediScope errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(MediScopeException):
    """Raised when configuration is invalid or missing."""

    pass


class ServiceUnavailableError(MediScopeException):
    """Raised when an external service is unavailable."""

    pass


class ModelLoadError(MediScopeException):
    """Raised when a model fails to load."""

    pass


class ProcessingError(MediScopeException):
    """Raised when data processing fails."""

    pass


class ValidationError(MediScopeException):
    """Raised when input validation fails."""

    pass


class TimeoutError(MediScopeException):
    """Raised when an operation times out."""

    pass
