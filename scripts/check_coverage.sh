#!/bin/bash
# Check code coverage before allowing commit/push
# Returns exit code 1 if coverage is below threshold

set -e

THRESHOLD=${COVERAGE_THRESHOLD:-90}
COVERAGE_DIR="runtime agents"

echo "🔍 Running coverage check (threshold: ${THRESHOLD}%)..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || true
fi

# Run tests with coverage in mock mode (fast)
MOCK_BEDROCK=true pytest tests/ \
    --cov=runtime \
    --cov=agents \
    --cov-report=term-missing \
    --cov-fail-under=${THRESHOLD} \
    -q \
    --tb=no \
    2>&1

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    echo "✅ Coverage check passed (>= ${THRESHOLD}%)"
    exit 0
else
    echo ""
    echo "❌ Coverage check failed (< ${THRESHOLD}%)"
    echo "Please add more tests to increase coverage before pushing."
    exit 1
fi
