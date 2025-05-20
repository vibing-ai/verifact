# VeriFact Test Suite

This directory contains tests for the VeriFact factchecking platform.

## Test Structure

The tests are organized into the following directories:

```
src/tests/
├── __init__.py                  (Import all tests for discovery)
├── conftest.py                  (Global fixtures)
├── README.md                    (This file)
├── agents/                      (Agent-specific tests)
│   ├── __init__.py
│   ├── conftest.py              (Agent-specific fixtures)
│   ├── test_agent_detector.py
│   ├── test_claim_detector.py
│   ├── test_evidence_hunter.py
│   └── test_verdict_writer.py
├── api/                         (API tests)
│   ├── __init__.py
│   ├── conftest.py              (API-specific fixtures)
│   └── test_api.py
├── utils/                       (Utility tests)
│   ├── __init__.py
│   ├── conftest.py              (Utility-specific fixtures)
│   ├── test_db_utils.py
│   ├── test_model_config.py
│   └── test_search_tools.py
├── models/                      (Model-specific tests)
│   ├── __init__.py
│   └── conftest.py
├── integration/                 (Integration tests)
│   ├── __init__.py
│   ├── conftest.py              (Integration-specific fixtures)
│   ├── test_db_integration.py
│   ├── test_pipeline_integration.py
│   └── test_factcheck_pipeline.py
├── performance/                 (Performance tests)
│   ├── __init__.py
│   ├── conftest.py              (Performance-specific fixtures)
│   └── test_benchmark_pipeline.py
└── system/                      (System tests)
    ├── __init__.py
    ├── conftest.py              (System-specific fixtures)
    └── test_verifact.py
```

## Running Tests

### Running All Tests

To run all tests:

```bash
pytest
```

### Running Tests in a Specific Directory

To run tests in a specific directory:

```bash
# Run all agent tests
pytest src/tests/agents/

# Run all API tests
pytest src/tests/api/

# Run all utility tests
pytest src/tests/utils/

# Run all integration tests
pytest src/tests/integration/
```

### Running Specific Test Files

To run a specific test file:

```bash
# Run claim detector tests
pytest src/tests/agents/test_claim_detector.py

# Run database utility tests
pytest src/tests/utils/test_db_utils.py
```

### Running Integration Tests

Integration tests that make external API calls are skipped by default. To run them:

```bash
pytest --run-integration
```

### Specifying a Model for Tests

For tests that interact with LLMs, you can specify which model to use:

```bash
pytest --model=gpt-4-turbo
```

### Running Coverage Reports

To run tests with coverage reports:

```bash
pytest --cov=src --cov-report=term --cov-report=html
```

Coverage reports will be generated in the `reports/coverage_html` directory.

## Test Fixtures

Test fixtures are organized in `conftest.py` files at different levels:

- `src/tests/conftest.py`: Global fixtures used across multiple test domains
- Domain-specific fixtures in each subdirectory's `conftest.py`

## Marking Tests

You can use the following markers to categorize tests:

```python
@pytest.mark.unit
def test_something():
    # Unit test
    pass

@pytest.mark.integration
def test_integration():
    # Integration test
    pass

@pytest.mark.slow
def test_performance():
    # Test that takes a long time to run
    pass
```

To run only tests with a specific marker:

```bash
pytest -m unit
pytest -m integration
pytest -m slow
```

## Writing New Tests

When writing new tests:

1. Place the test in the appropriate subdirectory
2. Use fixtures from the most specific conftest.py file
3. Follow the existing naming conventions
4. Import application code using absolute imports (e.g., `from src.agents.claim_detector import ...`)
5. Add appropriate markers to categorize the test

## Testing Strategy

The testing approach for VeriFact follows these principles:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **Agent Tests**: Test the behavior of AI agents with mocked responses
4. **End-to-End Tests**: Test the complete pipeline from input to output
5. **Benchmark Tests**: Test performance and throughput of the system
6. **Database Tests**: Test database interactions

## Test Organization

All tests for VeriFact are contained within this directory:

- **Agent Tests**:

  - `test_claim_detector.py`: Tests for the ClaimDetector agent
  - `test_evidence_hunter.py`: Tests for the EvidenceHunter agent
  - `test_verdict_writer.py`: Tests for the VerdictWriter agent

- **Pipeline Tests**:

  - `test_factcheck_pipeline.py`: Tests for the factchecking pipeline
  - `test_pipeline_integration.py`: Integration tests for pipeline components

- **API Tests**:

  - `test_api.py`: Tests for the API endpoints

- **Benchmark Tests**:

  - `test_benchmark_pipeline.py`: Performance benchmarks for the system

- **Database Tests**:

  - `test_db_integration.py`: Tests for database integration
  - `test_db_utils.py`: Tests for database utilities

- **Utility Tests**:

  - `test_search_tools.py`: Tests for search tools
  - `test_model_config.py`: Tests for model configuration

- **Configuration**:
  - `conftest.py`: Pytest fixtures and configuration

## Running Tests

Run all tests:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=src
```

Run specific test files:

```bash
pytest src/tests/test_claim_detector.py
```

Run tests with specific markers:

```bash
pytest -m "unit"  # Run unit tests
pytest -m "integration"  # Run integration tests
pytest -m "slow"  # Run slow tests
```

## Adding New Tests

When adding new tests:

1. Create a file named `test_*.py` in this directory for the component you're testing
2. Use descriptive test names that explain what functionality is being tested
3. Use pytest fixtures for common test setups
4. Mock external dependencies (e.g., API calls, LLM responses)
5. Add appropriate markers to categorize tests
6. Aim for high test coverage of critical components

## Testing AI Agents

When testing AI agents:

1. Mock the LLM responses to ensure deterministic test results
2. Test both success and failure paths
3. Test with a variety of input types
4. Verify the agent extracts the correct information
5. Check that the agent handles errors gracefully

## Continuous Integration

Tests are automatically run on GitHub Actions when:

- Pull requests are opened or updated
- Code is pushed to the main branch

The CI pipeline checks:

- Test success/failure
- Code coverage
- Linting and formatting
- Type checking
