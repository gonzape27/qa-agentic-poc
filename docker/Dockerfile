# Dockerfile for running agent tests in CI

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest pytest-html pytest-asyncio pytest-cov

# Copy the application code
COPY . .

# Create reports directory
RUN mkdir -p reports

# Set environment variables
ENV PYTHONPATH=/app
ENV MOCK_BEDROCK=true
ENV PYTHONUNBUFFERED=1

# Default command: run tests with reports
CMD ["pytest", "tests/", "-v", \
     "--html=reports/report.html", \
     "--self-contained-html", \
     "--junitxml=reports/junit.xml", \
     "--tb=short"]
