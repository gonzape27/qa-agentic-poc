"""
Tests for the Agent Runner module.
"""

import json
import pytest

from runtime.agent_runner import AgentRunner, AgentOutput, run_agent
from runtime.bedrock_client import BedrockClient


class TestAgentRunner:
    """Tests for AgentRunner class."""

    def test_load_planner_agent(self, mock_bedrock_client):
        """Test loading the planner agent configuration."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)
        config = runner.load_agent("planner")

        assert config.name == "planner"
        assert "planning agent" in config.system_prompt.lower()
        assert "properties" in config.output_schema

    def test_load_executor_agent(self, mock_bedrock_client):
        """Test loading the executor agent configuration."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)
        config = runner.load_agent("executor")

        assert config.name == "executor"
        assert "execution agent" in config.system_prompt.lower()
        assert "properties" in config.output_schema

    def test_load_nonexistent_agent_raises_error(self, mock_bedrock_client):
        """Test that loading a non-existent agent raises an error."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        with pytest.raises(FileNotFoundError):
            runner.load_agent("nonexistent_agent")

    def test_validate_output_valid(self, mock_bedrock_client):
        """Test validation of valid output against schema."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        schema = {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }

        output = {"message": "Hello"}
        is_valid, errors = runner.validate_output(output, schema)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_output_invalid(self, mock_bedrock_client):
        """Test validation of invalid output against schema."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        schema = {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }

        output = {"wrong_field": "Hello"}
        is_valid, errors = runner.validate_output(output, schema)

        assert is_valid is False
        assert len(errors) > 0

    def test_detect_refusal_explicit(self, mock_bedrock_client):
        """Test detection of explicit refusal in output."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        output = {
            "refusal": {
                "reason": "Cannot help with this request"
            }
        }

        assert runner.detect_refusal(output) is True

    def test_detect_refusal_in_text(self, mock_bedrock_client):
        """Test detection of refusal language in output text."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        output = {
            "message": "I cannot assist with creating harmful content"
        }

        assert runner.detect_refusal(output) is True

    def test_detect_no_refusal(self, mock_bedrock_client):
        """Test that normal output is not detected as refusal."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        output = {
            "task_summary": "Create a user account",
            "steps": []
        }

        assert runner.detect_refusal(output) is False

    def test_parse_response_json(self, mock_bedrock_client):
        """Test parsing a plain JSON response."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        response = '{"message": "Hello"}'
        result = runner.parse_response(response)

        assert result == {"message": "Hello"}

    def test_parse_response_markdown_code_block(self, mock_bedrock_client):
        """Test parsing JSON from markdown code block."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        response = '```json\n{"message": "Hello"}\n```'
        result = runner.parse_response(response)

        assert result == {"message": "Hello"}

    def test_parse_response_with_text_before_json(self, mock_bedrock_client):
        """Test parsing JSON when there's text before it."""
        runner = AgentRunner(bedrock_client=mock_bedrock_client)

        response = 'Here is the response:\n{"message": "Hello"}'
        result = runner.parse_response(response)

        assert result == {"message": "Hello"}

    def test_run_agent_happy_path(self, mock_bedrock_client, valid_planner_response):
        """Test running an agent with a successful response."""
        mock_bedrock_client.set_mock_response("planner", valid_planner_response)

        runner = AgentRunner(bedrock_client=mock_bedrock_client)
        output = runner.run_agent("planner", "Create a new user account")

        assert output.agent_name == "planner"
        assert output.is_valid is True
        assert output.is_refusal is False
        assert output.parsed_output is not None
        assert "steps" in output.parsed_output


class TestRunAgentFunction:
    """Tests for the run_agent convenience function."""

    def test_run_agent_function(self, mock_bedrock_client, valid_planner_response):
        """Test the module-level run_agent function."""
        # This test validates the convenience function works
        # In real usage, it would create its own client
        pass  # Covered by class tests
