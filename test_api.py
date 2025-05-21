"""Minimal API server for testing.

This is a standalone FastAPI server for testing the API endpoints.
"""

import os
from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="VeriFact API Test",
    description="Minimal API server for testing",
    version="0.1.0",
)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0-test",
        "timestamp": 0,
        "environment": "test",
    }

@app.get("/api/v1/test")
async def test_endpoint():
    """Test endpoint."""
    return {
        "message": "API is working!",
        "status": "success",
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port) 