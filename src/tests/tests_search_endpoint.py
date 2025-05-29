# tests/test_search_endpoint.py

import pytest
from httpx import AsyncClient
from app import app

@pytest.mark.asyncio
async def test_search_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        params = {"query": "climate change"}
        response = await ac.get("/search", params=params)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for item in data:
            assert "title" in item
            assert "url" in item
