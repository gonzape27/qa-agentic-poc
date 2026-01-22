"""
Tests for the Bedrock Client module.
"""

import json
import pytest

from runtime.bedrock_client import BedrockClient, ModelConfig, create_client


class TestBedrockClient:
    """Tests for BedrockClient class."""

    def test_mock_mode_enabled_by_env(self, monkeypatch):
        """Test that mock mode is enabled by environment variable."""
        monkeypatch.setenv("MOCK_BEDROCK", "true")
        client = BedrockClient()
        assert client.mock_mode is True

    def test_mock_mode_disabled_by_default(self, monkeypatch):
        """Test that mock mode is disabled when env var is not set."""
        monkeypatch.delenv("MOCK_BEDROCK", raising=False)
        client = BedrockClient(mock_mode=False)
        assert client.mock_mode is False

    def test_mock_mode_override(self):
        """Test that mock mode can be overridden programmatically."""
        client = BedrockClient(mock_mode=True)
        assert client.mock_mode is True

        client2 = BedrockClient(mock_mode=False)
        assert client2.mock_mode is False

    def test_set_mock_response(self):
        """Test setting a mock response for an agent."""
        client = BedrockClient(mock_mode=True)
        client.set_mock_response("test_agent", '{"result": "success"}')

        response = client.invoke(
            system_prompt="Test",
            user_message="Test",
            agent_name="test_agent"
        )

        assert response == '{"result": "success"}'

    def test_set_default_mock_response(self):
        """Test setting a default mock response."""
        client = BedrockClient(mock_mode=True)
        client.set_default_mock_response('{"default": true}')

        response = client.invoke(
            system_prompt="Test",
            user_message="Test"
        )

        assert response == '{"default": true}'

    def test_mock_response_failure(self):
        """Test that mock responses can simulate failures."""
        client = BedrockClient(mock_mode=True)
        client.set_mock_response(
            "failing_agent",
            "",
            should_fail=True,
            error_message="Simulated failure"
        )

        with pytest.raises(Exception) as exc_info:
            client.invoke(
                system_prompt="Test",
                user_message="Test",
                agent_name="failing_agent"
            )

        assert "Simulated failure" in str(exc_info.value)

    def test_invocation_log(self):
        """Test that invocations are logged."""
        client = BedrockClient(mock_mode=True)
        client.set_default_mock_response('{"result": "ok"}')

        client.invoke(
            system_prompt="System prompt",
            user_message="User message"
        )

        log = client.get_invocation_log()
        assert len(log) == 1
        assert log[0]["system_prompt"] == "System prompt"
        assert log[0]["user_message"] == "User message"

    def test_clear_invocation_log(self):
        """Test clearing the invocation log."""
        client = BedrockClient(mock_mode=True)
        client.set_default_mock_response('{"result": "ok"}')

        client.invoke(system_prompt="Test", user_message="Test")
        assert len(client.get_invocation_log()) == 1

        client.clear_invocation_log()
        assert len(client.get_invocation_log()) == 0


class TestModelConfig:
    """Tests for ModelConfig class."""

    def test_default_values(self):
        """Test that ModelConfig has sensible defaults."""
        config = ModelConfig()

        assert config.max_tokens == 4096
        assert config.temperature == 0.0
        assert config.top_p == 1.0

    def test_custom_values(self):
        """Test that ModelConfig accepts custom values."""
        config = ModelConfig(
            model_id="custom-model",
            max_tokens=1000,
            temperature=0.5
        )

        assert config.model_id == "custom-model"
        assert config.max_tokens == 1000
        assert config.temperature == 0.5


class TestCreateClient:
    """Tests for the create_client factory function."""

    def test_create_client_mock(self):
        """Test creating a client in mock mode."""
        client = create_client(mock_mode=True)
        assert client.mock_mode is True

    def test_create_client_real(self):
        """Test creating a client in real mode."""
        client = create_client(mock_mode=False)
        assert client.mock_mode is False
