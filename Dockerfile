FROM python:3.10-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    HOST=0.0.0.0 \
    CHAINLIT_HOST=0.0.0.0 \
    CHAINLIT_PORT=8501

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r verifact && useradd -r -g verifact verifact \
    && mkdir -p /app \
    && chown -R verifact:verifact /app

# Set working directory
WORKDIR /app

# Python dependencies installation stage
FROM base AS dependencies

# Copy only requirements needed for installing dependencies
COPY pyproject.toml ./

# Install dependencies
COPY . .
RUN mkdir -p /app/src 
RUN touch /app/src/__init__.py
RUN pip install --no-cache-dir -e . && pip install --no-cache-dir psutil chainlit==0.7.700 openai~=1.30.0

# Final stage
FROM base

# Copy installed dependencies from the dependencies stage
COPY --from=dependencies /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=verifact:verifact . .
RUN mkdir -p /app/src && touch /app/src/__init__.py

# Ensure entrypoint script exists and is executable
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'if [ "$1" = "api" ]; then' >> /app/entrypoint.sh && \
    echo '    exec uvicorn src.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}' >> /app/entrypoint.sh && \
    echo 'elif [ "$1" = "ui" ]; then' >> /app/entrypoint.sh && \
    echo '    exec chainlit run app.py --host ${CHAINLIT_HOST:-0.0.0.0} --port ${CHAINLIT_PORT:-8501}' >> /app/entrypoint.sh && \
    echo 'else' >> /app/entrypoint.sh && \
    echo '    echo "Please specify either \"api\" or \"ui\" as the first argument"' >> /app/entrypoint.sh && \
    echo '    exit 1' >> /app/entrypoint.sh && \
    echo 'fi' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh && \
    ls -la /app/

# Set up healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose ports
EXPOSE ${PORT} ${CHAINLIT_PORT}

# Switch to non-root user
USER verifact

ENTRYPOINT ["/app/entrypoint.sh"]

# Default to running the UI
CMD ["ui"] 