# VeriFact Development Guidelines

This document provides guidelines and best practices for development on the VeriFact project.

## Table of Contents

- [Code Style](#code-style)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)
- [Pull Request Process](#pull-request-process)
- [Performance Considerations](#performance-considerations)
- [Security Guidelines](#security-guidelines)

## Code Style

### Python Style Guide

VeriFact follows [PEP 8](https://www.python.org/dev/peps/pep-0008/) for code style with the following specifics:

- **Line Length**: Maximum 88 characters (following Black's default)
- **Indentation**: 4 spaces (no tabs)
- **Naming Conventions**:
  - Classes: `CamelCase`
  - Functions and variables: `snake_case`
  - Constants: `UPPER_CASE_WITH_UNDERSCORES`
  - Private methods/variables: `_prefixed_with_underscore`
- **Imports**: Group and order imports as follows:
  1. Standard library imports
  2. Third-party library imports
  3. Local application imports
  
  Each group should be separated by a blank line.

### Automatic Formatting

We use [Black](https://black.readthedocs.io/) for automatic code formatting and [isort](https://pycqa.github.io/isort/) for import sorting:

```bash
# Format code with Black
black src tests

# Sort imports
isort src tests
```

### Type Annotations

Use type hints for function arguments and return values according to [PEP 484](https://www.python.org/dev/peps/pep-0484/):

```python
def process_claim(claim: str, confidence_threshold: float = 0.7) -> List[Evidence]:
    """Process a claim and return supporting evidence."""
    # ...
```

## Testing Requirements

### Test Coverage

- All new code must include tests
- Aim for minimum 80% code coverage for each module
- Unit tests should be isolated and not depend on external services
- Integration tests should verify the interaction between components

### Running Tests

We use pytest for testing:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src

# Run a specific test file
pytest src/tests/test_claim_detector.py

# Run a specific test
pytest src/tests/test_claim_detector.py::TestClaimDetector::test_detect_simple_claim
```

### Test Types

1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test interactions between components
3. **Functional Tests**: Test complete features from a user perspective
4. **Performance Tests**: Ensure the system meets performance requirements

### Mocking

- Use `unittest.mock` or `pytest-mock` for mocking dependencies
- Avoid mocking the system under test
- Create fixtures for commonly used test objects

## Documentation Standards

### Code Documentation

- All modules, classes, and functions should have docstrings
- Follow [Google style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- Document parameters, return values, raised exceptions, and examples

Example:

```python
def detect_claims(text: str, min_confidence: float = 0.5) -> List[Claim]:
    """
    Detect factual claims in the provided text.
    
    Args:
        text: Input text to analyze for claims
        min_confidence: Minimum confidence threshold (0-1) for claim detection
        
    Returns:
        List of Claim objects containing detected claims
        
    Raises:
        ValueError: If text is empty or min_confidence is outside valid range
        
    Example:
        >>> detect_claims("The Earth is round.")
        [Claim(text="The Earth is round.", confidence=0.95)]
    """
```

### API Documentation

- Use OpenAPI/Swagger for API documentation
- Document all endpoints, parameters, request/response formats
- Include example requests and responses

## Pull Request Process

1. Ensure all tests pass locally before submitting PR
2. Update documentation if needed
3. Add relevant tests
4. Follow the PR template
5. Link to related issues
6. Wait for CI checks to pass
7. Address review comments

## Performance Considerations

- Consider the computational complexity of algorithms
- Optimize resource-intensive operations
- Use appropriate data structures
- Implement caching where beneficial
- Use async operations for I/O-bound tasks
- Profile code to identify bottlenecks

## Security Guidelines

- Never commit sensitive credentials
- Use environment variables for configuration
- Validate all user inputs
- Use parameterized queries to prevent SQL injection
- Implement proper error handling without leaking sensitive information
- Follow OWASP security best practices 