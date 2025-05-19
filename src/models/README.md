# Models

This directory contains the data models used throughout the VeriFact application.

## Contents

- `factcheck.py`: Pydantic models for claims, evidence, verdicts, and API requests/responses

## Purpose

The models in this directory define the data structures used for:

1. **Agent Communication**: Standardized models for passing data between agents
2. **API Contracts**: Request and response models for API endpoints
3. **Database Storage**: Models that define how data is stored in Supabase/PGVector
4. **Validation**: Type definitions and field validations for ensuring data integrity

## Usage

To use these models in your code:

```python
from src.models.factcheck import Claim, Evidence, Verdict

# Create a claim
claim = Claim(
    text="The Earth is flat",
    context="From a discussion about planetary science",
    checkworthy=True
)

# Create evidence
evidence = Evidence(
    text="Satellite imagery and physics calculations confirm Earth's spherical shape",
    source="https://nasa.gov/earth-images",
    relevance=0.95,
    stance="contradicting"
)

# Create a verdict
verdict = Verdict(
    claim=claim.text,
    verdict="false",
    confidence=0.98,
    explanation="Multiple lines of evidence confirm Earth is approximately spherical",
    sources=["https://nasa.gov/earth-images"]
)
```

## Adding New Models

When adding new models:

1. Create appropriately named files for related model groups
2. Use Pydantic's BaseModel as the base class
3. Include detailed field descriptions
4. Add appropriate validation using Pydantic Field types
5. Include type hints for all fields
6. Document the model with a docstring
