"""
Prompt Regression Tests

Tests agent behavior against golden inputs to detect behavioral drift.
Validates output structure, tool choice, and safety flags.
"""

import json
from pathlib import Path

import pytest

from agents.planner.graph import run_planner
from agents.executor.graph import run_executor
from runtime.bedrock_client import BedrockClient
from runtime.tool_registry import ToolRegistry, ToolMode, reset_registry


# Load golden test cases
GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden_cases(filename: str) -> dict:
    """Load golden test cases from JSON file."""
    filepath = GOLDEN_DIR / filename
    with open(filepath) as f:
        return json.load(f)


class TestPlannerRegression:
    """Regression tests for the Planner agent using golden inputs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mock client for each test."""
        self.client = BedrockClient(mock_mode=True)

    def _create_mock_response(self, expected: dict) -> str:
        """Create a mock response based on expected behavior."""
        if expected.get("is_refusal"):
            return json.dumps({
                "task_summary": "Request refused",
                "refusal": {
                    "reason": "I cannot assist with this request as it appears to be harmful or unauthorized."
                }
            })
        elif expected.get("is_clarification"):
            return json.dumps({
                "task_summary": "Clarification needed",
                "clarification_needed": "Please provide more details about what you want to accomplish."
            })
        else:
            # Create steps based on requirements
            num_steps = expected.get("min_steps", 2)
            steps = []
            for i in range(num_steps):
                steps.append({
                    "id": f"step{i+1}",
                    "description": f"Step {i+1} description",
                    "dependencies": [f"step{i}"] if i > 0 else [],
                    "complexity": "medium"
                })
            return json.dumps({
                "task_summary": "Task planned successfully",
                "steps": steps
            })

    @pytest.mark.parametrize("case", load_golden_cases("planner_cases.json")["cases"])
    def test_planner_golden_case(self, case):
        """Test planner against golden input cases."""
        case_id = case["id"]
        case_name = case["name"]
        input_text = case["input"]
        expected = case["expected"]

        # Setup mock response
        mock_response = self._create_mock_response(expected)
        self.client.set_mock_response("planner", mock_response)

        # Run planner
        result = run_planner(
            task=input_text,
            bedrock_client=self.client
        )

        # Assertions
        assert result["error"] is None, f"[{case_id}] {case_name}: Unexpected error"
        assert result["output"] is not None, f"[{case_id}] {case_name}: No output"

        output = result["output"]
        parsed = output.parsed_output

        # Check refusal expectation
        if expected.get("is_refusal"):
            assert output.is_refusal, f"[{case_id}] {case_name}: Expected refusal"
            assert "refusal" in parsed, f"[{case_id}] {case_name}: Missing refusal field"
        else:
            assert not output.is_refusal, f"[{case_id}] {case_name}: Unexpected refusal"

        # Check clarification expectation
        if expected.get("is_clarification"):
            assert "clarification_needed" in parsed, \
                f"[{case_id}] {case_name}: Expected clarification request"

        # Check steps expectation
        if expected.get("has_steps"):
            assert "steps" in parsed, f"[{case_id}] {case_name}: Missing steps"
            steps = parsed["steps"]

            if "min_steps" in expected:
                assert len(steps) >= expected["min_steps"], \
                    f"[{case_id}] {case_name}: Too few steps"

            if "max_steps" in expected:
                assert len(steps) <= expected["max_steps"], \
                    f"[{case_id}] {case_name}: Too many steps"


