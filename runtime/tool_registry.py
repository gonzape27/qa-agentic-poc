"""
Tool Registry with Stubbing Support

Defines tools for agents and provides fake implementations for testing.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum


class ToolMode(Enum):
    """Mode for tool execution."""
    REAL = "real"
    STUB = "stub"


@dataclass
class ToolCall:
    """Record of a tool invocation."""
    tool_name: str
    arguments: dict
    result: Any
    mode: ToolMode


@dataclass
class ToolDefinition:
    """Definition of a tool available to agents."""
    name: str
    description: str
    parameters: dict
    real_implementation: Optional[Callable] = None
    stub_implementation: Optional[Callable] = None
    stub_response: Any = None


class ToolRegistry:
    """
    Registry for managing tools available to agents.

    Supports both real and stubbed implementations for testing.
    """

    def __init__(self, mode: ToolMode = ToolMode.STUB):
        """
        Initialize the tool registry.

        Args:
            mode: Default execution mode for tools
        """
        self.mode = mode
        self._tools: dict[str, ToolDefinition] = {}
        self._call_log: list[ToolCall] = []
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        # File operations tool
        self.register(ToolDefinition(
            name="read_file",
            description="Read the contents of a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            },
            stub_response="[STUB] File contents would be here"
        ))

        self.register(ToolDefinition(
            name="write_file",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            },
            stub_response="[STUB] File written successfully"
        ))

        # HTTP request tool
        self.register(ToolDefinition(
            name="http_request",
            description="Make an HTTP request to an external API",
            parameters={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "description": "HTTP method"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to request"
                    },
                    "body": {
                        "type": "object",
                        "description": "Request body (for POST/PUT)"
                    }
                },
                "required": ["method", "url"]
            },
            stub_response={"status": 200, "body": "[STUB] Response data"}
        ))

        # Database query tool
        self.register(ToolDefinition(
            name="database_query",
            description="Execute a database query",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "params": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Query parameters"
                    }
                },
                "required": ["query"]
            },
            stub_response={"rows": [], "affected": 0, "message": "[STUB] Query executed"}
        ))

        # Shell command tool
        self.register(ToolDefinition(
            name="shell_command",
            description="Execute a shell command",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory for the command"
                    }
                },
                "required": ["command"]
            },
            stub_response={"exit_code": 0, "stdout": "[STUB] Command output", "stderr": ""}
        ))

        # Search tool
        self.register(ToolDefinition(
            name="search",
            description="Search for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["query"]
            },
            stub_response={"results": [{"title": "[STUB] Result", "url": "https://example.com"}]}
        ))

    def register(self, tool: ToolDefinition) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool definition to register
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        """
        Get a tool by name.

        Args:
            name: Name of the tool

        Returns:
            Tool definition or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())

    def get_tool_schemas(self) -> list[dict]:
        """
        Get tool schemas in the format expected by Claude.

        Returns:
            List of tool definitions for the model
        """
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters
            })
        return schemas

    def execute(
        self,
        tool_name: str,
        arguments: dict,
        mode: Optional[ToolMode] = None
    ) -> Any:
        """
        Execute a tool with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            mode: Override execution mode

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool is not found
        """
        tool = self.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found")

        effective_mode = mode or self.mode

        if effective_mode == ToolMode.REAL and tool.real_implementation:
            result = tool.real_implementation(**arguments)
        elif tool.stub_implementation:
            result = tool.stub_implementation(**arguments)
        else:
            result = tool.stub_response

        # Log the call
        call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            mode=effective_mode
        )
        self._call_log.append(call)

        return result

    def get_call_log(self) -> list[ToolCall]:
        """Get the log of all tool calls."""
        return self._call_log.copy()

    def clear_call_log(self) -> None:
        """Clear the tool call log."""
        self._call_log.clear()

    def set_stub_response(self, tool_name: str, response: Any) -> None:
        """
        Set a custom stub response for a tool.

        Args:
            tool_name: Name of the tool
            response: Response to return when tool is called in stub mode
        """
        tool = self.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found")
        tool.stub_response = response


# Global registry instance
_default_registry: Optional[ToolRegistry] = None


def get_registry(mode: ToolMode = ToolMode.STUB) -> ToolRegistry:
    """
    Get or create the default tool registry.

    Args:
        mode: Execution mode for the registry

    Returns:
        ToolRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry(mode=mode)
    return _default_registry


def reset_registry() -> None:
    """Reset the default registry (useful for testing)."""
    global _default_registry
    _default_registry = None
