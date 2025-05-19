# VeriFact: Open-Source AI Factchecking Platform

VeriFact is an open-source AI factchecking platform that leverages a multi-agent architecture to detect factual claims, gather evidence, and generate verdicts with transparent explanations and source citations.

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Overview

VeriFact uses a pipeline of specialized AI agents to process and verify factual claims:

1. **ClaimDetector**: Identifies and extracts check-worthy factual claims from text
2. **EvidenceHunter**: Searches for and evaluates supporting/contradicting evidence
3. **VerdictWriter**: Synthesizes evidence to produce verdicts with confidence scores and explanations

Each agent is designed to perform its specialized task efficiently while maintaining transparency in the factchecking process.

## Implementation Status

VeriFact is under active development. Here's the current status of key features:

| Feature                | Status      | Notes                                              |
| ---------------------- | ----------- | -------------------------------------------------- |
| ClaimDetector Agent    | Implemented | Uses OpenAI Agent SDK with OpenRouter              |
| EvidenceHunter Agent   | Implemented | Uses OpenAI Agent SDK with OpenRouter              |
| VerdictWriter Agent    | Implemented | Uses OpenAI Agent SDK with OpenRouter              |
| Chainlit UI            | Implemented | Interactive chat interface with step visualization |
| FastAPI Backend        | Implemented | RESTful API for factchecking                       |
| Supabase Integration   | In Progress | Basic setup implemented, advanced features planned |
| PGVector Integration   | Planned     | For semantic search capabilities                   |
| Docker Deployment      | Implemented | Full containerization with docker-compose          |
| Multi-claim Processing | Planned     | Currently processes claims sequentially            |
| Multilingual Support   | Planned     | English-only in current version                    |
| Media Analysis         | Planned     | Text-only factchecking currently                   |

## Tech Stack

- **Agent Framework**: OpenAI Agent SDK
- **Model Access**: OpenRouter (for accessing models from OpenAI, Anthropic, Mistral, etc.)
- **Database**: Supabase with PGVector for vector storage
- **Web Interface**: Chainlit for interactive UI
- **API Framework**: FastAPI
- **Containerization**: Docker and Docker Compose
- **Language**: Python 3.10+

## Getting Started

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (for containerized deployment)
- OpenRouter API key
- Supabase account (optional for advanced features)

### Installation

1. Clone the repository:

   ```
   git clone https://github.com/vibing-ai/verifact.git
   cd verifact
   ```

2. Install dependencies:

   ```
   pip install -e .  # Install package with dependencies
   # or for development:
   pip install -e ".[dev]"  # Install with development dependencies
   ```

3. Set up environment variables:

   - Copy `configs/env.template` to `.env`
   - Add your OpenRouter API key (required)
   - Configure Supabase credentials if needed

### Running with Docker

The easiest way to run VeriFact is using Docker Compose:

```
docker-compose up
```

This will start:

- The Chainlit web interface at http://localhost:8501
- The FastAPI backend at http://localhost:8000
- A PostgreSQL database with the PGVector extension

### Manual Setup

#### Running the Web Interface

```
chainlit run app.py
```

#### Running the API Server

```
uvicorn src.main:app --reload
```

#### CLI Usage

```
python cli.py --input "Text containing claims to verify"
```

## Configuration

VeriFact can be configured through environment variables or a `.env` file:

| Variable             | Description                             | Required              |
| -------------------- | --------------------------------------- | --------------------- |
| OPENROUTER_API_KEY   | Your OpenRouter API key                 | Yes                   |
| OPENROUTER_SITE_URL  | Your site URL for OpenRouter reference  | No                    |
| OPENROUTER_SITE_NAME | Your site name for OpenRouter reference | No                    |
| SUPABASE_URL         | Supabase project URL                    | For Supabase features |
| SUPABASE_KEY         | Supabase API key                        | For Supabase features |
| SUPABASE_DB_URL      | Direct PostgreSQL connection string     | For local development |

## Development

### Project Structure

```
verifact/
├── src/                        # Source code
│   ├── agents/                 # Agent implementations
│   ├── api/                    # API endpoints
│   ├── models/                 # ML models and Pydantic schemas
│   └── utils/                  # Utilities
├── app.py                      # Chainlit application
├── cli.py                      # Command-line interface
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Docker build configuration
├── pyproject.toml              # Project metadata and dependencies
├── requirements.txt            # Dependencies (deprecated)
└── configs/                    # Configuration files
```

### Running Tests

```
pytest
```

## Using OpenRouter

VeriFact uses OpenRouter to access AI models from multiple providers:

1. Sign up for an account at [OpenRouter](https://openrouter.ai/)
2. Get your API key from the OpenRouter dashboard
3. In your `.env` file, set:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

VeriFact supports models from multiple providers through OpenRouter:

- OpenAI models (e.g., `openai/gpt-4o`)
- Anthropic models (e.g., `anthropic/claude-3-opus`)
- Mistral models (e.g., `mistral/mistral-large`)
- And more

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