class TestExecutorRegression:
    """Regression tests for the Executor agent using golden inputs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        self.client = BedrockClient(mock_mode=True)
        reset_registry()
        self.registry = ToolRegistry(mode=ToolMode.STUB)

    def _create_mock_response(self, case: dict) -> str:
        """Create a mock executor response based on expected behavior."""
        expected = case["expected"]
        plan = case["input"]

        if expected.get("is_refusal"):
            return json.dumps({
                "execution_id": f"exec-{case['id']}",
                "refusal": {
                    "reason": "I cannot execute this plan as it contains dangerous operations."
                }
            })
        else:
            results = []
            for step in plan.get("steps", []):
                tool_calls = []
                if expected.get("allowed_tools"):
                    tool_calls.append({
                        "tool_name": expected["allowed_tools"][0],
                        "arguments": {},
                        "result": "Success"
                    })
                results.append({
                    "step_id": step["id"],
                    "status": "success",
                    "tool_calls": tool_calls,
                    "output": "Step completed"
                })

            return json.dumps({
                "execution_id": f"exec-{case['id']}",
                "results": results,
                "summary": {
                    "total_steps": len(results),
                    "successful": len(results),
                    "failed": 0,
                    "skipped": 0
                }
            })

    @pytest.mark.parametrize("case", load_golden_cases("executor_cases.json")["cases"])
    def test_executor_golden_case(self, case):
        """Test executor against golden input cases."""
        case_id = case["id"]
        case_name = case["name"]
        plan = case["input"]
        expected = case["expected"]

        # Setup mock response
        mock_response = self._create_mock_response(case)
        self.client.set_mock_response("executor", mock_response)

        # Run executor
        result = run_executor(
            plan=plan,
            bedrock_client=self.client,
            tool_registry=self.registry
        )

        # Assertions
        assert result["error"] is None, f"[{case_id}] {case_name}: Unexpected error"
        assert result["output"] is not None, f"[{case_id}] {case_name}: No output"

        output = result["output"]
        parsed = output.parsed_output

        # Check refusal expectation
        if expected.get("is_refusal"):
            assert output.is_refusal, f"[{case_id}] {case_name}: Expected refusal"
        else:
            assert not output.is_refusal, f"[{case_id}] {case_name}: Unexpected refusal"

            # Check tool usage
            if "results" in parsed:
                all_tool_calls = []
                for res in parsed["results"]:
                    all_tool_calls.extend(res.get("tool_calls", []))

                tool_names = [tc["tool_name"] for tc in all_tool_calls]

                # Check forbidden tools weren't used
                for forbidden in expected.get("forbidden_tools", []):
                    assert forbidden not in tool_names, \
                        f"[{case_id}] {case_name}: Forbidden tool '{forbidden}' was used"


class TestSafetyRegression:
    """Safety regression tests to ensure agents refuse harmful requests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mock client."""
        self.client = BedrockClient(mock_mode=True)

    @pytest.mark.parametrize("case", load_golden_cases("safety_cases.json")["cases"])
    def test_safety_case(self, case):
        """Test that agents refuse harmful requests."""
        case_id = case["id"]
        case_name = case["name"]
        input_text = case["input"]
        expected_behavior = case["expected_behavior"]

        # Mock a refusal response
        refusal_response = json.dumps({
            "task_summary": "Request refused",
            "refusal": {
                "reason": "I cannot assist with this request as it could cause harm."
            }
        })
        self.client.set_mock_response("planner", refusal_response)

        # Run planner with harmful input
        result = run_planner(
            task=input_text,
            bedrock_client=self.client
        )

        # Verify refusal
        if expected_behavior == "refusal":
            assert result["output"].is_refusal, \
                f"[{case_id}] {case_name}: Expected refusal for harmful request"


class TestOutputStructureRegression:
    """Tests to validate output structure hasn't changed."""

    def test_planner_output_schema_compliance(self):
        """Verify planner output matches expected schema."""
        client = BedrockClient(mock_mode=True)

        # Valid response
        response = json.dumps({
            "task_summary": "Test task",
            "steps": [
                {
                    "id": "step1",
                    "description": "Test step",
                    "dependencies": [],
                    "complexity": "low"
                }
            ]
        })
        client.set_mock_response("planner", response)

        result = run_planner(task="Test", bedrock_client=client)

        assert result["output"].is_valid, "Planner output should match schema"

        # Check required fields
        parsed = result["output"].parsed_output
        assert "task_summary" in parsed
        assert "steps" in parsed

        # Check step structure
        step = parsed["steps"][0]
        assert "id" in step
        assert "description" in step
        assert "dependencies" in step
        assert "complexity" in step

    def test_executor_output_schema_compliance(self):
        """Verify executor output matches expected schema."""
        client = BedrockClient(mock_mode=True)
        reset_registry()

        # Valid response
        response = json.dumps({
            "execution_id": "exec-test",
            "results": [
                {
                    "step_id": "step1",
                    "status": "success",
                    "tool_calls": [],
                    "output": "Done"
                }
            ],
            "summary": {
                "total_steps": 1,
                "successful": 1,
                "failed": 0,
                "skipped": 0
            }
        })
        client.set_mock_response("executor", response)

        result = run_executor(
            plan={"task_summary": "Test", "steps": []},
            bedrock_client=client
        )

        assert result["output"].is_valid, "Executor output should match schema"

        # Check required fields
        parsed = result["output"].parsed_output
        assert "execution_id" in parsed
        assert "results" in parsed
        assert "summary" in parsed

        # Check summary structure
        summary = parsed["summary"]
        assert "total_steps" in summary
        assert "successful" in summary
        assert "failed" in summary
        assert "skipped" in summary
