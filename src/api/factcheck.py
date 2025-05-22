from fastapi import APIRouter
from datetime import datetime
import time
import asyncio
from models.factcheck import (
    FactCheckRequest,
    FactCheckResponse,
    Claim,
    Source
)
from src.verifact_manager_openrouter import VerifactManager

router = APIRouter(prefix="/api/v1")

@router.post("/factcheck", response_model=FactCheckResponse)
async def factcheck(request: FactCheckRequest):
    start_time = time.time()

    # Use our OpenRouter-based VerifactManager
    manager = VerifactManager()
    try:
        verdicts = await manager.run(request.text)

        # Convert verdicts to the API response format
        claims = []
        for verdict in verdicts:
            sources_list = []
            for source_url in verdict.sources:
                sources_list.append(
                    Source(
                        url=source_url,
                        credibility=0.9,  # Default credibility
                        quote="Evidence from source"  # Default quote
                    )
                )

            claims.append(
                Claim(
                    text=verdict.claim,
                    verdict=verdict.verdict,
                    confidence=verdict.confidence,
                    explanation=verdict.explanation,
                    sources=sources_list
                )
            )

        response = FactCheckResponse(
            claims=claims,
            metadata={
                "processing_time": f"{time.time() - start_time:.1f}s",
                "model_version": "1.0.5"
            }
        )
    except Exception as e:
        # Fallback to placeholder response in case of errors
        response = FactCheckResponse(
            claims=[
                Claim(
                    text="Error processing request",
                    verdict="Unverifiable",
                    confidence=0.0,
                    explanation=f"Error: {str(e)}",
                    sources=[]
                )
            ],
            metadata={
                "processing_time": f"{time.time() - start_time:.1f}s",
                "model_version": "1.0.5",
                "error": str(e)
            }
        )
    finally:
        # Close the manager's HTTP client
        await manager.close()

    return response