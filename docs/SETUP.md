# VeriFact Development Environment Setup

This guide will help you set up your development environment for contributing to VeriFact.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**: VeriFact requires Python 3.10 or newer
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
conda create -n verifact python=3.10
conda activate verifact
```

## Step 3: Install Dependencies

Install the package in development mode along with all dependencies:

```bash
# Install dependencies
pip install -e .

# Or with development dependencies (recommended for contributors)
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
cp .env-example .env
```

Edit the `.env` file and add at minimum:

```
# OpenRouter API Key for model access (Required)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Supabase Configuration (Optional)
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
```

### Environment Variables Explained

Here's a detailed explanation of all environment variables from the template:

#### OpenRouter Configuration (Required)

- `OPENROUTER_API_KEY`: Your API key from OpenRouter (required)
- `OPENROUTER_SITE_URL`: The URL of your site (e.g., https://verifact.vibing.im)
- `OPENROUTER_SITE_NAME`: The name of your site (e.g., VeriFact)

#### Model Configuration (OpenRouter Free Models)

- `DEFAULT_MODEL`: Default model for general processing (default: meta-llama/llama-3.3-8b-instruct:free)
  - Alternative options include qwen/qwen3-8b:free (better for multilingual) or microsoft/phi-4-reasoning:free (lightweight)
- `CLAIM_DETECTOR_MODEL`: Model for claim detection (default: qwen/qwen3-8b:free)
  - Best for structured JSON output and entity extraction
  - Alternative options include meta-llama/llama-3.3-8b-instruct:free or microsoft/phi-4-reasoning:free
- `EVIDENCE_HUNTER_MODEL`: Model for evidence gathering (default: google/gemma-3-27b-it:free)
  - Optimized for RAG applications with 128k context window
  - Alternative options include deepseek/deepseek-chat:free (stronger reasoning) or mistralai/mixtral-8x22b:free
- `VERDICT_WRITER_MODEL`: Model for verdict generation (default: deepseek/deepseek-chat:free)
  - Best reasoning capabilities for evidence synthesis
  - Alternative options include nousresearch/deephermes-3-mistral-24b-preview:free or google/gemma-3-27b-it:free

#### Model Parameters (Optional)

- `MODEL_TEMPERATURE`: Controls randomness (0.1-1.0, lower means more deterministic)
- `MODEL_MAX_TOKENS`: Maximum tokens for model responses
- `MODEL_REQUEST_TIMEOUT`: Timeout for model requests in seconds

#### Supabase Configuration (Optional)

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key (public)
- `SUPABASE_SERVICE_KEY`: Your Supabase service role key (keep secure, never expose)
- `SUPABASE_DB_URL`: Direct PostgreSQL connection string

#### Database Configuration (Important Security Considerations)

- `POSTGRES_USER`: Database username (change from default for security)
- `POSTGRES_PASSWORD`: Database password (use a strong, unique password)
- `POSTGRES_DB`: Database name

⚠️ **SECURITY WARNING**: Never use default database credentials in production. Always change the database username and password from defaults. The service is configured to use environment variables defined in your `.env` file.

#### Chainlit Configuration (UI)

- `CHAINLIT_HOST`: Host to bind Chainlit server (0.0.0.0 for Docker)
- `CHAINLIT_PORT`: Port for Chainlit server (default: 8501)
- `CHAINLIT_AUTH_SECRET`: Secret for Chainlit authentication
- `CHAINLIT_AUTH_ENABLED`: Enable/disable authentication (true/false)

#### API Configuration

- `API_HOST`: Host to bind API server
- `API_PORT`: Port for API server (default: 8000)

#### Logging Configuration

- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Setting Up OpenRouter

[OpenRouter](https://openrouter.ai/) is a unified API that provides access to multiple AI model providers through a single interface. VeriFact uses OpenRouter to access various free models without requiring separate API keys for each provider.

#### Setting Up Your OpenRouter Account:

1. Create an account at [OpenRouter](https://openrouter.ai/)
2. Generate an API key from your dashboard
3. Add the API key to your `.env` file as `OPENROUTER_API_KEY`
4. Add your site URL and name to properly identify your requests (optional but recommended)

#### OpenRouter Free Tier Information:

- The free tier includes access to selected models with limited usage
- Current free models include Meta Llama 3, Qwen, Gemma, DeepSeek, and more
- Free tier typically has usage limits and potential queue times during high demand
- For production use, consider upgrading to a paid plan for higher rate limits and priority access

#### How VeriFact Uses OpenRouter:

1. Different components of the factchecking pipeline use specialized models:

   - Claim detection uses structured-output optimized models
   - Evidence hunting uses models with large context windows
   - Verdict writing uses models with strong reasoning capabilities

2. Model fallbacks are configured in the `.env` file, so if one model is unavailable, an alternative can be used

3. Rate limiting and error handling are built into the system to handle OpenRouter service limitations

For the most up-to-date list of available models and their capabilities, check the [OpenRouter documentation](https://openrouter.ai/docs).

### Alternative Model Access

If you prefer to use your own API keys for specific providers instead of OpenRouter, you can uncomment and configure the following in your `.env` file:

```
# OPENAI_API_KEY=your_openai_api_key_here         # Uncomment if needed
```

### Setting Up Supabase (Optional)

If you want to use Supabase for database features:

1. Create a project at [Supabase](https://supabase.com/)
2. Get your project URL and both API keys from the project settings:
   - **Anon Key**: Used for public client-side requests (SUPABASE_KEY)
   - **Service Role Key**: Used for secure server-side access (SUPABASE_SERVICE_KEY)
3. Enable the pgvector extension in your Supabase project by running:
   ```sql
   -- Run this in the Supabase SQL editor
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Add the URL and keys to your `.env` file

