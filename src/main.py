"""
VeriFact API Entry Point

This module serves as the main entry point for the VeriFact API service.
It initializes a FastAPI application with the factcheck router.

To run the API server directly:
    python -m src.main

For the web UI interface, use `app.py` with Chainlit.
For CLI access, use `cli.py`.
"""

from fastapi import FastAPI
from src.api.factcheck import router as factcheck_router

description = """
# VeriFact API

VeriFact is an open-source AI factchecking application designed to detect claims, 
gather evidence, and generate accurate verdicts.

## Factchecking

You can use this API to verify factual claims in text by:
* **Submitting text** containing potential claims
* Receiving **verdicts** with explanations and source citations

The system employs three specialized AI agents:
* **ClaimDetector**: Identifies factual claims worth checking
* **EvidenceHunter**: Gathers evidence from trusted sources
* **VerdictWriter**: Analyzes evidence and generates verdicts

## Note

This is an alpha version of the API. Features and endpoints may change as the project evolves.
"""

tags_metadata = [
    {
        "name": "Factchecking",
        "description": "Operations related to factchecking claims in text.",
    },
]

app = FastAPI(
    title="VeriFact API",
    description=description,
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "VeriFact Team",
        "url": "https://github.com/vibing-ai/verifact",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

app.include_router(factcheck_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
