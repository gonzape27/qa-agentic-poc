# QA Agentic POC

LangGraph-based agent testing framework with AWS Bedrock integration. This project demonstrates how to treat AI agent prompts as versioned code and test them systematically.

## Features

- **LangGraph Agents**: Planner and Executor agents with defined responsibilities
- **Versioned Prompts**: System prompts stored as markdown files
- **Schema Validation**: JSON schemas enforce output structure
- **Mock Mode**: Test without AWS credentials
- **CI/CD Integration**: GitHub Actions with test reports
- **Safety Testing**: Regression tests for harmful request handling

## Project Structure

```
qa-agentic-poc/
├── agents/                     # Agent definitions
│   ├── planner/               # Planning agent
│   │   ├── system.md          # System prompt
│   │   ├── schema.json        # Output schema
│   │   └── graph.py           # LangGraph definition
│   └── executor/              # Execution agent
│       ├── system.md
│       ├── schema.json
│       └── graph.py
├── runtime/                   # Core runtime components
│   ├── agent_runner.py        # Agent execution engine
│   ├── bedrock_client.py      # AWS Bedrock integration
│   └── tool_registry.py       # Tool definitions & stubs
├── tests/                     # Test suite
│   ├── golden/                # Golden test cases
│   ├── test_*.py              # Test files
│   └── conftest.py            # Pytest fixtures
├── docker/                    # Docker configuration
├── .github/workflows/         # CI/CD pipelines
└── scripts/                   # Utility scripts
```

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Local Setup

```bash
# Clone the repository
git clone https://github.com/gonzape27/qa-agentic-poc.git
cd qa-agentic-poc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running Tests Locally

```bash
# Run all tests in mock mode (no AWS needed)
make test-mock

# Run tests with HTML report
make test-html

# Run tests like CI
make test-ci
```

Or using scripts:

```bash
# Linux/Mac
./scripts/run_tests.sh

# Windows PowerShell
.\scripts\run_tests.ps1
```

### Test Reports

After running tests, reports are generated in the `reports/` directory:

- `reports/report.html` - Interactive HTML report
- `reports/junit.xml` - JUnit XML for CI integration

Open `reports/report.html` in a browser to view detailed test results.

## Agent Architecture

### Planner Agent

The Planner agent breaks down tasks into executable steps:

- **Input**: Natural language task description
- **Output**: Structured plan with steps, dependencies, and complexity
- **Safety**: Refuses harmful requests, asks for clarification on ambiguous input

### Executor Agent

The Executor agent carries out planned steps using available tools:

- **Input**: Plan from Planner agent
- **Output**: Execution results with tool call logs
- **Safety**: Validates steps before execution, refuses dangerous operations

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Testing Configuration
MOCK_BEDROCK=true  # Set to false for real Bedrock calls
```

### Mock Mode

For testing without AWS credentials, set `MOCK_BEDROCK=true`. The Bedrock client will return configurable mock responses.

```python
from runtime.bedrock_client import BedrockClient

client = BedrockClient(mock_mode=True)
client.set_mock_response("planner", '{"task_summary": "Test", "steps": []}')
```

## Testing Strategy

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Agent workflow testing
3. **E2E Tests**: Full planner → executor pipeline
4. **Regression Tests**: Golden input/output validation
5. **Safety Tests**: Harmful request handling

### Golden Test Cases

Golden test cases are stored in `tests/golden/`:

- `planner_cases.json` - Planner agent test scenarios
- `executor_cases.json` - Executor agent test scenarios
- `safety_cases.json` - Safety/refusal test scenarios

### Adding New Test Cases

1. Add your test case to the appropriate JSON file
2. Run tests to validate behavior
3. Commit changes to track prompt behavior over time

## Docker

### Build and Run

```bash
# Build image
docker build -t qa-agentic-poc -f docker/Dockerfile .

# Run tests in container
docker run --rm -v $(pwd)/reports:/app/reports qa-agentic-poc
```

### Docker Compose

```bash
cd docker

# Run tests in mock mode
docker-compose up test

# Run with real Bedrock (requires AWS credentials)
docker-compose up test-real
```

## CI/CD

### GitHub Actions

The repository includes a CI pipeline (`.github/workflows/agent-tests.yml`) that:

1. Runs tests on push/PR to main
2. Generates HTML and JUnit reports
3. Uploads reports as artifacts
4. Publishes test summary to PR

### Viewing CI Reports

1. Go to the Actions tab in GitHub
2. Click on a workflow run
3. Download the `test-reports` artifact
4. Open `report.html` in a browser

## Adding a New Agent

1. Create agent directory:
   ```bash
   mkdir -p agents/my_agent
   ```

2. Create system prompt (`agents/my_agent/system.md`):
   ```markdown
   # My Agent

   You are an agent that does X.

   ## Role
   - Responsibility 1
   - Responsibility 2

   ## Output Requirements
   - Always respond with JSON
   ```

3. Create output schema (`agents/my_agent/schema.json`):
   ```json
   {
     "$schema": "http://json-schema.org/draft-07/schema#",
     "type": "object",
     "properties": {
       "result": {"type": "string"}
     },
     "required": ["result"]
   }
   ```

4. Create graph definition (`agents/my_agent/graph.py`):
   ```python
   from langgraph.graph import StateGraph, END
   from runtime.agent_runner import AgentRunner

   def create_my_agent_graph():
       # Define your graph
       pass
   ```

5. Add tests in `tests/test_my_agent.py`

6. Add golden test cases in `tests/golden/`

## Troubleshooting

### Tests fail with import errors

Ensure you're running from the project root and have installed dependencies:

```bash
pip install -r requirements.txt
export PYTHONPATH=$(pwd)
```

### Mock mode not working

Verify the environment variable is set:

```bash
echo $MOCK_BEDROCK  # Should print "true"
```

### Schema validation errors

Check that your agent's output matches the schema in `schema.json`. Use a JSON validator to verify.

## License

MIT
