# VeriFact Configuration Guide

This document provides information about all configuration files used in the VeriFact project.

## Environment Variables

VeriFact uses environment variables for configuration. Create a `.env` file in the project root with the following variables:

```bash
# VeriFact Authentication Configuration
CHAINLIT_AUTH_SECRET="your-secret-key"

# Admin user credentials
VERIFACT_ADMIN_USER="admin"
VERIFACT_ADMIN_PASSWORD="admin"

# Demo user credentials
VERIFACT_DEMO_USER="demo"
VERIFACT_DEMO_PASSWORD="demo"

# Enable Chainlit data persistence
CHAINLIT_PERSIST=true

# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_SITE_URL=https://yourdomain.com
OPENROUTER_SITE_NAME=YourAppName
```

A template `.env` file is provided in `configs/env.template`.

## Chainlit Configuration

VeriFact uses Chainlit for its interactive UI. Configuration for Chainlit is stored in `chainlit.toml` in the project root.

### Key Chainlit Settings

```toml
[UI]
# Name of the app and organization
name = "VeriFact"
description = "AI-powered factchecking platform"
avatar = "/public/logo.png"
theme = "light"

[meta]
# Meta tags for website
title = "VeriFact"
description = "Open-source AI factchecking platform"
favicon = "/public/favicon.ico"

[features]
# Feature toggles
wiki = false
auth_with_credentials = true
```

## Docker Configuration

Docker configurations are stored in:

- `Dockerfile`: Configures the main VeriFact container
- `docker-compose.yml`: Orchestrates all services required for running VeriFact

## Testing Configuration

Testing configuration is managed through:

- `pytest.ini`: Controls test discovery and execution parameters
- Pre-commit hooks in `.pre-commit-config.yaml`

## Editor Configuration

A consistent development environment is provided through `.vscode/settings.json`, which includes:

- Linting configuration
- Formatting settings
- Editor behavior settings

## Dependency Management

The project uses `pyproject.toml` for dependency management. All dependencies should be added to this file rather than creating separate requirements.txt files.

```toml
[build-system]
requires = ["setuptools>=42.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "verifact"
version = "0.1.0"
description = "Open-source AI factchecking platform"
# ... additional configuration details
```
