# Makefile for local development and testing

.PHONY: help install install-dev test test-mock test-real test-html test-ci lint clean setup

# Load .env file if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install all dependencies including dev"
	@echo "  make test         - Run tests (uses .env settings)"
	@echo "  make test-mock    - Run tests in mock mode (no AWS needed)"
	@echo "  make test-real    - Run tests with real AWS Bedrock"
	@echo "  make test-html    - Run tests and generate HTML report"
	@echo "  make test-ci      - Run tests like CI (with reports)"
	@echo "  make lint         - Run linting checks"
	@echo "  make clean        - Clean up generated files"
	@echo "  make setup        - Full setup (venv + install)"

# Setup virtual environment and install dependencies
setup:
	python -m venv venv
	@echo "Virtual environment created."
	@echo "Activate it with: source venv/bin/activate (Linux/Mac)"
	@echo "                  venv\\Scripts\\activate (Windows)"
	@echo "Then run: make install-dev"

# Install production dependencies
install:
	pip install -r requirements.txt

# Install all dependencies including dev
install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-html pytest-asyncio pytest-cov

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

# Run linting (if tools are installed)
lint:
	@which ruff > /dev/null && ruff check . || echo "ruff not installed, skipping"
	@which mypy > /dev/null && mypy runtime/ agents/ || echo "mypy not installed, skipping"

# Clean up generated files
clean:
	rm -rf reports/*.html reports/*.xml
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache */.pytest_cache
	rm -rf *.egg-info
	rm -rf .coverage htmlcov
	rm -rf venv
