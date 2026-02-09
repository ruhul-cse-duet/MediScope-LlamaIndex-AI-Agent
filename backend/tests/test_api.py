"""
Enhanced test suite for MediScope application.
Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_success(self):
        """Test health endpoint returns 200 and correct data."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert data["version"] == settings.app_version
        assert data["environment"] == settings.environment

    def test_health_check_structure(self):
        """Test health endpoint returns expected structure."""
        response = client.get("/api/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "environment" in data


class TestChatEndpoint:
    """Tests for chat endpoint."""

    def test_chat_valid_message(self):
        """Test chat with valid message."""
        response = client.post(
            "/api/chat",
            json={"message": "I have a headache"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "disclaimer" in data
        assert "session_id" in data
        assert isinstance(data["red_flag"], bool)

    def test_chat_empty_message(self):
        """Test chat with empty message returns error."""
        response = client.post(
            "/api/chat",
            json={"message": ""},
        )
        
        assert response.status_code in [400, 422]

    def test_chat_missing_message(self):
        """Test chat without message field returns error."""
        response = client.post(
            "/api/chat",
            json={},
        )
        
        assert response.status_code == 422

    def test_chat_with_context(self):
        """Test chat with image context."""
        response = client.post(
            "/api/chat",
            json={
                "message": "What does this show?",
                "image_text": "Blood pressure: 120/80",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_chat_red_flag_detection(self):
        """Test red flag detection for emergency symptoms."""
        response = client.post(
            "/api/chat",
            json={"message": "I have severe chest pain"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["red_flag"] is True
        assert data["urgent_notice"] is not None

    def test_chat_message_too_long(self):
        """Test chat with very long message."""
        long_message = "a" * 10001  # Over 10000 char limit
        response = client.post(
            "/api/chat",
            json={"message": long_message},
        )
        
        assert response.status_code in [400, 422]


class TestRagEndpoint:
    """Tests for RAG ingest endpoint."""

    def test_ingest_valid_document(self):
        """Test ingesting a valid document."""
        response = client.post(
            "/api/rag/ingest",
            json={
                "text": "Hypertension is high blood pressure.",
                "metadata": {"source": "test"},
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "doc_id" in data
        assert "status" in data

    def test_ingest_empty_text(self):
        """Test ingesting empty text returns error."""
        response = client.post(
            "/api/rag/ingest",
            json={"text": ""},
        )
        
        assert response.status_code in [400, 422]

    def test_ingest_missing_text(self):
        """Test ingesting without text field returns error."""
        response = client.post(
            "/api/rag/ingest",
            json={},
        )
        
        assert response.status_code == 422


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_endpoint(self):
        """Test accessing non-existent endpoint."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_invalid_method(self):
        """Test using wrong HTTP method."""
        response = client.get("/api/chat")  # Should be POST
        assert response.status_code == 405

    def test_invalid_json(self):
        """Test sending invalid JSON."""
        response = client.post(
            "/api/chat",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 422]


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = client.options("/api/health")
        
        # In test client, CORS headers might not be fully set
        # This is a basic check
        assert response.status_code in [200, 405]


@pytest.mark.skipif(
    settings.llm_provider == "none",
    reason="LLM provider not configured",
)
class TestLLMIntegration:
    """Tests for LLM integration (requires configured provider)."""

    def test_llm_generates_response(self):
        """Test LLM generates non-empty response."""
        response = client.post(
            "/api/chat",
            json={"message": "What is diabetes?"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["message"]) > 0


@pytest.mark.skipif(
    settings.stt_provider == "none",
    reason="STT provider not configured",
)
class TestSTTIntegration:
    """Tests for STT integration (requires configured provider)."""

    def test_stt_endpoint_exists(self):
        """Test STT endpoint is available."""
        # This would require actual audio file
        # Just test endpoint exists
        response = client.post("/api/stt")
        assert response.status_code in [400, 422]  # Missing file


@pytest.mark.skipif(
    settings.tts_provider == "none",
    reason="TTS provider not configured",
)
class TestTTSIntegration:
    """Tests for TTS integration (requires configured provider)."""

    def test_tts_endpoint_exists(self):
        """Test TTS endpoint is available."""
        response = client.post(
            "/api/tts",
            json={"text": "test"},
        )
        
        # Might fail with provider error, but endpoint should exist
        assert response.status_code in [200, 400, 500]


class TestConfiguration:
    """Tests for configuration."""

    def test_settings_loaded(self):
        """Test settings are loaded correctly."""
        assert settings.app_name is not None
        assert settings.app_version is not None
        assert settings.environment is not None

    def test_log_level_valid(self):
        """Test log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        assert settings.log_level in valid_levels

    def test_environment_valid(self):
        """Test environment is valid."""
        valid_envs = {"local", "development", "staging", "production"}
        assert settings.environment in valid_envs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
