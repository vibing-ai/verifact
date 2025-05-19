# VeriFact Development Environment Setup

This guide will help you set up your development environment for contributing to VeriFact.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9+**: VeriFact requires Python 3.9 or newer
- **Git**: For version control
- **pip** or **uv**: For package management

## Step 1: Clone the Repository

First, fork the repository on GitHub, then clone your fork:

```bash
# Clone your fork
git clone https://github.com/vibing-ai/verifact.git
cd verifact

# Add the original repository as upstream (only if you're using your own fork)
git remote add upstream https://github.com/vibing-ai/verifact.git
```

## Step 2: Set Up a Virtual Environment

We recommend using a virtual environment to isolate dependencies:

### Using venv (Standard Library)

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Using conda (Alternative)

```bash
# Create a conda environment
conda create -n verifact python=3.9
conda activate verifact
```

## Step 3: Install Dependencies

Install the package in development mode along with all dependencies:

```bash
# Install dependencies
pip install -e ".[dev]"
```

This will install:

- Core dependencies from `requirements.txt`
- Development dependencies (testing, linting, documentation tools)

## Step 4: Set Up Pre-commit Hooks (Optional but Recommended)

Pre-commit hooks help ensure code quality before committing:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install
```

## Step 5: Configure Environment Variables

Copy the example environment file and configure it with your API keys:

```bash
cp .env.example .env
```

Edit the `.env` file and add the required API keys:

```
# OpenAI API Key for agent operations
OPENAI_API_KEY=your_openai_api_key

# Web search API key for evidence gathering
SEARCH_API_KEY=your_search_api_key

# Other configuration variables
DEBUG=False
LOG_LEVEL=INFO
```

## Step 6: Verify Your Setup

Run the tests to verify that everything is set up correctly:

```bash
# Run tests
pytest

# Verify code formatting
black --check src tests
flake8 src tests
```

## Step 7: Set Up Your IDE

### Visual Studio Code

If you're using VS Code, install the following extensions:

- Python
- Pylance
- Black Formatter
- flake8
- isort

Create or update `.vscode/settings.json` with:

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.nosetestsEnabled": false,
  "python.testing.pytestArgs": ["src/tests"]
}
```

### PyCharm

If you're using PyCharm:

1. Open the project
2. Go to Settings > Project > Python Interpreter
3. Add a new interpreter using the virtual environment you created
4. Configure Black as the formatter in Settings > Tools > Black
5. Install the "Save Actions" plugin for auto-formatting on save

## Development Workflow

1. Create a branch for your work:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, write tests, and ensure they pass:

   ```bash
   pytest
   ```

3. Format your code:

   ```bash
   black src tests
   isort src tests
   ```

4. Commit your changes with a descriptive message:

   ```bash
   git commit -m "Add feature: brief description of what you did"
   ```

5. Push your branch to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

6. Open a pull request on the GitHub repository

## Common Development Tasks

### Running the Application Locally

```bash
# Run the application in development mode
python -m verifact --debug
```

### Adding New Dependencies

If you need to add a new dependency:

1. Add it to `pyproject.toml` or `requirements.txt`
2. Update your virtual environment:
   ```bash
   pip install -e ".[dev]"
   ```

### Updating from Upstream

Keep your fork up to date with the main repository:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

## Troubleshooting

### Common Issues

#### Missing API Keys

Ensure you've added all required API keys to your `.env` file.

#### Package Import Errors

If you encounter package import errors, ensure you've installed the package in development mode:

```bash
pip install -e ".[dev]"
```

#### Test Failures

If tests are failing, check:

- You have the latest code from upstream
- Your environment variables are set correctly
- You've installed all dependencies

#### Pre-commit Hook Failures

If pre-commit hooks fail, run the checks manually to understand the errors:

```bash
black src tests
isort src tests
flake8 src tests
```

## Getting Help

If you encounter issues not covered in this guide:

1. Check existing issues on GitHub
2. Ask in the project's discussion forum
3. Reach out to project maintainers

---

Happy coding!