#### Supabase Security Best Practices

1. **Row Level Security (RLS)**: Always enable and configure RLS policies on your tables

   ```sql
   -- Example RLS policy for user-specific data
   ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

   CREATE POLICY "Users can view their own data" ON your_table
     FOR SELECT USING (auth.uid() = user_id);
   ```

2. **API Key Management**:

   - Never expose your Service Role Key in client-side code
   - Use the Anon Key for public-facing applications
   - Store the Service Role Key securely in environment variables

3. **Database Password Security**:

   - Use a unique, complex password for the database
   - Change default credentials (postgres/postgres) immediately
   - Rotate credentials periodically for enhanced security

4. **Connection Security**:
   - Use SSL/TLS for all database connections
   - Consider using Supabase Edge Functions for sensitive operations

### PGVector Setup for Embeddings

VeriFact uses PGVector for storing and querying vector embeddings:

1. **Embedding Generation**: The system uses the `text-embedding-3-small` model (configurable via `EMBEDDING_MODEL` environment variable) to generate vector embeddings of claims and evidence.

2. **Database Tables**: Vector columns use the pgvector `vector` type:

   ```sql
   CREATE TABLE claims (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     text TEXT NOT NULL,
     embedding vector(1536)  -- Dimension based on embedding model
   );
   ```

3. **Vector Indexes**: For efficient similarity search, create an index:

   ```sql
   -- For HNSW index (faster search, slower inserts)
   CREATE INDEX ON claims USING hnsw (embedding vector_l2_ops);

   -- Or for IVFFlat index (more balanced)
   CREATE INDEX ON claims USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
   ```

4. **Similarity Searches**: Performed using L2 distance, cosine similarity, or inner product
   ```sql
   -- Example: Find similar claims by cosine similarity
   SELECT id, text, 1 - (embedding <=> query_embedding) as similarity
   FROM claims
   ORDER BY embedding <=> query_embedding
   LIMIT 5;
   ```

These vector operations power VeriFact's semantic search capabilities and enable efficient retrieval of related claims and evidence.

## Step 6: Run VeriFact

### Using Docker (Recommended for Full Stack)

The easiest way to run the complete stack:

```bash
docker-compose up
```

This will start:

- The Chainlit web interface at http://localhost:8501
- The FastAPI backend at http://localhost:8000
- A PostgreSQL database with the PGVector extension

For running in the background:

```bash
docker-compose up -d
```

To stop the services:

```bash
docker-compose down
```

### Running Components Separately (Local Development)

#### Chainlit Interface

```bash
chainlit run app.py
```

Access the UI at http://localhost:8501

#### API Server

```bash
uvicorn src.main:app --reload
```

Access the API at http://localhost:8000

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

VeriFact uses the OpenAI Agent SDK with OpenRouter for model access, creating a modular pipeline of specialized agents for factchecking.

### Agent Structure

Each agent follows a similar structure:

1. **Initialization**: Create an Agent instance with instructions and output type
2. **Run Method**: Process input and generate output using the Runner

Example agent implementation:

```python
from openai.agents import Agent, Runner
from openai.agents.tools import WebSearchTool
from src.utils.model_config import get_model_name, get_model_settings

class MyAgent:
    def __init__(self, model_name=None):
        # Get appropriate model name and settings from environment config
        self.model_name = get_model_name(model_name, agent_type="my_agent")
        self.model_settings = get_model_settings()

        # For example, this might resolve to:
        # self.model_name = "meta-llama/llama-3.3-8b-instruct:free"

        # Create the agent with specialized instructions
        self.agent = Agent(
            name="MyAgent",
            instructions="""
            Your task is to process the input data and generate a structured output.
            Follow these specific steps:
            1. Analyze the input carefully
            2. Extract relevant information
            3. Format the results according to the output schema
            """,
            output_type=YourOutputType,  # Structured output schema
            tools=[WebSearchTool()],  # If web search is needed
            model=self.model_name,
            **self.model_settings
        )

    async def process(self, input_data):
        # Run the agent with the input data
        result = await Runner.run(self.agent, input_data)
        return result.output
```

