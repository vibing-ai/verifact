# VeriFact Tests

This directory contains tests for the VeriFact project.

## Test Structure

- `fixtures/`: Test fixtures with sample data
- `integration/`: Integration tests for the full pipeline
- `unit/`: Unit tests for individual components
- `conftest.py`: Pytest configuration
- `test_*.py`: Test files

## Running Tests

### Running All Tests

```bash
pytest
```

### Running Unit Tests Only

```bash
pytest src/tests/test_*.py
```

### Running Integration Tests Only

```bash
pytest src/tests/integration/
```

### Running End-to-End Tests

End-to-end tests make real API calls and require API keys to be set in your environment.

```bash
# Run only end-to-end tests
pytest -m e2e

# Run all tests except end-to-end tests
pytest -m "not e2e"
```

### Running Tests with Coverage

To run tests with coverage reporting and ensure at least 80% coverage:

```bash
# Run the coverage script
./run_tests_with_coverage.sh

# Or manually with pytest
pytest --cov=src --cov-report=term --cov-report=html
```

The coverage report will be generated in the `coverage_html_report/` directory. Open `coverage_html_report/index.html` in a browser to view the detailed report.

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation. They use mocks to avoid external dependencies.

### Integration Tests

Integration tests verify that different components work together correctly. They still use mocks for external services but test the interactions between internal components.

### End-to-End Tests

End-to-end tests verify the entire system works correctly with real external services. These tests make actual API calls and require API keys to be set.

## Test Fixtures

The `fixtures/` directory contains sample data for testing:

- `claims.py`: Sample factual claims
- `evidence.py`: Sample evidence for claims
- `verdicts.py`: Sample verdicts for claims

See the [fixtures README](fixtures/README.md) for more details.

## Writing New Tests

### Unit Tests

Place unit tests in the root of the `tests/` directory with filenames starting with `test_`.

```python
# src/tests/test_new_component.py
import pytest
from src.new_component import NewComponent

def test_new_component_functionality():
    component = NewComponent()
    result = component.do_something()
    assert result == expected_result
```

### Integration Tests

Place integration tests in the `integration/` directory with filenames starting with `test_`.

```python
# src/tests/integration/test_new_integration.py
import pytest
from src.component_a import ComponentA
from src.component_b import ComponentB

@pytest.mark.integration
def test_components_work_together():
    component_a = ComponentA()
    component_b = ComponentB(component_a)
    result = component_b.process_with_a("input")
    assert result == expected_result
```

### End-to-End Tests

Place end-to-end tests in the `integration/` directory with filenames starting with `test_` and mark them with `@pytest.mark.e2e`.

```python
# src/tests/integration/test_new_e2e.py
import pytest
from src.main import Application

@pytest.mark.e2e
def test_full_application():
    app = Application()
    result = app.process_real_data()
    assert result.status == "success"
```
