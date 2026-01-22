"""
End-to-End Agent Workflow Tests

Tests the complete flow: Planner → Executor
Validates step execution and ensures no extra tool calls.
"""

import json
import pytest

from agents.planner.graph import run_planner
from agents.executor.graph import run_executor
from runtime.bedrock_client import BedrockClient
from runtime.tool_registry import ToolRegistry, ToolMode, reset_registry


class TestEndToEndWorkflow:
    """End-to-end tests for the planner → executor workflow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        reset_registry()
        yield
        reset_registry()

    def test_full_workflow_happy_path(self):
        """
        Test complete workflow: task → plan → execute.

        This test validates:
        1. Planner produces a valid plan
        2. Executor receives and processes the plan
        3. All steps are executed
        4. No unexpected errors occur
        """
        # Setup mock client
        client = BedrockClient(mock_mode=True)

        # Mock planner response
        planner_response = json.dumps({
            "task_summary": "Send welcome email to new user",
            "steps": [
                {
                    "id": "step1",
                    "description": "Validate user email format",
                    "dependencies": [],
                    "complexity": "low"
                },
                {
                    "id": "step2",
                    "description": "Check if user exists in database",
                    "dependencies": ["step1"],
                    "complexity": "low"
                },
                {
                    "id": "step3",
                    "description": "Send welcome email via email service",
                    "dependencies": ["step2"],
                    "complexity": "medium"
                }
            ]
        })

        # Mock executor response
        executor_response = json.dumps({
            "execution_id": "exec-e2e-001",
            "results": [
                {
                    "step_id": "step1",
                    "status": "success",
                    "tool_calls": [],
                    "output": "Email format is valid"
                },
                {
                    "step_id": "step2",
                    "status": "success",
                    "tool_calls": [
                        {
                            "tool_name": "database_query",
                            "arguments": {"query": "SELECT * FROM users WHERE email = ?"},
                            "result": "User found"
                        }
                    ],
                    "output": "User exists in database"
                },
                {
                    "step_id": "step3",
                    "status": "success",
                    "tool_calls": [
                        {
                            "tool_name": "http_request",
                            "arguments": {"method": "POST", "url": "https://email.service/send"},
                            "result": "Email sent"
                        }
                    ],
                    "output": "Welcome email sent successfully"
                }
            ],
            "summary": {
                "total_steps": 3,
                "successful": 3,
                "failed": 0,
                "skipped": 0
            }
        })

        client.set_mock_response("planner", planner_response)
        client.set_mock_response("executor", executor_response)

        # Step 1: Run planner
        planner_result = run_planner(
            task="Send a welcome email to the new user john@example.com",
            bedrock_client=client
        )

        # Validate planner output
        assert planner_result["error"] is None
        assert planner_result["output"] is not None
        assert planner_result["output"].is_valid is True
        assert planner_result["output"].is_refusal is False

        plan = planner_result["output"].parsed_output
        assert "steps" in plan
        assert len(plan["steps"]) == 3

        # Step 2: Run executor with the plan
        tool_registry = ToolRegistry(mode=ToolMode.STUB)

        executor_result = run_executor(
            plan=plan,
            bedrock_client=client,
            tool_registry=tool_registry
        )

        # Validate executor output
        assert executor_result["error"] is None
        assert executor_result["output"] is not None
        assert executor_result["output"].is_valid is True
        assert executor_result["output"].is_refusal is False

        execution = executor_result["output"].parsed_output
        assert "results" in execution
        assert "summary" in execution

        # Validate all steps completed successfully
        summary = execution["summary"]
        assert summary["total_steps"] == 3
        assert summary["successful"] == 3
        assert summary["failed"] == 0
        assert summary["skipped"] == 0

    def test_workflow_with_step_failure(self):
        """
        Test workflow where a step fails.

        Validates that failures are properly reported.
        """
        client = BedrockClient(mock_mode=True)

        # Planner response
        planner_response = json.dumps({
            "task_summary": "Process payment",
            "steps": [
                {
                    "id": "step1",
                    "description": "Validate payment details",
                    "dependencies": [],
                    "complexity": "low"
                },
                {
                    "id": "step2",
                    "description": "Charge credit card",
                    "dependencies": ["step1"],
                    "complexity": "high"
                }
            ]
        })

        # Executor response with failure
        executor_response = json.dumps({
            "execution_id": "exec-e2e-002",
            "results": [
                {
                    "step_id": "step1",
                    "status": "success",
                    "tool_calls": [],
                    "output": "Payment details valid"
                },
                {
                    "step_id": "step2",
                    "status": "failed",
                    "tool_calls": [
                        {
                            "tool_name": "http_request",
                            "arguments": {"method": "POST", "url": "https://payment.gateway/charge"},
                            "result": "Card declined"
                        }
                    ],
                    "error": "Payment gateway returned: Card declined"
                }
            ],
            "summary": {
                "total_steps": 2,
                "successful": 1,
                "failed": 1,
                "skipped": 0
            }
        })

        client.set_mock_response("planner", planner_response)
        client.set_mock_response("executor", executor_response)

        # Run planner
        planner_result = run_planner(
            task="Process payment of $50",
            bedrock_client=client
        )
        plan = planner_result["output"].parsed_output

        # Run executor
        executor_result = run_executor(
            plan=plan,
            bedrock_client=client
        )

        # Validate failure is captured
        execution = executor_result["output"].parsed_output
        assert execution["summary"]["failed"] == 1

        # Find the failed step
        failed_step = next(
            r for r in execution["results"]
            if r["status"] == "failed"
        )
        assert failed_step["step_id"] == "step2"
        assert "error" in failed_step

    def test_workflow_refusal_at_executor(self):
        """
        Test workflow where executor refuses to execute.

        Validates safety behavior in the execution phase.
        """
        client = BedrockClient(mock_mode=True)

        # Planner produces plan (incorrectly planning harmful task)
        planner_response = json.dumps({
            "task_summary": "Access restricted data",
            "steps": [
                {
                    "id": "step1",
                    "description": "Bypass authentication",
                    "dependencies": [],
                    "complexity": "high"
                }
            ]
        })

        # Executor refuses
        executor_response = json.dumps({
            "execution_id": "exec-e2e-003",
            "refusal": {
                "reason": "Cannot execute steps that bypass security controls",
                "step_id": "step1"
            }
        })

        client.set_mock_response("planner", planner_response)
        client.set_mock_response("executor", executor_response)

        # Run workflow
        planner_result = run_planner(
            task="Get admin access",
            bedrock_client=client
        )
        plan = planner_result["output"].parsed_output

        executor_result = run_executor(
            plan=plan,
            bedrock_client=client
        )

        # Validate refusal
        assert executor_result["output"].is_refusal is True
        assert "refusal" in executor_result["output"].parsed_output

    def test_no_extra_tool_calls(self):
        """
        Test that executor doesn't make unauthorized tool calls.

        Validates that only expected tools are called for each step.
        """
        client = BedrockClient(mock_mode=True)
        tool_registry = ToolRegistry(mode=ToolMode.STUB)

        # Clear any previous calls
        tool_registry.clear_call_log()

        # Simple plan with known tool requirements
        planner_response = json.dumps({
            "task_summary": "Read a file",
            "steps": [
                {
                    "id": "step1",
                    "description": "Read config file",
                    "dependencies": [],
                    "complexity": "low"
                }
            ]
        })

        # Executor response with single tool call
        executor_response = json.dumps({
            "execution_id": "exec-e2e-004",
            "results": [
                {
                    "step_id": "step1",
                    "status": "success",
                    "tool_calls": [
                        {
                            "tool_name": "read_file",
                            "arguments": {"path": "/config/app.json"},
                            "result": "Config loaded"
                        }
                    ],
                    "output": "Config file read successfully"
                }
            ],
            "summary": {
                "total_steps": 1,
                "successful": 1,
                "failed": 0,
                "skipped": 0
            }
        })

        client.set_mock_response("planner", planner_response)
        client.set_mock_response("executor", executor_response)

        # Run workflow
        planner_result = run_planner(
            task="Read the config file",
            bedrock_client=client
        )
        plan = planner_result["output"].parsed_output

        executor_result = run_executor(
            plan=plan,
            bedrock_client=client,
            tool_registry=tool_registry
        )

        # Check execution results
        execution = executor_result["output"].parsed_output
        all_tool_calls = []

        for result in execution.get("results", []):
            all_tool_calls.extend(result.get("tool_calls", []))

        # Validate only expected tool was called
        tool_names = [tc["tool_name"] for tc in all_tool_calls]

        # Should only have read_file, nothing else
        assert "read_file" in tool_names
        # Ensure no dangerous tools were called
        dangerous_tools = ["shell_command", "write_file", "database_query"]
        for dangerous in dangerous_tools:
            assert dangerous not in tool_names, f"Unexpected call to {dangerous}"
