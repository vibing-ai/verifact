# VeriFact: Open-Source AI Factchecking Platform

VeriFact is an open-source AI factchecking platform that leverages a multi-agent architecture to detect factual claims, gather evidence, and generate verdicts with transparent explanations and source citations.

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Features

- **Claim Detection**: Automatically identifies check-worthy factual claims from text
- **Evidence Gathering**: Searches reliable sources to find relevant information about claims
- **Verdict Generation**: Analyzes evidence to determine whether claims are true, false, or need more context
- **Interactive UI**: Explore evidence and see the fact-checking process step-by-step
- **Authentication**: Secure access with user accounts
- **Session Persistence**: Store and access your previous fact-checking sessions
- **Results Export**: Save fact-check results for later use or sharing

## Overview

VeriFact uses a pipeline of specialized AI agents to process and verify factual claims:

1. **ClaimDetector**: Identifies and extracts check-worthy factual claims from text
2. **EvidenceHunter**: Searches for and evaluates supporting/contradicting evidence
3. **VerdictWriter**: Synthesizes evidence to produce verdicts with confidence scores and explanations

Each agent is designed to perform its specialized task efficiently while maintaining transparency in the factchecking process.

## Implementation Status

VeriFact is under active development. Here's the current status of key features:

| Feature                | Status      | Notes                                                  |
| ---------------------- | ----------- | ------------------------------------------------------ |
| ClaimDetector Agent    | Implemented | Uses OpenAI Agent SDK with OpenRouter                  |
| EvidenceHunter Agent   | Implemented | Uses OpenAI Agent SDK with OpenRouter                  |
| VerdictWriter Agent    | Implemented | Uses OpenAI Agent SDK with OpenRouter                  |
| Chainlit UI            | Implemented | Interactive chat interface with step visualization     |
| FastAPI Backend        | Implemented | RESTful API for factchecking                           |
| Supabase Integration   | Implemented | Vector storage, user auth, and session persistence     |
| PGVector Integration   | Implemented | For semantic search and embeddings storage             |
| Docker Deployment      | Implemented | Full containerization with docker-compose              |
| Redis Caching          | Implemented | For model responses and evidence caching               |
| Multi-claim Processing | In Progress | Parallel processing implementation underway            |
| Multilingual Support   | In Progress | Basic support implemented, expanding language coverage |
| Media Analysis         | Planned     | Text-only factchecking currently                       |

## Tech Stack

- **Agent Framework**: OpenAI Agent SDK
- **Internal Agent System**: Renamed from `src.agents` to `src.verifact_agents` to avoid namespace conflicts
- **Model Access**: OpenRouter (for accessing models from OpenAI, Anthropic, Mistral, etc.)
- **Database**: Supabase with PGVector for vector storage
- **Web Interface**: Chainlit for interactive UI
- **API Framework**: FastAPI
- **Caching**: Redis for model and evidence caching
- **Containerization**: Docker and Docker Compose
- **Language**: Python 3.10+

## Setup and Installation

### Prerequisites

- Python 3.10+
- pip or poetry for package management
- Docker & Docker Compose (optional, for containerized deployment)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/verifact.git
   cd verifact
   ```

2. Install the dependencies:

   ```bash
   pip install -e .
   ```

   Or with development dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

3. Copy the environment template and configure it:

   ```bash
   cp .env-example .env
   ```

4. At minimum, configure the following in your `.env` file:

   ```
   # Required: OpenRouter API key for model access
   OPENROUTER_API_KEY=your_openrouter_api_key_here

   # Optional: Serper for enhanced web search
   USE_SERPER=false
   SERPER_API_KEY=your_serper_api_key_here  # Only if USE_SERPER=true

   # Optional: Supabase for database features
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_key_here
   ```

5. Start the application:

   With Docker (recommended for full stack):

   ```bash
   docker-compose up
   ```

   Or run components separately:

   ```bash
   chainlit run app.py  # For the UI (http://localhost:8501)
   ```

## Model Configuration

VeriFact uses specialized models from OpenRouter's free tier, each selected for specific strengths:

- **Claim Detection**: `qwen/qwen3-8b:free` (best for structured JSON output)
- **Evidence Gathering**: `google/gemma-3-27b-it:free` (optimized for RAG with 128k context)
- **Verdict Writing**: `deepseek/deepseek-chat:free` (best reasoning for evidence synthesis)

You can customize which models are used by editing your `.env` file:

```
# Model Selection
DEFAULT_MODEL=meta-llama/llama-3.3-8b-instruct:free
CLAIM_DETECTOR_MODEL=qwen/qwen3-8b:free
EVIDENCE_HUNTER_MODEL=google/gemma-3-27b-it:free
VERDICT_WRITER_MODEL=deepseek/deepseek-chat:free
```

## OpenAI Agents SDK Integration

VeriFact now integrates the OpenAI Agents SDK, which provides additional agent capabilities alongside our specialized factchecking agents:

```bash
# Set your OpenAI API key for OpenAI Agents SDK
export OPENAI_API_KEY=your_openai_api_key_here
```

The project's internal agent module has been renamed from `src.agents` to `src.verifact_agents` to avoid namespace conflicts. This allows you to:

```python
# Import OpenAI Agents SDK
from agents import Agent as OpenAIAgent

