# tests/test_factcheck_endpoint.py

import pytest
from httpx import AsyncClient
from app import app  # Adjust the import based on your project structure

@pytest.mark.asyncio
async def test_factcheck_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "claim": "The Eiffel Tower is located in Berlin."
        }
        response = await ac.post("/factcheck", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "verdict" in data
        assert "evidence" in data
        assert data["verdict"] in ["true", "false", "uncertain"]

