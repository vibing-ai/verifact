# VeriFact Development Guidelines

This document provides guidelines for developing and contributing to the VeriFact project.

## Getting Started

1. Clone the repository
2. Set up your Python environment (Python 3.10+ recommended)
3. Install dependencies: `pip install -e .`
4. Install pre-commit hooks: `pre-commit install`

## Code Organization

The VeriFact codebase is organized into modules based on functionality:

- `src/verifact_agents/`: Contains the agent implementations
  - `claim_detector/`: Identifies factual claims in text
  - `evidence_hunter/`: Gathers evidence for claims
  - `verdict_writer/`: Generates verdicts based on evidence
- `src/models/`: Contains data model definitions
- `src/utils/`: Shared utility functions
- `src/ui/`: User interface components for Chainlit
- `src/api/`: API endpoints and related code
- `src/pipeline/`: End-to-end fact-checking pipeline

## Code Organization Guidelines

### File Size

- **Maximum file size**: 300 lines of code (excluding comments and blank lines)
- When a file approaches 250 lines, consider refactoring into smaller modules
- If a file must exceed 300 lines, add a comment at the top explaining why

### Module Organization

- Group related functionality in the same directory
- Use `__init__.py` to create a clean public API
- Organize imports: standard library, then third-party, then local
- Maintain backward compatibility when refactoring

### Class and Function Size

- Maximum function size: 50 lines
- Maximum class size: 200 lines
- Extract complex logic into helper functions
- Use composition over inheritance where possible

### Naming Conventions

- Use descriptive names that reflect the purpose
- Use snake_case for functions, methods, and variables
- Use PascalCase for classes and type names
- Use ALL_CAPS for constants

## Testing

- Write unit tests for all new code
- Tests should be in the `src/tests/` directory
- Use pytest for test framework
- Aim for at least 85% code coverage

## Documentation

- Add docstrings to all public functions, classes, and methods
- Use Google-style docstrings
- Keep the documentation up-to-date with code changes

## Code Review Process

1. Create a new branch for your changes
2. Make your changes and commit them
3. Run the tests to ensure they pass
4. Create a pull request
5. Address any feedback from reviewers
6. Once approved, your changes will be merged

## Refactoring Guidelines

When refactoring code, follow these principles:

1. **Single Responsibility Principle**: Each module should do one thing well
2. **Don't Repeat Yourself**: Extract common code into shared functions
3. **Composition over Inheritance**: Use composition to build complex behavior
4. **Backward Compatibility**: Maintain existing APIs to avoid breaking changes

### Steps for Refactoring Large Files

1. Identify logical component boundaries
2. Create new files for each component
3. Move code to new files
4. Update imports
5. Update the original file to delegate to the new components
6. Run tests to ensure no regressions

## Commit Message Guidelines

- Use the imperative mood ("Add feature" not "Added feature")
- First line should be a summary (50 chars or less)
- Provide details in the body if necessary
- Reference issue numbers if applicable

## Versioning

We use semantic versioning:

- MAJOR.MINOR.PATCH
- MAJOR for incompatible API changes
- MINOR for new functionality in a backward-compatible manner
- PATCH for backward-compatible bug fixes

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

- **Line Length**: Maximum 100 characters (following Ruff's default)
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

We use [Ruff](https://docs.astral.sh/ruff/) for automatic code linting and formatting:

```bash
# Lint code with Ruff
ruff check src tests

# Format code with Ruff
ruff format src tests
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

## Database Connection Pooling

VeriFact uses connection pooling for efficient database access.

### Configuration

Configure the connection pool using these environment variables:

| Variable              | Description                                     | Default |
| --------------------- | ----------------------------------------------- | ------- |
| DB_POOL_MIN_SIZE      | Minimum number of connections to maintain       | 2       |
| DB_POOL_MAX_SIZE      | Maximum number of connections allowed           | 10      |
| DB_POOL_MAX_IDLE_TIME | Maximum time (seconds) a connection can be idle | 300     |
| DB_COMMAND_TIMEOUT    | Command timeout in seconds                      | 60.0    |

### Usage

Use the context manager to get a connection from the pool:

```python
from src.utils.db.pool import get_db_connection

async def get_user(user_id: str):
    async with get_db_connection() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )
```

### Best Practices

1. Always use the context manager to ensure connections are returned to the pool
2. Keep transactions as short as possible
3. Use connection timeout values to prevent hanging connections
4. Monitor connection pool metrics for potential issues
5. Properly size the pool based on expected concurrency

## OpenRouter Model Usage Guidelines

### Model Selection

When working with OpenRouter free tier models, consider the following:

- Choose models based on their specific strengths:

  - `meta-llama/llama-3.3-8b-instruct:free`: Good general purpose model
  - `qwen/qwen3-8b:free`: Best for structured JSON output and entity extraction
  - `google/gemma-3-27b-it:free`: Optimized for RAG applications with 128k context
  - `deepseek/deepseek-chat:free`: Best reasoning capabilities for evidence synthesis

- Always provide fallback options in your agent configurations to handle cases where a specific model is unavailable or has long queue times

### Optimizing for Free Tier

- Set appropriate temperature (usually 0.1-0.3) for more consistent and deterministic outputs
- Keep prompts concise and clear to minimize token usage
- Use streaming for better user experience while waiting for responses
- Implement caching for repeated or similar requests
- Set reasonable timeouts (120s recommended) as free tier models may have longer queue times

### Testing with Models

- Mock model responses in unit tests to avoid unnecessary API calls
- Use recorded responses for integration tests
- Create a dedicated test OpenRouter API key with separate rate limits
- Include fallback behavior testing to ensure your application gracefully handles model unavailability

### Monitoring Usage

- Implement logging to track token usage across different models
- Monitor response times to identify potential bottlenecks
- Set up alerts for API rate limit approaches
- Have a strategy for handling model unavailability (fallbacks, retries with backoff)
