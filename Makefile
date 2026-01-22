# Makefile for local development and testing

.PHONY: help install install-dev test test-mock test-real test-html test-ci coverage coverage-html coverage-check cover-agent cover-agent-all lint clean setup setup-hooks

# Load .env file if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Coverage threshold (90%)
COVERAGE_THRESHOLD ?= 90

help:
	@echo "Available commands:"
	@echo "  make install        - Install production dependencies"
	@echo "  make install-dev    - Install all dependencies including dev"
	@echo "  make test           - Run tests (uses .env settings)"
	@echo "  make test-mock      - Run tests in mock mode (no AWS needed)"
	@echo "  make test-real      - Run tests with real AWS Bedrock"
	@echo "  make test-html      - Run tests and generate HTML report"
	@echo "  make test-ci        - Run tests like CI (with reports)"
	@echo "  make coverage       - Run tests with coverage report"
	@echo "  make coverage-html  - Generate HTML coverage report"
	@echo "  make coverage-check - Check coverage meets threshold (${COVERAGE_THRESHOLD}%)"
	@echo "  make cover-agent    - Generate tests for a specific file (FILE=path/to/file.py)"
	@echo "  make cover-agent-all- Generate tests for all low-coverage files"
	@echo "  make lint           - Run linting checks"
	@echo "  make clean          - Clean up generated files"
	@echo "  make setup          - Full setup (venv + install + hooks)"
	@echo "  make setup-hooks    - Install git pre-push hook"

# Setup virtual environment and install dependencies
setup: setup-hooks
	python -m venv venv
	@echo "Virtual environment created."
	@echo "Activate it with: source venv/bin/activate (Linux/Mac)"
	@echo "                  venv\\Scripts\\activate (Windows)"
	@echo "Then run: make install-dev"

# Setup git hooks
setup-hooks:
	@echo "Setting up git hooks..."
	git config core.hooksPath .githooks
	@echo "✅ Git hooks installed. Pre-push will check coverage >= ${COVERAGE_THRESHOLD}%"

# Install production dependencies
install:
	pip install -r requirements.txt

# Install all dependencies including dev
install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-html pytest-asyncio pytest-cov coverage

# Run tests (uses MOCK_BEDROCK from .env, defaults to mock if not set)
test:
	pytest tests/ -v

# Run tests in mock mode (no AWS credentials needed)
test-mock:
	MOCK_BEDROCK=true pytest tests/ -v --tb=short

# Run tests with real AWS Bedrock (requires credentials in .env)
test-real:
	MOCK_BEDROCK=false pytest tests/ -v --tb=short

# Run tests with HTML report (uses .env settings)
test-html:
	mkdir -p reports
	pytest tests/ -v \
		--html=reports/report.html \
		--self-contained-html \
		--junitxml=reports/junit.xml

# Run tests like CI would (with all reports, uses .env settings)
test-ci:
	mkdir -p reports
	pytest tests/ -v \
		--html=reports/report.html \
		--self-contained-html \
		--junitxml=reports/junit.xml \
		--tb=short \
		|| true
	@echo ""
	@echo "Test reports generated in reports/"
	@echo "  - HTML Report: reports/report.html"
	@echo "  - JUnit XML: reports/junit.xml"
	@echo ""
	@echo "Mode: $${MOCK_BEDROCK:-not set (defaults to mock)}"

# Run tests with coverage report
coverage:
	MOCK_BEDROCK=true pytest tests/ \
		--cov=runtime \
		--cov=agents \
		--cov-report=term-missing

# Generate HTML coverage report
coverage-html:
	mkdir -p reports/coverage
	MOCK_BEDROCK=true pytest tests/ \
		--cov=runtime \
		--cov=agents \
		--cov-report=html:reports/coverage \
		--cov-report=term-missing
	@echo ""
	@echo "Coverage report: reports/coverage/index.html"

# Check coverage meets threshold (used by pre-push hook)
coverage-check:
	@echo "Checking coverage threshold: ${COVERAGE_THRESHOLD}%"
	MOCK_BEDROCK=true pytest tests/ \
		--cov=runtime \
		--cov=agents \
		--cov-report=term-missing \
		--cov-fail-under=${COVERAGE_THRESHOLD} \
		-q --tb=no

# Run linting (if tools are installed)
lint:
	@which ruff > /dev/null && ruff check . || echo "ruff not installed, skipping"
	@which mypy > /dev/null && mypy runtime/ agents/ || echo "mypy not installed, skipping"

# Clean up generated files
clean:
	rm -rf reports/*.html reports/*.xml reports/coverage
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache */.pytest_cache
	rm -rf *.egg-info
	rm -rf .coverage htmlcov coverage.xml
	rm -rf venv

# ============================================================================
# Cover-Agent: AI-powered test generation
# ============================================================================

# Generate tests for a specific file
# Usage: make cover-agent FILE=runtime/bedrock_client.py TEST=tests/test_bedrock_client.py
cover-agent:
ifndef FILE
	@echo "Usage: make cover-agent FILE=<source_file> [TEST=<test_file>]"
	@echo "Example: make cover-agent FILE=runtime/bedrock_client.py TEST=tests/test_bedrock_client.py"
	@exit 1
endif
	@echo "🤖 Running Cover-Agent on $(FILE)..."
	cover-agent \
		--source-file $(FILE) \
		--test-file $(or $(TEST),tests/test_$(notdir $(basename $(FILE))).py) \
		--coverage-type cobertura \
		--desired-coverage $(COVERAGE_THRESHOLD) \
		--max-iterations 5

# Generate tests for all files below coverage threshold
cover-agent-all:
	@echo "🤖 Running Cover-Agent on low-coverage files..."
	@echo ""
	@echo "Targeting: runtime/bedrock_client.py (74% coverage)"
	-cover-agent \
		--source-file runtime/bedrock_client.py \
		--test-file tests/test_bedrock_client.py \
		--coverage-type cobertura \
		--desired-coverage $(COVERAGE_THRESHOLD) \
		--max-iterations 3
	@echo ""
	@echo "Targeting: runtime/agent_runner.py (98% coverage)"
	-cover-agent \
		--source-file runtime/agent_runner.py \
		--test-file tests/test_agent_runner.py \
		--coverage-type cobertura \
		--desired-coverage $(COVERAGE_THRESHOLD) \
		--max-iterations 3
	@echo ""
	@echo "✅ Cover-Agent complete. Run 'make coverage' to verify."
