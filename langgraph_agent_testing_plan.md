# Agentic Prompt & Runtime Testing with LangGraph (Bedrock)

This file contains an execution-ready task plan intended for use with Claude Code.

---

## Objective
Create a GitHub repository that:
- Hosts LangGraph-based agents
- Treats system prompts as versioned code
- Tests agents at runtime
- Runs a minimal agent execution inside CI using Docker
- Uses AWS Bedrock (Claude models)
- Prevents behavioral drift via automated tests
- **Generates test reports in GitHub Actions with passing and failing test examples**

---

## Global Constraints
- Runtime framework: LangGraph
- Model provider: AWS Bedrock (Claude models - e.g., claude-3-sonnet, claude-3-haiku)
- CI provider: GitHub Actions
- Runtime execution in CI: Docker
- No real infra side-effects (tools must be stubbed)
- Prompts must be editable without touching code
- **GitHub repository: gonzape27/qa-agentic-poc**
- **Local testing must be fully supported (without Docker)**

---

## TASK 1 — Create GitHub Repository Skeleton
Create a new GitHub repository under `gonzape27` with Python 3.11, dependency management, and base folders.

Expected structure:
```
/agents
/runtime
/tests
/docker
/.github/workflows
```

Acceptance:
- Repo builds locally
- Clean baseline commit
- Repository created at github.com/gonzape27/qa-agentic-poc

---

## TASK 2 — Define Agent Folder Structure
Each agent must contain:
- system.md (system prompt)
- schema.json (strict output schema)

Example:
```
/agents/planner
/agents/executor
```

Acceptance:
- Clear responsibility per agent
- Schemas validated automatically

---

## TASK 3 — Implement LangGraph Agent Runtime
Create runtime/agent_runner.py that:
- Loads system prompts
- Executes LangGraph nodes
- Validates output schemas
- Detects refusals

Expose:
```python
run_agent(agent_name, input_payload, tools, model_config)
```

---

## TASK 4 — Bedrock Model Integration
Create runtime/bedrock_client.py:
- Invoke Claude models via Bedrock (claude-3-sonnet or claude-3-haiku)
- Credentials via env vars
- Deterministic test mode

Env vars:
```
AWS_REGION
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
BEDROCK_MODEL_ID
```

---

## TASK 5 — Tool Registry & Stubbing
Create runtime/tool_registry.py:
- Define tools
- Provide fake implementations
- Log tool usage
- Prevent real side effects

---

## TASK 6 — LangGraph Agent Definition
Define one graph per agent:
- Planner: single node
- Executor: tool-using node

Acceptance:
- Deterministic execution
- Testable in isolation

---

## TASK 7 — Runtime Agent Tests
Use pytest to test:
- Happy path (MUST PASS)
- Ambiguous input (MUST PASS)
- Unsafe input / refusal (MUST PASS)
- **Intentional failing test (MUST FAIL) - for report demonstration**

Assertions:
- Schema validity
- Tool usage correctness
- Safety behavior

---

## TASK 8 — Local Development & Testing Setup
Enable full local testing without Docker:

**Requirements:**
- `requirements.txt` or `pyproject.toml` with all dependencies
- Virtual environment setup instructions
- `.env.example` template for required environment variables
- Local pytest execution with same reports as CI
- Mock mode for Bedrock (no AWS credentials needed for basic tests)

**Commands to support:**
```bash
# Setup
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run tests locally
pytest tests/ -v --html=reports/report.html --junitxml=reports/junit.xml

# Run with mock mode (no AWS needed)
MOCK_BEDROCK=true pytest tests/ -v
```

Acceptance:
- Tests run locally without Docker
- Mock mode works without AWS credentials
- Same test reports generated locally as in CI

---

## TASK 9 — Docker Runtime for CI
Create docker/Dockerfile:
- Install deps
- Copy repo
- Run pytest

Acceptance:
- Same behavior locally and in CI

---

## TASK 10 — GitHub Actions CI Pipeline
Create agent-tests.yml:
- Build Docker image
- Run runtime tests
- Inject Bedrock secrets
- **Generate HTML/XML test reports**
- **Upload test reports as artifacts**
- **Display test summary in GitHub Actions**

CI must fail on:
- Schema breaks
- Missing refusals
- Tool misuse

**Test Report Requirements:**
- pytest-html for HTML reports
- JUnit XML for GitHub Actions summary
- Report includes both passing and failing tests
- Reports uploaded as downloadable artifacts

---

## TASK 11 — End-to-End Agent Test
Add a test that:
- Runs planner → executor
- Validates step execution
- Ensures no extra tool calls

---

## TASK 12 — Prompt Regression Strategy
Add golden inputs and validate:
- Output structure
- Tool choice
- Safety flags

---

## TASK 13 — Documentation
Add README.md explaining:
- Agent structure
- Prompt testing
- **Local development setup and testing**
- CI execution
- Docker usage
- **How to view test reports**

---

## TASK 14 — Local Test Verification
Run all tests locally to verify implementation:
- Install dependencies in virtual environment
- Run pytest with all test files
- Verify passing and failing tests work as expected
- Fix any issues discovered
- Generate test reports locally

Acceptance:
- All non-intentional tests pass
- Intentional failures are properly marked as xfail
- HTML and XML reports generated successfully

---

## Success Criteria
- Prompt changes trigger CI
- Agent regressions caught early
- Adding an agent takes < 1 hour
- **Test reports visible in GitHub Actions**
- **Both passing and failing tests demonstrated in reports**
- **Local testing works without Docker or AWS credentials (mock mode)**
- **Same test experience locally and in CI**
- **All tests verified to pass locally before deployment**
