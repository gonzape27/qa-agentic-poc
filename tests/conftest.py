"""
Pytest configuration and fixtures.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.bedrock_client import BedrockClient
from runtime.tool_registry import ToolRegistry, ToolMode, reset_registry


@pytest.fixture(autouse=True)
def setup_mock_mode():
    """Ensure mock mode is enabled for all tests."""
    os.environ["MOCK_BEDROCK"] = "true"
    yield
    # Cleanup
    if "MOCK_BEDROCK" in os.environ:
        del os.environ["MOCK_BEDROCK"]


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client for testing."""
    client = BedrockClient(mock_mode=True)
    return client


@pytest.fixture
def tool_registry():
    """Create a fresh tool registry for testing."""
    reset_registry()
    registry = ToolRegistry(mode=ToolMode.STUB)
    yield registry
    reset_registry()


@pytest.fixture
def valid_planner_response():
    """Sample valid planner response."""
    return json.dumps({
        "task_summary": "Create a new user account",
        "steps": [
            {
                "id": "step1",
                "description": "Validate user input",
                "dependencies": [],
                "complexity": "low"
            },
            {
                "id": "step2",
                "description": "Check if email exists",
                "dependencies": ["step1"],
                "complexity": "low"
            },
            {
                "id": "step3",
                "description": "Create user record",
                "dependencies": ["step2"],
                "complexity": "medium"
            }
        ]
    })


@pytest.fixture
def valid_executor_response():
    """Sample valid executor response."""
    return json.dumps({
        "execution_id": "exec-001",
        "results": [
            {
                "step_id": "step1",
                "status": "success",
                "tool_calls": [],
                "output": "Input validated successfully"
            },
            {
                "step_id": "step2",
                "status": "success",
                "tool_calls": [
                    {
                        "tool_name": "database_query",
                        "arguments": {"query": "SELECT * FROM users WHERE email = ?"},
                        "result": "No existing user found"
                    }
                ],
                "output": "Email is available"
            },
            {
                "step_id": "step3",
                "status": "success",
                "tool_calls": [
                    {
                        "tool_name": "database_query",
                        "arguments": {"query": "INSERT INTO users..."},
                        "result": "User created"
                    }
                ],
                "output": "User account created"
            }
        ],
        "summary": {
            "total_steps": 3,
            "successful": 3,
            "failed": 0,
            "skipped": 0
        }
    })


@pytest.fixture
def refusal_response():
    """Sample refusal response."""
    return json.dumps({
        "task_summary": "Harmful request detected",
        "refusal": {
            "reason": "I cannot assist with creating malware or any harmful software."
        }
    })


@pytest.fixture
def ambiguous_response():
    """Sample response requesting clarification."""
    return json.dumps({
        "task_summary": "Task requires clarification",
        "clarification_needed": "Please specify which type of account you want to create: admin, standard, or guest?"
    })
