# Tests

This directory contains tests for the VeriFact application.

## Testing Strategy

The testing approach for VeriFact follows these principles:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **Agent Tests**: Test the behavior of AI agents with mocked responses
4. **End-to-End Tests**: Test the complete pipeline from input to output

## Test Organization

- `test_claim_detector.py`: Tests for the ClaimDetector agent
- `test_evidence_hunter.py`: Tests for the EvidenceHunter agent
- `test_verdict_writer.py`: Tests for the VerdictWriter agent
- `test_api.py`: Tests for the API endpoints
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

1. Create a file named `test_*.py` for the component you're testing
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
