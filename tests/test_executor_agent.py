"""
Tests for the Executor Agent.
"""

import json
import os
import pytest

from agents.executor.graph import create_executor_graph, run_executor
from runtime.bedrock_client import BedrockClient
from runtime.tool_registry import ToolRegistry, ToolMode, reset_registry


def is_mock_mode():
    """Check if running in mock mode."""
    return os.getenv("MOCK_BEDROCK", "true").lower() == "true"


class TestExecutorAgent:
    """Tests for the Executor agent."""

    def test_executor_happy_path(
        self,
        mock_bedrock_client,
        valid_executor_response,
        tool_registry
    ):
        """Test executor with a valid plan - should execute or refuse appropriately."""
        mock_bedrock_client.set_mock_response("executor", valid_executor_response)

        # Use a plan that's feasible with available tools
        plan = {
            "task_summary": "Read a configuration file",
            "steps": [
                {"id": "step1", "description": "Read config.json file", "dependencies": [], "complexity": "low"}
            ]
        }

        result = run_executor(
            plan=plan,
            bedrock_client=mock_bedrock_client,
            tool_registry=tool_registry
        )

        assert result["error"] is None
        assert result["output"] is not None
        # Real LLM may return:
        # - Valid structured results (is_valid=True with results/refusal)
        # - Tool use attempts (is_valid=False but still a valid response)
        # Both indicate the executor is working correctly
        parsed = result["output"].parsed_output
        has_expected_response = (
            "results" in parsed or
            "refusal" in parsed or
            "tool_use" in parsed  # Real LLM may try to use tools
        )
        assert has_expected_response, f"Unexpected response format: {parsed}"

    def test_executor_refusal(self, mock_bedrock_client, tool_registry):
        """Test executor refuses to execute harmful plan."""
        refusal = json.dumps({
            "execution_id": "exec-refused",
            "refusal": {
                "reason": "Cannot execute harmful operations",
                "step_id": "step1"
            }
        })

        mock_bedrock_client.set_mock_response("executor", refusal)

        plan = {
            "task_summary": "Harmful task",
            "steps": [
                {"id": "step1", "description": "Do something bad", "dependencies": [], "complexity": "high"}
            ]
        }

        result = run_executor(
            plan=plan,
            bedrock_client=mock_bedrock_client,
            tool_registry=tool_registry
        )

        assert result["output"].is_refusal is True

    def test_executor_graph_creation(self, mock_bedrock_client, tool_registry):
        """Test that executor graph is created correctly."""
        graph = create_executor_graph(
            bedrock_client=mock_bedrock_client,
            tool_registry=tool_registry
        )

        assert graph is not None

    @pytest.mark.skipif(
        os.getenv("MOCK_BEDROCK", "true").lower() != "true",
        reason="Model error simulation only works in mock mode"
    )
    def test_executor_handles_model_error(self, mock_bedrock_client, tool_registry):
        """Test that executor handles model errors gracefully."""
        mock_bedrock_client.set_mock_response(
            "executor",
            "",
            should_fail=True,
            error_message="Model unavailable"
        )

        result = run_executor(
            plan={"task_summary": "Test", "steps": []},
            bedrock_client=mock_bedrock_client,
            tool_registry=tool_registry
        )

        assert result["error"] is not None


class TestExecutorToolUsage:
    """Tests for executor tool usage tracking."""

    def test_tool_calls_tracked(
        self,
        mock_bedrock_client,
        valid_executor_response,
        tool_registry
    ):
        """Test that tool calls are tracked during execution."""
        mock_bedrock_client.set_mock_response("executor", valid_executor_response)

        plan = {"task_summary": "Test", "steps": []}

        result = run_executor(
            plan=plan,
            bedrock_client=mock_bedrock_client,
            tool_registry=tool_registry
        )

        # Tool calls should be in the state
        assert "tool_calls" in result
