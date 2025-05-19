# VeriFact API Implementation

This directory contains the API implementation for the VeriFact factchecking service.

## API Structure

The API is built using FastAPI and follows these design principles:

- RESTful endpoints
- Pydantic models for request/response validation
- Automatic OpenAPI documentation
- Modular router-based architecture

## Files

- `factcheck.py`: Contains the main factchecking endpoint
- Future endpoint modules will be added here

## Adding New Endpoints

To add a new endpoint to the API:

1. Create a new module in the `src/api` directory
2. Define a new router with appropriate tags and responses:

```python
router = APIRouter(
    tags=["YourTag"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)
```

3. Define your endpoint with detailed OpenAPI documentation:

```python
@router.get(
    "/your-endpoint",
    response_model=YourResponseModel,
    summary="Short summary",
    description="""
    Detailed description of what your endpoint does.

    This can include markdown formatting.
    """,
    response_description="What the response contains"
)
async def your_endpoint():
    # Implementation
    pass
```

4. Include your router in `src/main.py`:

```python
from src.api.your_module import router as your_router
app.include_router(your_router, prefix="/api/v1")
```

## OpenAPI Documentation

The API automatically generates OpenAPI documentation from:

- Pydantic models (for schema definitions)
- Function docstrings
- Endpoint decorators (summary, description, etc.)

To ensure good documentation:

1. Use type hints and Pydantic models
2. Add detailed docstrings to functions
3. Use the summary, description, and response_description parameters
4. Add examples where appropriate

FastAPI serves the documentation at:

- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json`
