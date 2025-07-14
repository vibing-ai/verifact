from fastapi import APIRouter

import time
from models.factcheck import FactCheckRequest, FactCheckResponse, Claim, Source, FactCheckOptions

router = APIRouter(prefix="/api/v1")


@router.post("/factcheck", response_model=FactCheckResponse)
async def factcheck(request: FactCheckRequest):
    start_time = time.time()

    # Extract the text to be fact-checked from the request
    text_to_check = request.text
    options = request.options or FactCheckOptions()

    # TODO: Implement actual fact-checking logic here
    # This is a placeholder response
    return FactCheckResponse(
        claims=[
            Claim(
                text="Example claim",
                verdict="Mostly True",
                confidence=0.89,
                explanation="This is a detailed explanation with evidence",
                sources=[
                    Source(url="source1.com", credibility=0.95, quote="Example quote from source")
                ],
            )
        ],
        metadata={
            "processing_time": f"{time.time() - start_time:.1f}s",
            "model_version": "1.0.4",
            "input_length": len(text_to_check),
            "options_used": {
                "min_check_worthiness": options.min_check_worthiness,
                "domains": options.domains,
                "max_claims": options.max_claims,
                "explanation_detail": options.explanation_detail,
            },
        },
    )

