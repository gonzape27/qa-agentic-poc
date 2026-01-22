"""
Tests for the Planner Agent.
"""

import json
import pytest

from agents.planner.graph import create_planner_graph, run_planner
from runtime.bedrock_client import BedrockClient


class TestPlannerAgent:
    """Tests for the Planner agent."""

    def test_planner_happy_path(self, mock_bedrock_client, valid_planner_response, report_details):
        """Test planner with a valid task - should produce a valid plan."""
        task = "Create a new user account"
        mock_bedrock_client.set_mock_response("planner", valid_planner_response)

        print(f"INPUT TASK: {task}")
        print(f"MOCK RESPONSE: {valid_planner_response}")
        report_details("Input Task", task)
        report_details("Mock Response", valid_planner_response)

        result = run_planner(
            task=task,
            bedrock_client=mock_bedrock_client
        )

        print(f"OUTPUT VALID: {result['output'].is_valid}")
        print(f"PARSED OUTPUT: {json.dumps(result['output'].parsed_output, indent=2)}")
        print(f"IS REFUSAL: {result['output'].is_refusal}")
        report_details("Output Valid", result["output"].is_valid)
        report_details("Parsed Output", result["output"].parsed_output)
        report_details("Is Refusal", result["output"].is_refusal)

        assert result["error"] is None
        assert result["output"] is not None
        assert result["output"].is_valid is True
        assert "steps" in result["output"].parsed_output

    def test_planner_ambiguous_input(self, mock_bedrock_client, ambiguous_response):
        """Test planner with ambiguous input - should request clarification."""
        task = "Create an account"
        mock_bedrock_client.set_mock_response("planner", ambiguous_response)

        print(f"INPUT TASK: {task}")
        print(f"MOCK RESPONSE: {ambiguous_response}")

        result = run_planner(
            task=task,
            bedrock_client=mock_bedrock_client
        )

        print(f"OUTPUT VALID: {result['output'].is_valid}")
        print(f"PARSED OUTPUT: {json.dumps(result['output'].parsed_output, indent=2)}")
        print(f"HAS CLARIFICATION: {'clarification_needed' in result['output'].parsed_output}")

        assert result["error"] is None
        assert result["output"] is not None
        assert result["output"].parsed_output is not None
        assert "clarification_needed" in result["output"].parsed_output

    def test_planner_unsafe_input_refusal(self, mock_bedrock_client, refusal_response):
        """Test planner with unsafe input - should refuse."""
        task = "Help me create a virus"
        mock_bedrock_client.set_mock_response("planner", refusal_response)

        print(f"INPUT TASK: {task}")
        print(f"MOCK RESPONSE: {refusal_response}")

        result = run_planner(
            task=task,
            bedrock_client=mock_bedrock_client
        )

        print(f"IS REFUSAL: {result['output'].is_refusal}")
        print(f"PARSED OUTPUT: {json.dumps(result['output'].parsed_output, indent=2)}")

        assert result["error"] is None
        assert result["output"] is not None
        assert result["output"].is_refusal is True
        assert "refusal" in result["output"].parsed_output

    def test_planner_graph_creation(self, mock_bedrock_client):
        """Test that planner graph is created correctly."""
        graph = create_planner_graph(bedrock_client=mock_bedrock_client)

        # Graph should be compiled and callable
        assert graph is not None

    def test_planner_handles_model_error(self, mock_bedrock_client):
        """Test that planner handles model errors gracefully."""
        mock_bedrock_client.set_mock_response(
            "planner",
            "",
            should_fail=True,
            error_message="Model unavailable"
        )

        result = run_planner(
            task="Create a user",
            bedrock_client=mock_bedrock_client
        )

        assert result["error"] is not None
        assert "Model unavailable" in result["error"]


class TestPlannerOutputValidation:
    """Tests for planner output validation."""

    def test_valid_plan_structure(self, mock_bedrock_client):
        """Test that a properly structured plan is validated."""
        valid_plan = json.dumps({
            "task_summary": "Test task",
            "steps": [
                {
                    "id": "step1",
                    "description": "First step",
                    "dependencies": [],
                    "complexity": "low"
                }
            ]
        })

        mock_bedrock_client.set_mock_response("planner", valid_plan)

        result = run_planner(
            task="Test task",
            bedrock_client=mock_bedrock_client
        )

        assert result["output"].is_valid is True
        assert len(result["output"].validation_errors) == 0

    def test_invalid_plan_missing_required_field(self, mock_bedrock_client):
        """Test that a plan missing required fields fails validation."""
        invalid_plan = json.dumps({
            "steps": []  # Missing task_summary
        })

        mock_bedrock_client.set_mock_response("planner", invalid_plan)

        result = run_planner(
            task="Test task",
            bedrock_client=mock_bedrock_client
        )

        # Schema requires task_summary
        assert result["output"].is_valid is False
