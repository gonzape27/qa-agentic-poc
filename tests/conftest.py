"""
Pytest configuration and fixtures.
"""

import json
import logging
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.bedrock_client import BedrockClient
from runtime.tool_registry import ToolRegistry, ToolMode, reset_registry

# Configure logging to capture test output
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ============================================================================
# pytest-html hooks for enhanced reporting
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "logs: mark test to include detailed logs in report"
    )


def pytest_html_results_summary(prefix, summary, postfix):
    """Add custom CSS to expand all test details by default."""
    prefix.extend([
        "<style>",
        "  /* Show all test details expanded by default */",
        "  .extras-row { display: table-row !important; }",
        "  .extras { display: block !important; }",
        "  .col-result { cursor: pointer; }",
        "  /* Style the log divs */",
        "  .log { margin: 8px 0; padding: 10px; background: #f5f5f5; border-left: 3px solid #4CAF50; }",
        "  .log strong { color: #333; }",
        "  .log pre { margin: 5px 0 0 0; white-space: pre-wrap; word-wrap: break-word; background: #fff; padding: 8px; border-radius: 4px; max-height: 300px; overflow-y: auto; }",
        "  /* Color code by test result */",
        "  tr.passed .log { border-left-color: #4CAF50; }",
        "  tr.failed .log { border-left-color: #f44336; }",
        "  tr.xfailed .log { border-left-color: #ff9800; }",
        "</style>",
        "<script>",
        "  // Auto-expand all test rows on page load",
        "  document.addEventListener('DOMContentLoaded', function() {",
        "    // Find all collapsed rows and expand them",
        "    document.querySelectorAll('.extras-row').forEach(function(row) {",
        "      row.style.display = 'table-row';",
        "    });",
        "    document.querySelectorAll('.extras').forEach(function(el) {",
        "      el.style.display = 'block';",
        "    });",
        "  });",
        "</script>",
    ])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to add extra information to HTML report for ALL tests.
    This captures stdout, stderr, and custom logs for both passing and failing tests.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        # Import here to avoid issues if pytest-html is not installed
        try:
            from pytest_html import extras
        except ImportError:
            return

        # Get the extras list for HTML report (use 'extras' not 'extra' to avoid deprecation)
        extra_list = getattr(report, "extras", [])

        # Add test docstring as description
        if item.function.__doc__:
            extra_list.append(extras.html(
                f'<div class="log"><strong>Description:</strong> {item.function.__doc__.strip()}</div>'
            ))

        # Add captured stdout if any
        if hasattr(report, "capstdout") and report.capstdout:
            extra_list.append(extras.html(
                f'<div class="log"><strong>Stdout:</strong><pre>{report.capstdout}</pre></div>'
            ))

        # Add captured stderr if any
        if hasattr(report, "capstderr") and report.capstderr:
            extra_list.append(extras.html(
                f'<div class="log"><strong>Stderr:</strong><pre>{report.capstderr}</pre></div>'
            ))

        # Add captured log if any
        if hasattr(report, "caplog") and report.caplog:
            extra_list.append(extras.html(
                f'<div class="log"><strong>Logs:</strong><pre>{report.caplog}</pre></div>'
            ))

        # Add any custom properties set during the test
        if hasattr(item, "test_details"):
            for key, value in item.test_details.items():
                extra_list.append(extras.html(
                    f'<div class="log"><strong>{key}:</strong><pre>{value}</pre></div>'
                ))

        report.extras = extra_list


@pytest.fixture
def test_logger(request):
    """
    Fixture that provides a logger and captures output for the HTML report.
    Usage: def test_example(test_logger):
               test_logger.info("This will appear in the report")
    """
    # Create a test-specific logger
    test_name = request.node.name
    log = logging.getLogger(test_name)
    log.setLevel(logging.DEBUG)

    # Store details that will be added to the report
    request.node.test_details = {}

    def add_detail(key: str, value: str):
        """Add a custom detail to the test report."""
        request.node.test_details[key] = value

    log.add_detail = add_detail
    return log


@pytest.fixture
def report_details(request):
    """
    Fixture to add custom details to the HTML report.
    Usage: def test_example(report_details):
               report_details("Input", "some input value")
               report_details("Expected", "expected output")
    """
    request.node.test_details = {}

    def add_detail(key: str, value):
        """Add a key-value detail to the test report."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2)
        request.node.test_details[key] = str(value)

    return add_detail


@pytest.fixture(autouse=True)
def setup_mock_mode():
    """
    Setup mock mode based on environment.

    If MOCK_BEDROCK is already set (from .env or command line), respect it.
    Otherwise, default to mock mode for safety.
    """
    original_value = os.environ.get("MOCK_BEDROCK")

    # Only set mock mode if not already configured
    if original_value is None:
        os.environ["MOCK_BEDROCK"] = "true"

    yield

    # Restore original state
    if original_value is None and "MOCK_BEDROCK" in os.environ:
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