### Example Configuration for Claim Detection

Here's a real-world example using the Claim Detector agent with Qwen model:

```python
from openai.agents import Agent, Runner
from pydantic import BaseModel, Field
from typing import List

# Define structured output schema
class Claim(BaseModel):
    text: str = Field(description="The exact text of the factual claim")
    context: str = Field(description="The surrounding context of the claim")

class ClaimsOutput(BaseModel):
    claims: List[Claim] = Field(description="List of factual claims extracted from text")

class ClaimDetectorAgent:
    def __init__(self, model_name=None):
        # This will resolve to "qwen/qwen3-8b:free" by default
        self.model_name = get_model_name(model_name, agent_type="claim_detector")
        self.model_settings = get_model_settings()

        self.agent = Agent(
            name="ClaimDetector",
            instructions="""
            Identify factual claims in the provided text that can be verified.
            A factual claim is a statement that:
            - Makes an assertion about reality that can be proven true or false
            - Is specific enough to be verified
            - Is not purely subjective or opinion-based

            For each claim, extract the exact text and provide context.
            """,
            output_type=ClaimsOutput,
            model=self.model_name,
            temperature=0.1,  # Lower temperature for more consistent output
            **self.model_settings
        )

    async def detect_claims(self, text):
        result = await Runner.run(self.agent, text)
        return result.output
```

The examples above demonstrate how the system dynamically selects the appropriate model based on the agent type, using environment configuration to determine the correct model for each part of the factchecking pipeline.

## Understanding the Stack

- **OpenAI Agent SDK with OpenRouter**: Provides the framework for creating and running agents with access to multiple model providers
- **OpenRouter**: Gives access to multiple model providers through a single API
- **Chainlit**: Provides the interactive UI with step-by-step visualization
- **Supabase with PGVector**: Used for vector storage and database operations
- **FastAPI**: Serves the API endpoints
- **Docker**: Containerizes the entire stack for easy deployment

## Model Selection and Configuration

VeriFact uses a specialized set of models from OpenRouter's free tier, each selected for specific strengths:

### Default Model (meta-llama/llama-3.3-8b-instruct:free)

- General purpose language model for fallback operations
- Well-balanced between performance and efficiency
- Alternatives include Qwen 3-8b (better for multilingual) and Microsoft Phi-4 (MIT licensed)

### Claim Detector Model (qwen/qwen3-8b:free)

- Optimized for structured JSON output and entity extraction
- Excellent at identifying factual statements in text
- Strong performance in categorizing information by domain

### Evidence Hunter Model (google/gemma-3-27b-it:free)

- 128k context window for processing large amounts of evidence
- Optimized for Retrieval-Augmented Generation (RAG)
- Balances reasoning capabilities with moderate resource requirements

### Verdict Writer Model (deepseek/deepseek-chat:free)

- Superior reasoning for evidence synthesis and analysis
- Strong logical capabilities for verdict determination
- Clear explanation generation with proper attribution

### Embedding Model (text-embedding-3-small)

- Used for generating vector embeddings for semantic search
- Stored in the database using PGVector
- Powers similarity search for related claims and evidence

### Model Configuration

Models are configured in your `.env` file:

```
DEFAULT_MODEL=meta-llama/llama-3.3-8b-instruct:free
CLAIM_DETECTOR_MODEL=qwen/qwen3-8b:free
EVIDENCE_HUNTER_MODEL=google/gemma-3-27b-it:free
VERDICT_WRITER_MODEL=deepseek/deepseek-chat:free
EMBEDDING_MODEL=text-embedding-3-small
```

### Free Tier Considerations

When using the free tier models from OpenRouter:

- Rate limits apply based on OpenRouter's policies
- Queue times may vary, especially during peak usage
- Consider setting appropriate timeouts (120s recommended)
- Implement caching to reduce redundant API calls

For detailed guidelines on working with these models, see the OpenRouter Model Usage Guidelines section in [DEVELOPMENT.md](DEVELOPMENT.md).

## Common Development Tasks

### Running the Application Locally

```bash
# Run the application in development mode
python -m verifact --debug
```

### Adding New Dependencies

If you need to add a new dependency:

