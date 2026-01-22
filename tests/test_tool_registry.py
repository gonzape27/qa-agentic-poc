"""
Tests for the Tool Registry module.
"""

import pytest

from runtime.tool_registry import (
    ToolRegistry,
    ToolDefinition,
    ToolMode,
    get_registry,
    reset_registry
)


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_default_tools_registered(self, tool_registry):
        """Test that default tools are registered on initialization."""
        tools = tool_registry.list_tools()

        assert "read_file" in tools
        assert "write_file" in tools
        assert "http_request" in tools
        assert "database_query" in tools
        assert "shell_command" in tools
        assert "search" in tools

    def test_register_custom_tool(self, tool_registry):
        """Test registering a custom tool."""
        tool = ToolDefinition(
            name="custom_tool",
            description="A custom tool for testing",
            parameters={
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                }
            },
            stub_response="custom response"
        )

        tool_registry.register(tool)
        assert "custom_tool" in tool_registry.list_tools()

    def test_get_tool(self, tool_registry):
        """Test getting a tool by name."""
        tool = tool_registry.get("read_file")

        assert tool is not None
        assert tool.name == "read_file"
        assert "file" in tool.description.lower()

    def test_get_nonexistent_tool(self, tool_registry):
        """Test getting a non-existent tool returns None."""
        tool = tool_registry.get("nonexistent")
        assert tool is None

    def test_get_tool_schemas(self, tool_registry):
        """Test getting tool schemas in Claude format."""
        schemas = tool_registry.get_tool_schemas()

        assert len(schemas) > 0
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "input_schema" in schema

    def test_execute_stub_mode(self, tool_registry):
        """Test executing a tool in stub mode."""
        result = tool_registry.execute(
            "read_file",
            {"path": "/test/file.txt"}
        )

        assert "[STUB]" in result

    def test_execute_logs_call(self, tool_registry):
        """Test that tool execution is logged."""
        tool_registry.execute(
            "read_file",
            {"path": "/test/file.txt"}
        )

        log = tool_registry.get_call_log()
        assert len(log) == 1
        assert log[0].tool_name == "read_file"
        assert log[0].arguments == {"path": "/test/file.txt"}

    def test_clear_call_log(self, tool_registry):
        """Test clearing the call log."""
        tool_registry.execute("read_file", {"path": "/test"})
        assert len(tool_registry.get_call_log()) == 1

        tool_registry.clear_call_log()
        assert len(tool_registry.get_call_log()) == 0

    def test_set_stub_response(self, tool_registry):
        """Test setting a custom stub response."""
        tool_registry.set_stub_response("read_file", "Custom content")

        result = tool_registry.execute(
            "read_file",
            {"path": "/test"}
        )

        assert result == "Custom content"

    def test_execute_nonexistent_tool_raises_error(self, tool_registry):
        """Test that executing a non-existent tool raises an error."""
        with pytest.raises(ValueError) as exc_info:
            tool_registry.execute("nonexistent", {})

        assert "not found" in str(exc_info.value)


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_registry_creates_singleton(self):
        """Test that get_registry returns the same instance."""
        reset_registry()

        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_reset_registry(self):
        """Test that reset_registry clears the singleton."""
        reset_registry()
        registry1 = get_registry()

        reset_registry()
        registry2 = get_registry()

        assert registry1 is not registry2
