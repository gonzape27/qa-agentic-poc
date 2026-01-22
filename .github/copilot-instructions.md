# GitHub Copilot Instructions

This repository contains a LangGraph-based agent testing framework for AWS Bedrock.

## Project Structure

```
qa-agentic-poc/
├── agents/                  # Agent definitions
│   ├── planner/            # Planning agent
│   │   ├── system.md       # System prompt
│   │   ├── schema.json     # Output JSON schema
│   │   └── graph.py        # LangGraph definition
│   └── executor/           # Execution agent
│       ├── system.md
│       ├── schema.json
│       └── graph.py
├── runtime/                 # Core runtime components
│   ├── agent_runner.py     # Agent execution engine
│   ├── bedrock_client.py   # AWS Bedrock client (with mock mode)
│   └── tool_registry.py    # Tool definitions and stubs
├── tests/                   # Test suite
│   ├── conftest.py         # Pytest fixtures
│   ├── test_*.py           # Test files
│   └── golden/             # Golden test cases
└── scripts/                 # Utility scripts
```

## Testing Guidelines

When generating tests for this project:

1. **Use pytest fixtures** from `tests/conftest.py`:
   - `mock_bedrock_client` - Mocked Bedrock client
   - `tool_registry` - Fresh tool registry instance
   - `valid_planner_response` - Sample planner response
   - `valid_executor_response` - Sample executor response
   - `report_details` - Add details to HTML report

2. **Test patterns**:
   ```python
   def test_example(self, mock_bedrock_client, tool_registry):
       """Test description."""
       mock_bedrock_client.set_mock_response("agent_name", '{"json": "response"}')
       # ... test logic
       assert result.is_valid is True
   ```

3. **Coverage requirements**:
   - Minimum 90% coverage required
   - Focus on `runtime/` and `agents/` directories
   - Use `MOCK_BEDROCK=true` for fast tests

4. **Test categories**:
   - Happy path tests
   - Error handling tests
   - Edge cases (invalid JSON, refusals, etc.)
   - Schema validation tests

## Key Classes

- `AgentRunner` - Loads and runs agents with schema validation
- `BedrockClient` - AWS Bedrock client with mock mode for testing
- `ToolRegistry` - Manages tool definitions with stub responses
- `AgentOutput` - Structured output with validation status

## Mock Mode

Tests run with `MOCK_BEDROCK=true` by default:
```python
mock_bedrock_client.set_mock_response("planner", json.dumps({
    "task_summary": "...",
    "steps": [...]
}))
```

## Running Tests

```bash
make test           # Run tests
make coverage       # Run with coverage
make coverage-check # Verify >= 90% coverage
```