1. Add it to `pyproject.toml` (preferred approach)
2. Update your virtual environment:
   ```bash
   pip install -e .  # Or pip install -e ".[dev]" for development dependencies
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

Error: `OPENROUTER_API_KEY is required`

Solution: Ensure you've added your OpenRouter API key to your `.env` file.

#### Model Provider Errors

Error: `Unable to connect to OpenRouter`

Solutions:

- Check your internet connection
- Verify your API key is correct
- Ensure you're not hitting rate limits with OpenRouter

#### Package Import Errors

Error: `ModuleNotFoundError: No module named 'verifact'`

Solution: Ensure you've installed the package in development mode:

```bash
pip install -e ".[dev]"
```

#### Docker Issues

Error: `Cannot connect to the Docker daemon`

Solution: Ensure Docker is running on your system:

```bash
# Check Docker status
sudo systemctl status docker  # Linux
docker --version  # Check installation
```

Error: `Port is already allocated`

Solution: Change the port in docker-compose.yml or stop the service using that port.

#### Database Connection Issues

Error: `Connection refused to PostgreSQL`

Solutions:

- Ensure the database container is running
- Check your SUPABASE_DB_URL is correct
- For Docker, use `verifact-db` as the hostname instead of `localhost`

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

### Quick Start Example

For a quick setup to test the system:

1. Clone the repository and set up your environment:

   ```bash
   git clone https://github.com/vibing-ai/verifact.git
   cd verifact
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

2. Set up minimal environment variables:

   ```bash
   cp .env-example .env
   # Edit .env and add your OpenRouter API key at minimum
   ```

3. Run the Chainlit UI:

   ```bash
   chainlit run app.py
   ```

4. Open http://localhost:8501 in your browser and start fact-checking!

## Getting Help

If you encounter issues not covered in this guide:

1. Check existing issues on GitHub
2. Ask in the project's discussion forum
3. Reach out to project maintainers

## Database Schema and Vector Storage

VeriFact uses a PostgreSQL database with the pgvector extension for storing claims, evidence, and vector embeddings. Here's an overview of the key database components:

### Database Tables

#### Claims Table

Stores factual claims detected from input text:

- `id`: Unique identifier for each claim
- `text`: The exact text of the claim
- `source_text`: The original text containing the claim
- `metadata`: Additional information about the claim (JSON)
- `created_at`: Timestamp when the claim was created
- `embedding`: Vector representation of the claim (pgvector)

#### Evidence Table

Stores evidence gathered for each claim:

- `id`: Unique identifier for each evidence piece
- `claim_id`: Foreign key linking to the claim
- `text`: The evidence text
- `source`: Source URL or reference
- `relevance_score`: How relevant the evidence is to the claim (0-1)
- `reliability_score`: How reliable the source is (0-1)
- `created_at`: Timestamp when the evidence was stored
- `metadata`: Additional information about the evidence (JSON)

#### Verdicts Table

Stores factchecking verdicts:

- `id`: Unique identifier for each verdict
- `claim_id`: Foreign key linking to the claim
- `verdict`: The factchecking verdict (e.g., TRUE, FALSE, PARTIALLY_TRUE)
- `confidence`: Confidence level in the verdict (0-1)
- `explanation`: Detailed explanation of the verdict
- `created_at`: Timestamp when the verdict was created
- `metadata`: Additional information about the verdict (JSON)

### Vector Storage with pgvector

VeriFact uses the pgvector extension to:

1. Store vector embeddings of claims and evidence
2. Perform similarity searches to find related claims and evidence
3. Enable semantic search capabilities for retrieval augmented generation

The system uses the `text-embedding-3-small` model from OpenAI (configurable via `EMBEDDING_MODEL` environment variable) to generate embeddings.

## Search API Integration

VeriFact supports web search capabilities through multiple methods:

### Built-in OpenAI Functions Search

By default, VeriFact uses the search capabilities built into the OpenAI functions framework, which provides:

- Basic web search functionality
- No additional API keys required
- Limited daily search volume

### Serper.dev API Integration (Optional)

For more powerful search capabilities, you can enable Serper.dev integration:

1. Set `USE_SERPER=true` in your `.env` file
2. Add your Serper API key as `SERPER_API_KEY`

Serper.dev advantages:

- Higher search volume limits
- More structured search results
- Additional search verticals (news, images)
- Better international search coverage

To set up Serper.dev:

1. Create an account at [Serper.dev](https://serper.dev)
2. Generate an API key from your dashboard
3. Configure the environment variables in your `.env` file

### Search Configuration Example

```
# Search Configuration
USE_SERPER=true                                  # Set to true to use Serper.dev API
SERPER_API_KEY=your_serper_api_key_here          # Required when USE_SERPER=true
```

When `USE_SERPER=false` or not set, the system falls back to the built-in search capabilities.

---

Happy fact-checking!
