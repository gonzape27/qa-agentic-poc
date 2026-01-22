#!/bin/bash
# Run tests locally with reports

set -e

# Ensure reports directory exists
mkdir -p reports

# Set mock mode
export MOCK_BEDROCK=true

echo "Running tests in mock mode..."
echo ""

# Run pytest with reports
pytest tests/ -v \
    --html=reports/report.html \
    --self-contained-html \
    --junitxml=reports/junit.xml \
    --tb=short \
    "$@"

echo ""
echo "Test reports generated:"
echo "  - HTML Report: reports/report.html"
echo "  - JUnit XML: reports/junit.xml"
