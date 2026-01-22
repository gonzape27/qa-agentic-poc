"""
Tests for the Executor Agent.
"""

import json
import pytest

from agents.executor.graph import create_executor_graph, run_executor
from runtime.bedrock_client import BedrockClient
from runtime.tool_registry import ToolRegistry, ToolMode, reset_registry


class TestExecutorAgent:
    """Tests for the Executor agent."""

    def test_executor_happy_path(
        self,
        mock_bedrock_client,
        valid_executor_response,
        tool_registry
    ):
        """Test executor with a valid plan - should execute successfully."""
        mock_bedrock_client.set_mock_response("executor", valid_executor_response)

        plan = {
            "task_summary": "Create user account",
            "steps": [
                {"id": "step1", "description": "Validate", "dependencies": [], "complexity": "low"}
            ]
        }

        print(f"INPUT PLAN: {json.dumps(plan, indent=2)}")
        print(f"MOCK RESPONSE: {valid_executor_response}")

        result = run_executor(
            plan=plan,
            bedrock_client=mock_bedrock_client,
            tool_registry=tool_registry
        )

        print(f"OUTPUT VALID: {result['output'].is_valid}")
        print(f"PARSED OUTPUT: {json.dumps(result['output'].parsed_output, indent=2)}")

        assert result["error"] is None
        assert result["output"] is not None
        assert result["output"].is_valid is True
        assert "results" in result["output"].parsed_output

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

        print(f"INPUT PLAN: {json.dumps(plan, indent=2)}")
        print(f"MOCK RESPONSE: {refusal}")

        result = run_executor(
            plan=plan,
            bedrock_client=mock_bedrock_client,
            tool_registry=tool_registry
        )

        print(f"IS REFUSAL: {result['output'].is_refusal}")
        print(f"PARSED OUTPUT: {json.dumps(result['output'].parsed_output, indent=2)}")

        assert result["output"].is_refusal is True

    def test_executor_graph_creation(self, mock_bedrock_client, tool_registry):
        """Test that executor graph is created correctly."""
        graph = create_executor_graph(
            bedrock_client=mock_bedrock_client,
            tool_registry=tool_registry
        )

        assert graph is not None

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
