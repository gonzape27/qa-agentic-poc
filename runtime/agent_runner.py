"""
LangGraph Agent Runtime

Loads system prompts, executes LangGraph nodes, validates outputs, and detects refusals.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

import jsonschema
from pydantic import BaseModel, Field

from runtime.bedrock_client import BedrockClient, ModelConfig


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    system_prompt: str
    output_schema: dict


class AgentOutput(BaseModel):
    """Standardized agent output."""
    agent_name: str
    raw_response: str
    parsed_output: Optional[dict] = None
    is_valid: bool = False
    is_refusal: bool = False
    validation_errors: list[str] = Field(default_factory=list)


class AgentRunner:
    """
    Runtime for executing LangGraph-based agents.

    Handles loading prompts, executing models, and validating outputs.
    """

    AGENTS_DIR = Path(__file__).parent.parent / "agents"

    def __init__(self, bedrock_client: Optional[BedrockClient] = None):
        """
        Initialize the agent runner.

        Args:
            bedrock_client: Optional BedrockClient instance. If not provided,
                          a default client will be created.
        """
        self.bedrock_client = bedrock_client or BedrockClient()
        self._agent_cache: dict[str, AgentConfig] = {}

    def load_agent(self, agent_name: str) -> AgentConfig:
        """
        Load an agent's configuration from disk.

        Args:
            agent_name: Name of the agent (folder name in agents/)

        Returns:
            AgentConfig with loaded prompt and schema

        Raises:
            FileNotFoundError: If agent folder or required files don't exist
        """
        if agent_name in self._agent_cache:
            return self._agent_cache[agent_name]

        agent_dir = self.AGENTS_DIR / agent_name

        if not agent_dir.exists():
            raise FileNotFoundError(f"Agent '{agent_name}' not found at {agent_dir}")

        # Load system prompt
        system_prompt_path = agent_dir / "system.md"
        if not system_prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found: {system_prompt_path}")

        system_prompt = system_prompt_path.read_text(encoding="utf-8")

        # Load output schema
        schema_path = agent_dir / "schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        output_schema = json.loads(schema_path.read_text(encoding="utf-8"))

        config = AgentConfig(
            name=agent_name,
            system_prompt=system_prompt,
            output_schema=output_schema
        )

        self._agent_cache[agent_name] = config
        return config

    def validate_output(self, output: dict, schema: dict) -> tuple[bool, list[str]]:
        """
        Validate agent output against its JSON schema.

        Args:
            output: Parsed JSON output from the agent
            schema: JSON schema to validate against

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        try:
            jsonschema.validate(instance=output, schema=schema)
            return True, []
        except jsonschema.ValidationError as e:
            errors.append(str(e.message))
            return False, errors
        except jsonschema.SchemaError as e:
            errors.append(f"Invalid schema: {e.message}")
            return False, errors

    def detect_refusal(self, output: dict) -> bool:
        """
        Detect if the agent output indicates a refusal.

        Args:
            output: Parsed JSON output from the agent

        Returns:
            True if the output contains a refusal
        """
        # Check for explicit refusal field
        if "refusal" in output and output["refusal"]:
            return True

        # Check for refusal patterns in common fields
        refusal_indicators = [
            "i cannot", "i can't", "i'm unable", "i am unable",
            "refuse", "not allowed", "cannot assist", "cannot help"
        ]

        # Check string fields for refusal language
        for key, value in output.items():
            if isinstance(value, str):
                lower_value = value.lower()
                if any(indicator in lower_value for indicator in refusal_indicators):
                    return True

        return False

    def parse_response(self, response: str) -> Optional[dict]:
        """
        Parse the model response as JSON.

        Args:
            response: Raw string response from the model

        Returns:
            Parsed dictionary or None if parsing fails
        """
        # Try to extract JSON from the response
        response = response.strip()

        # Handle markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    return None
            return None

    def run_agent(
        self,
        agent_name: str,
        input_payload: str | dict,
        tools: Optional[list[dict]] = None,
        model_config: Optional[ModelConfig] = None
    ) -> AgentOutput:
        """
        Execute an agent with the given input.

        Args:
            agent_name: Name of the agent to run
            input_payload: Input message or data for the agent
            tools: Optional list of tool definitions for the agent
            model_config: Optional model configuration override

        Returns:
            AgentOutput with results and validation status
        """
        # Load agent configuration
        agent_config = self.load_agent(agent_name)

        # Convert input to string if necessary
        if isinstance(input_payload, dict):
            user_message = json.dumps(input_payload, indent=2)
        else:
            user_message = str(input_payload)

        # Build the prompt with schema instructions
        schema_instruction = (
            "\n\n## Response Format\n"
            "You must respond with valid JSON that conforms to the following schema:\n"
            f"```json\n{json.dumps(agent_config.output_schema, indent=2)}\n```"
        )

        full_system_prompt = agent_config.system_prompt + schema_instruction

        # Invoke the model
        raw_response = self.bedrock_client.invoke(
            system_prompt=full_system_prompt,
            user_message=user_message,
            tools=tools,
            config=model_config,
            agent_name=agent_name
        )

        # Parse the response
        parsed_output = self.parse_response(raw_response)

        # Create output object
        output = AgentOutput(
            agent_name=agent_name,
            raw_response=raw_response
        )

        if parsed_output is None:
            output.validation_errors.append("Failed to parse response as JSON")
            return output

        output.parsed_output = parsed_output

        # Validate against schema
        is_valid, errors = self.validate_output(parsed_output, agent_config.output_schema)
        output.is_valid = is_valid
        output.validation_errors.extend(errors)

        # Check for refusal
        output.is_refusal = self.detect_refusal(parsed_output)

        return output


def run_agent(
    agent_name: str,
    input_payload: str | dict,
    tools: Optional[list[dict]] = None,
    model_config: Optional[ModelConfig] = None
) -> AgentOutput:
    """
    Convenience function to run an agent.

    This is the main entry point for running agents.

    Args:
        agent_name: Name of the agent to run
        input_payload: Input message or data for the agent
        tools: Optional list of tool definitions for the agent
        model_config: Optional model configuration override

    Returns:
        AgentOutput with results and validation status
    """
    runner = AgentRunner()
    return runner.run_agent(agent_name, input_payload, tools, model_config)
