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


    def test_generic_mock_response(self):
        """Test that generic mock response is returned when no mock is set."""
        client = BedrockClient(mock_mode=True)

        # Don't set any mock response
        response = client.invoke(
            system_prompt="Test",
            user_message="Test"
        )

        # Should return generic mock
        parsed = json.loads(response)
        assert "task_summary" in parsed

    def test_mock_failure_default_message(self):
        """Test mock failure with default error message."""
        client = BedrockClient(mock_mode=True)
        client.set_mock_response(
            "test_agent",
            "",
            should_fail=True
            # No error_message - should use default
        )

        with pytest.raises(Exception) as exc_info:
            client.invoke(
                system_prompt="Test",
                user_message="Test",
                agent_name="test_agent"
            )

        assert "Mock failure" in str(exc_info.value)

    def test_invoke_with_tools(self):
        """Test invoke with tools parameter."""
        client = BedrockClient(mock_mode=True)
        client.set_default_mock_response('{"result": "ok"}')

        tools = [{"name": "test_tool", "description": "A test tool"}]

        response = client.invoke(
            system_prompt="Test",
            user_message="Test",
            tools=tools
        )

        log = client.get_invocation_log()
        assert log[0]["tools"] == tools

    def test_invoke_with_config(self):
        """Test invoke with custom model config."""
        client = BedrockClient(mock_mode=True)
        client.set_default_mock_response('{"result": "ok"}')

        config = ModelConfig(max_tokens=500, temperature=0.7)

        response = client.invoke(
            system_prompt="Test",
            user_message="Test",
            config=config
        )

        log = client.get_invocation_log()
        assert log[0]["config"]["max_tokens"] == 500
        assert log[0]["config"]["temperature"] == 0.7

    def test_region_default(self, monkeypatch):
        """Test that region defaults correctly."""
        monkeypatch.delenv("AWS_REGION", raising=False)
        client = BedrockClient(mock_mode=True)
        assert client.region == "us-east-1"

    def test_region_from_env(self, monkeypatch):
        """Test that region is read from environment."""
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        client = BedrockClient(mock_mode=True)
        assert client.region == "eu-west-1"

    def test_region_override(self):
        """Test that region can be overridden."""
        client = BedrockClient(region="ap-northeast-1", mock_mode=True)
        assert client.region == "ap-northeast-1"


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

    def test_create_client_default(self, monkeypatch):
        """Test creating client with default settings."""
        monkeypatch.setenv("MOCK_BEDROCK", "true")
        client = create_client()
        assert client.mock_mode is True
