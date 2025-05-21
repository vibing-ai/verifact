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
    build-essential \
    libssl-dev \
    libffi-dev \
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

# Install virtualenv
RUN pip install --no-cache-dir virtualenv

# Create and activate virtual environment
RUN virtualenv /venv
ENV PATH="/venv/bin:$PATH"

# Copy only requirements needed for installing dependencies
COPY requirements.txt ./

# Install dependencies in the virtual environment
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir cryptography>=41.0.0

# If openai-agents is needed, install it separately with a compatible version
RUN pip install --no-cache-dir "openai-agents>=0.0.15"

# Copy application code
COPY . .
RUN mkdir -p /app/src 
RUN touch /app/src/__init__.py
# Install package in development mode without dependencies
RUN pip install --no-cache-dir --no-deps -e .

# Final stage
FROM base

# Copy virtual environment from dependencies stage
COPY --from=dependencies /venv /venv
ENV PATH="/venv/bin:$PATH"

# Verify cryptography is installed
RUN /venv/bin/pip list | grep cryptography || /venv/bin/pip install --no-cache-dir cryptography>=41.0.0

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