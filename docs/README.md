# VeriFact Documentation

This directory contains documentation for the VeriFact project.

## Documentation Structure

- `api/`: API reference documentation for the REST API endpoints
- `agents/`: Detailed documentation on individual agents, their configurations, and behaviors
- `examples/`: Conceptual usage examples with explanations and code snippets
- `tutorials/`: Step-by-step tutorials for users and contributors
- `SETUP.md`: Comprehensive setup guide for development environments
- `DEVELOPMENT.md`: Development guidelines and workflows

## Model Selection

Each agent in VeriFact uses a specialized model from OpenRouter's free tier:

- ClaimDetector: Qwen 3-8b (optimized for structured output)
- EvidenceHunter: Google Gemma 3-27b-it (optimized for RAG with 128k context)
- VerdictWriter: DeepSeek Chat (best reasoning for evidence synthesis)

For more details, see the individual agent documentation files in the `agents/` directory and the OpenRouter model usage guidelines in `DEVELOPMENT.md`.

## Documentation vs Examples

The project maintains several directories for examples and documentation:

- `docs/examples/`: Contains markdown documentation with explanations, screenshots, and annotated code snippets
- `/examples/`: Contains runnable example scripts that demonstrate practical usage scenarios
- `/notebooks/`: Contains Jupyter notebooks for interactive exploration and learning

## Contributing to Documentation

Documentation is a critical part of making VeriFact accessible to users and contributors. When contributing to the codebase, please ensure that you update the relevant documentation.

For major documentation contributions, please follow the same process as code contributions by opening an issue and submitting a pull request.
