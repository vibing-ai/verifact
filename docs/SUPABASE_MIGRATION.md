# Migrating to Supabase

This document outlines the migration process from using a local PostgreSQL database to exclusively using Supabase for VeriFact's database operations.

## Overview

The migration removes the need for a local PostgreSQL service in Docker and updates all relevant configurations and code to work with Supabase exclusively. This simplifies our Docker setup and allows us to leverage Supabase's managed database capabilities.

## Prerequisites

1. **Supabase Project**: You need a Supabase project created with pgvector extension enabled.
2. **Supabase Credentials**: You need the following credentials:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase public (anon) key
   - `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key (for admin operations)

## Changes Made

### 1. Environment Configuration

- Removed local PostgreSQL variables (`POSTGRES_USER`, `POSTGRES_PASSWORD`, etc.)
- Added Supabase connection settings:
  ```
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_KEY=your-supabase-anon-key
  SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
  ```
- Updated Redis URL to use Docker service:
  ```
  REDIS_URL=redis://:${REDIS_PASSWORD:-}@verifact-redis:6379/0
  ```

### 2. Docker Configuration

- Removed the entire `verifact-db` service block from `docker-compose.yml` and `docker-compose.prod.yml`
- Updated dependency references in `verifact-ui` and `verifact-api` to only depend on `verifact-redis`
- Removed `SUPABASE_DB_URL` environment variable that pointed to local DB
- Removed `db-data` volume reference

### 3. Database Initialization

- Created a new module `src/utils/db/db_init.py` to handle Supabase database schema initialization
- Added PGVector extension verification
- Table creation scripts are executed via Supabase connection instead of initialization scripts

### 4. Application Startup

- Updated `src/main.py` to initialize the Supabase database schema during application startup
- Added health checks for Supabase connection
- Added warning if PGVector extension is not enabled in Supabase

### 5. Health Checks

- Updated the health check utilities in `src/utils/health/checkers.py` to verify Supabase connection instead of local PostgreSQL

## Using the Application

1. Copy `.env-example` to `.env` and update it with your Supabase credentials
2. Start the application with Docker Compose:
   ```
   docker-compose up -d
   ```

## Potential Issues

1. **PGVector Extension**: If the pgvector extension is not enabled in your Supabase project, vector similarity search functionality will not work. You need to enable this extension in your Supabase dashboard.

2. **Database Migration**: This update doesn't include data migration from your existing PostgreSQL database to Supabase. If you have existing data, you'll need to migrate it manually.

3. **Connection Pooling**: Supabase has connection limits based on your plan. The connection pool settings (`DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`) should be adjusted according to your Supabase plan limits.

## Running in Production

For production deployments, use:

```
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

This will apply the production configurations with appropriate resource limits and enable additional security features.
