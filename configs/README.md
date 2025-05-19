# VeriFact Configuration Files

This directory contains configuration files for the VeriFact application.

## Configuration Types

- `defaults.yml`: Default configuration values
- `dev.yml`: Development environment configuration
- `test.yml`: Testing environment configuration
- `prod.yml`: Production environment configuration

## Configuration Format

VeriFact uses YAML for configuration files. Each file contains sections for:

- Agent settings (model parameters, thresholds, etc.)
- API settings (rate limits, endpoints, etc.)
- Logging and monitoring settings
- External service integrations (search APIs, etc.)

## Custom Configurations

To create a custom configuration:

1. Copy one of the existing configuration files
2. Modify the values as needed
3. Pass the configuration file path to the application at startup:
   ```
   python -m verifact --config path/to/your/config.yml
   ``` 