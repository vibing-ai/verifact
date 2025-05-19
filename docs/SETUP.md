# VeriFact Development Environment Setup

This guide will help you set up your development environment for contributing to VeriFact.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9+**: VeriFact requires Python 3.9 or newer
- **Git**: For version control
- **pip** or **uv**: For package management
- **Docker & Docker Compose** (optional): For containerized development

## Step 1: Clone the Repository

First, fork the repository on GitHub, then clone your fork:

```bash
# Clone your fork
git clone https://github.com/yourusername/verifact.git
cd verifact

# Add the original repository as upstream
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
pip install -r requirements.txt

# Or with development dependencies
pip install -e ".[dev]"
```

## Step 4: Set Up Pre-commit Hooks (Optional but Recommended)

Pre-commit hooks help ensure code quality before committing:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install
```

## Step 5: Configure Environment Variables

Copy the template environment file and configure it with your API keys:

```bash
cp configs/env.template .env
```

Edit the `.env` file and add at minimum:

```
# OpenRouter API Key for model access (Required)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Supabase Configuration (Optional)
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
```

### Setting Up OpenRouter

1. Create an account at [OpenRouter](https://openrouter.ai/)
2. Generate an API key from your dashboard
3. Add the API key to your `.env` file

### Setting Up Supabase (Optional)

If you want to use Supabase for database features:

1. Create a project at [Supabase](https://supabase.com/)
2. Get your project URL and API key from the project settings
3. Enable the pgvector extension in your Supabase project
4. Add the URL and key to your `.env` file

## Step 6: Run VeriFact

### Using Docker

The easiest way to run the complete stack:

```bash
docker-compose up
```

This will start:

- The Chainlit web interface at http://localhost:8501
- The FastAPI backend at http://localhost:8000
- A PostgreSQL database with the PGVector extension

### Running Components Separately

#### Chainlit Interface

```bash
chainlit run app.py
```

#### API Server

```bash
uvicorn src.main:app --reload
```

#### CLI

```bash
python cli.py --input "Text containing claims to verify"
```

## Step 7: Verify Your Setup

Run the tests to verify that everything is set up correctly:

```bash
# Run tests
pytest

# Verify code formatting
black --check src tests
flake8 src tests
```

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

## Working with Agents

VeriFact uses the OpenAI Agent SDK with OpenRouter for model access.

### Agent Structure

Each agent follows a similar structure:

1. **Initialization**: Create an Agent instance with instructions and output type
2. **Run Method**: Process input and generate output using the Runner

Example:

```python
from openai.agents import Agent, Runner
from openai.agents.tools import WebSearchTool
from src.utils.model_config import get_model_name, get_model_settings

class MyAgent:
    def __init__(self, model_name=None):
        self.model_name = get_model_name(model_name, agent_type="my_agent")
        self.model_settings = get_model_settings()

        self.agent = Agent(
            name="MyAgent",
            instructions="Your instructions here...",
            output_type=YourOutputType,
            tools=[WebSearchTool()],  # If needed
            model=self.model_name,
            **self.model_settings
        )

    async def process(self, input_data):
        result = await Runner.run(self.agent, input_data)
        return result.output
```

### Adding a New Agent

To add a new agent:

1. Create a new directory under `src/agents/your_agent_name/`
2. Create an `__init__.py` file that exports your agent
3. Create an implementation file (e.g., `processor.py`) with your agent class
4. Update the agent pipeline in `app.py` to include your new agent

## Understanding the Stack

- **OpenAI Agent SDK**: Provides the framework for creating and running agents
- **OpenRouter**: Gives access to multiple model providers through a single API
- **Chainlit**: Provides the interactive UI with step-by-step visualization
- **Supabase with PGVector**: Used for vector storage and database operations
- **FastAPI**: Serves the API endpoints
- **Docker**: Containerizes the entire stack for easy deployment

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
