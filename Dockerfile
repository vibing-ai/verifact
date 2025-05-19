FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set Python path to include the src directory
ENV PYTHONPATH=/app

# Set default environment variables
ENV PORT=8000
ENV HOST=0.0.0.0
ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=8501

# Expose ports for FastAPI and Chainlit
EXPOSE ${PORT}
EXPOSE 8501

# Create a script to choose between running API or UI
RUN echo '#!/bin/bash\n\
if [ "$1" = "api" ]; then\n\
    exec uvicorn src.main:app --host ${HOST} --port ${PORT}\n\
elif [ "$1" = "ui" ]; then\n\
    exec chainlit run app.py --host ${CHAINLIT_HOST} --port ${CHAINLIT_PORT}\n\
else\n\
    echo "Please specify either 'api' or 'ui' as the first argument"\n\
    exit 1\n\
fi' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# Default to running the UI
CMD ["ui"] 