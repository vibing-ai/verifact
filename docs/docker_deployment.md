# Docker Deployment Guide

This document provides detailed instructions for deploying VeriFact using Docker.

## Prerequisites

- Docker Engine (>= 20.10.0)
- Docker Compose (>= 2.0.0)
- Git
- 4GB RAM minimum (8GB recommended)
- Free disk space:
  - Development: 2GB
  - Production: 4GB

## Quick Start

1. Clone the repository:

   ```bash
   git clone https://github.com/vibing-ai/verifact.git
   cd verifact
   ```

2. Configure the environment:

   ```bash
   cp .env-example .env
   # Edit .env with your preferred text editor
   ```

3. Start the services:

   ```bash
   # Development
   docker-compose up -d

   # Production
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

4. Verify deployment:

   ```bash
   # Check containers
   docker-compose ps

   # Check health
   curl http://localhost:8000/health
   ```

## Development Environment

The development setup is optimized for:

- Fast iteration cycles
- Source code hot-reloading
- Easy debugging
- Low resource usage

### Features

- Volume mounts for live code changes
- Development-friendly default settings
- Debug logging enabled
- No resource limits

### Starting Development Mode

```bash
docker-compose up -d
```

This starts:

- API server on http://localhost:8000
- UI on http://localhost:8501
- PostgreSQL database on port 5432
- Redis cache on port 6379

### Debugging

View logs to diagnose issues:

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f verifact-api
```

## Production Environment

The production setup is optimized for:

- Security
- Performance
- Reliability
- Resource efficiency

### Features

- Multi-stage builds for smaller images
- Non-root user execution
- Health checks for all services
- Resource limits to prevent abuse
- SSL termination with automatic renewal
- Optimized PostgreSQL settings
- Regular backups

### Starting Production Mode

```bash
# Create necessary directories
mkdir -p configs/certbot/conf configs/certbot/www configs/nginx

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### SSL Configuration

The production setup includes Nginx with Certbot for SSL:

1. Edit the Nginx configuration:

   ```bash
   # Replace yourdomain.com with your actual domain
   sed -i 's/verifact.yourdomain.com/your-actual-domain.com/g' configs/nginx/verifact.conf
   ```

2. Initialize SSL certificates:

   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certonly --webroot --webroot-path=/var/www/certbot --email your@email.com --agree-tos --no-eff-email -d your-actual-domain.com
   ```

3. Reload Nginx:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx nginx -s reload
   ```

## Helper Script

A helper script `scripts/docker-compose-helper.sh` is included to simplify common operations:

```bash
# Start development environment
./scripts/docker-compose-helper.sh up

# Start production environment
./scripts/docker-compose-helper.sh -e prod up

# View logs
./scripts/docker-compose-helper.sh logs

# Check health
./scripts/docker-compose-helper.sh health

# Backup database
./scripts/docker-compose-helper.sh backup-db

# Restore database
./scripts/docker-compose-helper.sh restore-db backups/verifact_db_backup_20230101_120000.sql
```

Run `./scripts/docker-compose-helper.sh --help` for more options.

## Container Details

### VeriFact API

The API container:

- Runs the FastAPI application
- Exposes port 8000
- Connects to PostgreSQL and Redis
- Includes health check endpoint

### VeriFact UI

The UI container:

- Runs the Chainlit UI
- Exposes port 8501
- Connects to the API service
- Handles websocket connections

### PostgreSQL Database

The database container:

- Uses pgvector extension for vector operations
- Persists data in a Docker volume
- Configured for optimal performance
- Includes automatic initialization

### Redis Cache

The Redis container:

- Provides caching for API responses
- Configured with memory limits
- Uses LRU eviction policy
- Persists data for reliability

### Nginx (Production)

The Nginx container:

- Provides SSL termination
- Acts as a reverse proxy
- Handles load balancing
- Implements security headers
- Rate limits requests

### Certbot (Production)

The Certbot container:

- Obtains and renews SSL certificates
- Uses Let's Encrypt for free certificates
- Automatically renews before expiration

## Upgrading

To upgrade VeriFact:

1. Pull the latest changes:

   ```bash
   git pull
   ```

2. Rebuild containers:

   ```bash
   # Development
   docker-compose build
   docker-compose up -d

   # Production
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

## Troubleshooting

### Service Won't Start

Check for errors:

```bash
docker-compose logs verifact-api
```

Common issues:

- Missing environment variables
- Database connection problems
- Port conflicts

### Database Connection Issues

Verify database is running:

```bash
docker-compose ps verifact-db
```

Check database logs:

```bash
docker-compose logs verifact-db
```

### Performance Issues

Increase resources in docker-compose.prod.yml:

```yaml
deploy:
  resources:
    limits:
      cpus: "2" # Increase as needed
      memory: 2G # Increase as needed
```

### SSL Certificate Issues

Verify Certbot logs:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs certbot
```

Manual renewal:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot renew
```
