"""
AWS Bedrock Client for Claude Models

Handles model invocation with support for mock mode during testing.
"""

import json
import os
from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for model invocation."""
    model_id: str = Field(
        default_factory=lambda: os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
    )
    max_tokens: int = 4096
    temperature: float = 0.0
    top_p: float = 1.0


class MockResponse(BaseModel):
    """Mock response configuration for testing."""
    response: str
    should_fail: bool = False
    error_message: str = ""


class BedrockClient:
    """
    Client for invoking Claude models via AWS Bedrock.

    Supports mock mode for testing without AWS credentials.
    """

    def __init__(
        self,
        region: Optional[str] = None,
        mock_mode: Optional[bool] = None
    ):
        """
        Initialize the Bedrock client.

        Args:
            region: AWS region. Defaults to AWS_REGION env var or us-east-1.
            mock_mode: Enable mock mode. Defaults to MOCK_BEDROCK env var.
        """
        self.region = region or os.getenv("AWS_REGION", "us-east-1")

        # Determine mock mode
        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            self.mock_mode = os.getenv("MOCK_BEDROCK", "false").lower() == "true"

        self._client = None
        self._mock_responses: dict[str, MockResponse] = {}
        self._invocation_log: list[dict] = []

    @property
    def client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None and not self.mock_mode:
            import boto3
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region
            )
        return self._client

    def set_mock_response(
        self,
        agent_name: str,
        response: str,
        should_fail: bool = False,
        error_message: str = ""
    ) -> None:
        """
        Set a mock response for a specific agent.

        Args:
            agent_name: Name of the agent to mock
            response: The response to return
            should_fail: Whether the call should raise an error
            error_message: Error message if should_fail is True
        """
        self._mock_responses[agent_name] = MockResponse(
            response=response,
            should_fail=should_fail,
            error_message=error_message
        )

    def set_default_mock_response(self, response: str) -> None:
        """Set a default mock response for all agents."""
        self._mock_responses["__default__"] = MockResponse(response=response)

    def get_invocation_log(self) -> list[dict]:
        """Get the log of all invocations (useful for testing)."""
        return self._invocation_log.copy()

    def clear_invocation_log(self) -> None:
        """Clear the invocation log."""
        self._invocation_log.clear()

    def invoke(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list[dict]] = None,
        config: Optional[ModelConfig] = None,
        agent_name: Optional[str] = None
    ) -> str:
        """
        Invoke the model with the given prompts.

        Args:
            system_prompt: System prompt for the model
            user_message: User message to process
            tools: Optional list of tool definitions
            config: Optional model configuration
            agent_name: Optional agent name for mock responses

        Returns:
            Model response as a string

        Raises:
            Exception: If invocation fails
        """
        config = config or ModelConfig()

        # Log the invocation
        invocation = {
            "system_prompt": system_prompt,
            "user_message": user_message,
            "tools": tools,
            "config": config.model_dump(),
            "agent_name": agent_name
        }
        self._invocation_log.append(invocation)

        if self.mock_mode:
            return self._mock_invoke(agent_name)

        return self._real_invoke(system_prompt, user_message, tools, config)

    def _mock_invoke(self, agent_name: Optional[str] = None) -> str:
        """Handle mock invocation."""
        # Check for agent-specific mock
        if agent_name and agent_name in self._mock_responses:
            mock = self._mock_responses[agent_name]
        elif "__default__" in self._mock_responses:
            mock = self._mock_responses["__default__"]
        else:
            # Return a generic mock response
            return json.dumps({
                "task_summary": "Mock response - no specific mock configured",
                "steps": []
            })

        if mock.should_fail:
            raise Exception(mock.error_message or "Mock failure")

        return mock.response

    def _real_invoke(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list[dict]],
        config: ModelConfig
    ) -> str:
        """Handle real Bedrock invocation."""
        # Build the request body for Claude
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }

        # Add tools if provided
        if tools:
            body["tools"] = tools

        response = self.client.invoke_model(
            modelId=config.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response["body"].read())

        # Extract text from Claude's response format
        content = response_body.get("content", [])
        text_parts = []

        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                # Include tool use in response for tracking
                text_parts.append(json.dumps({
                    "tool_use": {
                        "name": block.get("name"),
                        "input": block.get("input")
                    }
                }))

        return "\n".join(text_parts)


def create_client(mock_mode: Optional[bool] = None) -> BedrockClient:
    """
    Factory function to create a BedrockClient.

    Args:
        mock_mode: Override mock mode setting

    Returns:
        Configured BedrockClient instance
    """
    return BedrockClient(mock_mode=mock_mode)
