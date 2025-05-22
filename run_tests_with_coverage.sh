#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
fi

# Find Python executable
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Python not found. Please install Python 3."
    exit 1
fi

# Install required packages
$PYTHON -m pip install --user pytest pytest-cov pytest-asyncio python-dotenv pydantic openai openai-agents>=0.0.15

# Run tests with coverage
$PYTHON -m pytest src/tests/ --cov=src --cov-report=term --cov-report=html -v

# Print coverage report
echo "Coverage report generated in coverage_html_report/"
echo "Open coverage_html_report/index.html in a browser to view the report"

# Check if coverage is at least 80%
COVERAGE=$($PYTHON -m coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
if [ -z "$COVERAGE" ]; then
    echo "Could not determine coverage percentage."
    exit 1
elif (( $(echo "$COVERAGE < 80" | bc -l 2>/dev/null) )); then
    echo "Coverage is below 80% (${COVERAGE}%)"
    exit 1
else
    echo "Coverage is at or above 80% (${COVERAGE}%)"
    exit 0
fi