# Import VeriFact agents
from src.verifact_agents import ClaimDetector
```

For more details, see the [OpenAI Agents Integration Guide](docs/agents/openai_agents_integration.md).

## Using OpenRouter

VeriFact uses OpenRouter to access AI models from multiple providers:

1. Sign up for an account at [OpenRouter](https://openrouter.ai/)
2. Get your API key from the OpenRouter dashboard
3. Add to your `.env` file:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   OPENROUTER_SITE_URL=https://yourdomain.com  # Optional but recommended
   OPENROUTER_SITE_NAME=YourAppName            # Optional but recommended
   ```

VeriFact supports models from multiple providers through OpenRouter:

- Meta Llama models (e.g., `meta-llama/llama-3.3-8b-instruct:free`)
- Qwen models (e.g., `qwen/qwen3-8b:free`)
- Google models (e.g., `google/gemma-3-27b-it:free`)
- DeepSeek models (e.g., `deepseek/deepseek-chat:free`)
- And more

## Authentication

The application uses Chainlit's built-in password authentication.

To enable authentication, set in your `.env` file:

```
CHAINLIT_AUTH_ENABLED=true
CHAINLIT_AUTH_SECRET=your_secure_secret_here
```

Generate a secure secret key with:

```bash
chainlit create-secret
```

## Database Configuration

VeriFact can use Supabase with PGVector for vector storage and database operations:

```
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here

# Database Configuration (for local/custom PostgreSQL)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_here  # Change for security
POSTGRES_DB=postgres
POSTGRES_HOST=localhost  # Use "verifact-db" with Docker
POSTGRES_PORT=5432
```

⚠️ **SECURITY WARNING**: Never use default database credentials in production.

## Advanced Configuration

See `.env-example` for additional configuration options:

- Redis caching settings
- Embedding model configuration
- Search API integration
- Logging configuration
- Application ports and hosts

## Configuration

VeriFact uses a centralized configuration system based on environment variables. All configuration is validated using Pydantic to ensure type safety and proper defaults.

### Environment Variables

A template environment file is provided at `.env-example`. Copy this file to create your own configuration:

```bash
cp .env-example .env
```

At minimum, set the following variables in your `.env` file:

- `OPENROUTER_API_KEY`: API key for OpenRouter (required for model access)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Database credentials
- `REDIS_PASSWORD`: Password for Redis (optional but recommended)

See the template file for all available options and their descriptions.

### Configuration Structure

The configuration is organized into logical sections:

- **Application metadata**: General settings like environment and version
- **Database**: Connection and pool settings
- **Redis**: Cache configuration
- **API**: API server settings
- **UI**: Chainlit UI settings
- **Models**: Model selection and parameters
- **Logging**: Log level and format
- **Search**: Search engine configuration

### Using the Configuration

Import the settings from the config module:

```python
from src.config import settings

# Access configuration values
db_url = settings.database.url
api_port = settings.api.port
```

## Docker Deployment

VeriFact includes optimized Docker configurations for both development and production environments.

### Development Setup

To start all services in development mode:

```bash
docker-compose up -d
```

This will start:

- VeriFact API on port 8000
- VeriFact UI on port 8501
- PostgreSQL database with pgvector extension
- Redis for caching

### Production Setup

For production deployment, use both compose files:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The production configuration includes:

- Optimized resource limits
- Health checks for all services
- Nginx for SSL termination and load balancing
- Certbot for automatic SSL certificate renewal

### Helper Script

A helper script is provided to simplify Docker operations:

```bash
# Start in development mode
./scripts/docker-compose-helper.sh up

# Start in production mode
./scripts/docker-compose-helper.sh -e prod up

# View logs
./scripts/docker-compose-helper.sh logs

# Check service health
./scripts/docker-compose-helper.sh health
```

Run `./scripts/docker-compose-helper.sh --help` for more options.

### Container Security

The Docker setup implements security best practices:

- Multi-stage builds for smaller images
- Non-root user for running applications
- Health checks for all services
- Resource limitations to prevent container abuse

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
