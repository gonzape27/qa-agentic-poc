# PowerShell script to run tests locally with reports

# Ensure reports directory exists
if (-not (Test-Path "reports")) {
    New-Item -ItemType Directory -Path "reports" | Out-Null
}

# Set mock mode
$env:MOCK_BEDROCK = "true"

Write-Host "Running tests in mock mode..."
Write-Host ""

# Run pytest with reports
pytest tests/ -v `
    --html=reports/report.html `
    --self-contained-html `
    --junitxml=reports/junit.xml `
    --tb=short `
    $args

Write-Host ""
Write-Host "Test reports generated:"
Write-Host "  - HTML Report: reports/report.html"
Write-Host "  - JUnit XML: reports/junit.xml"
