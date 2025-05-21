# Contributing to VeriFact

First off, thank you for considering contributing to VeriFact! It's people like you that make this open-source project possible. This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Contribution Workflow](#contribution-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Communication](#communication)

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Please report unacceptable behavior by opening an issue in the repository.

## Ways to Contribute

There are many ways to contribute to VeriFact:

- **Code contributions**: Implement new features or fix bugs
- **Documentation**: Improve or expand README, tutorials, or code comments
- **Testing**: Write tests, find bugs, or verify fixes
- **Issue triage**: Help identify and categorize issues
- **Design**: Improve UI/UX, create logos or other visual assets
- **Ideas and planning**: Suggest features or improvements

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip or uv for package management
- OpenRouter API key for model access (register at [openrouter.ai](https://openrouter.ai))
- Git for version control
- Docker & Docker Compose (optional, for containerized development)

### Setting up the development environment

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```
   git clone https://github.com/yourusername/verifact.git
   cd verifact
   ```
3. Set up the upstream remote:
   ```
   git remote add upstream https://github.com/vibing-ai/verifact.git
   ```
4. Create a virtual environment and install dependencies:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"   # Installs the package in development mode with dev dependencies
   ```

5. Copy the environment template and configure it with your API keys:

   ```
   cp configs/env.template .env
   ```

   At minimum, add your OpenRouter API key to the `.env` file:

   ```
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

   Note: VeriFact uses pyproject.toml for dependency management. All dependencies should be added to this file rather than creating separate requirements.txt files.

## Contribution Workflow

1. **Find or create an issue**: All contributions should be tied to an issue. Look for issues labeled "good first issue" or "help wanted" to get started.

2. **Claim an issue**: Comment on the issue to let others know you're working on it.

3. **Create a branch**: Create a branch for your work based on the `main` branch:

   ```
   git checkout -b feature/your-feature-name
   ```

   Use prefixes like `feature/`, `bugfix/`, or `docs/` to categorize your branch.

4. **Make changes**: Implement your changes, adhering to the [coding standards](#coding-standards).

5. **Write tests**: Add or update tests to cover your changes.

6. **Commit changes**: Use clear and meaningful commit messages:

   ```
   git commit -m "Add feature: brief description of what you did"
   ```

7. **Pull latest changes**: Before submitting, pull any changes from upstream:

   ```
   git pull upstream main
   ```

   Resolve any conflicts that arise.

8. **Push your branch**: Push your changes to your fork:

   ```
   git push origin feature/your-feature-name
   ```

9. **Create a pull request**: Open a PR against the `main` branch of the original repository. Follow the PR template.

## Coding Standards

- Follow PEP 8 style guidelines for Python code
- Use meaningful variable and function names
- Include docstrings for all functions, classes, and modules
- Keep functions focused on a single responsibility
- Use type hints to improve code readability and tooling support
- Use `ruff` for linting and formatting your code before committing
- Use `mypy` for static type checking where applicable

## Testing Guidelines

- Write unit tests for all new functionality
- Tests should be located in the `src/tests/` directory
- Aim for at least 80% code coverage
- Set up at minimum an OpenRouter API key in your `.env` file for tests that require model access
- Use mocks for external services (web search, etc.) when appropriate
- Run the full test suite before submitting a PR:
  ```
  pytest
  ```

## Issue Reporting

When creating a new issue:

1. Check if a similar issue already exists
2. Use the appropriate issue template
3. Provide a clear, concise description of the problem
4. Include steps to reproduce, expected behavior, and actual behavior
5. Add relevant information like OS, Python version, and screenshots if applicable

## Running the Application

### Using Docker (Recommended for Full Stack)

```bash
docker-compose up
```

This will start all necessary services including the Chainlit UI, FastAPI backend, and database.

### Running Components Separately (Local Development)

For the Chainlit UI:

```bash
chainlit run app.py
```

For the API server:

```bash
uvicorn src.main:app --reload
```

## Communication

- **GitHub Issues**: Use for bug reports, feature requests, and substantial discussions
- **Pull Requests**: Use for code review and related discussions
- **Project boards**: Track progress of feature development
- **GitHub Discussions**: For general questions and community discussions

---

Thank you for contributing to VeriFact! Your efforts help make AI factchecking more accessible and reliable for everyone.
