# VeriFact Basic Usage Examples

This document provides basic examples of how to use the VeriFact system for factchecking. These examples cover standard use cases and common integration patterns.

## Table of Contents

- [Installation](#installation)
- [Initializing the Factchecker](#initializing-the-factchecker)
- [Simple Factchecking](#simple-factchecking)
- [Advanced Configuration](#advanced-configuration)
- [API Integration](#api-integration)
- [Using Individual Agents](#using-individual-agents)
- [Processing Multiple Claims](#processing-multiple-claims)

## Installation

```bash
# Install from PyPI
pip install verifact

# Install from source for development
git clone https://github.com/vibing-ai/verifact.git
cd verifact
pip install -e ".[dev]"
```

## Initializing the Factchecker

```python
import os
from verifact import VeriFact

# Set up API keys (or use environment variables)
os.environ["OPENAI_API_KEY"] = "your_openai_api_key"
os.environ["SEARCH_API_KEY"] = "your_search_api_key"

# Initialize with default settings
factchecker = VeriFact()

# Or initialize with custom configuration
factchecker = VeriFact(
    claim_detector_config={
        "min_check_worthiness": 0.8,
        "max_claims": 3
    },
    evidence_hunter_config={
        "max_sources": 5,
        "trusted_domains": ["edu", "gov", "org"]
    },
    verdict_writer_config={
        "verdict_scale": "five_point",
        "explanation_detail": "detailed"
    }
)
```

## Simple Factchecking

### Checking a Single Claim

```python
# Check a single claim directly
result = factchecker.check_claim("The Earth is approximately 4.54 billion years old.")

print(f"Claim: {result.claim}")
print(f"Verdict: {result.verdict}")
print(f"Confidence: {result.confidence}")
print(f"Explanation: {result.explanation}")
print("\nSources:")
for source in result.sources:
    print(f"- {source.url}")
```

### Checking Text with Multiple Claims

```python
# Process a text that may contain multiple claims
text = """
The Earth is approximately 4.54 billion years old. Water covers about 71% of the
Earth's surface. Mount Everest is the highest mountain on Earth with a height of
8,848.86 meters above sea level. I think chocolate ice cream is the best flavor,
but some people prefer vanilla.
"""

results = factchecker.check_text(text)

print(f"Found {len(results)} claims:")
for i, result in enumerate(results):
    print(f"\nClaim {i+1}: {result.claim}")
    print(f"Verdict: {result.verdict}")
    print(f"Confidence: {result.confidence}")
```

## Advanced Configuration

### Customizing Agent Behavior

```python
# Configure the factchecker with detailed options
factchecker = VeriFact(
    claim_detector_config={
        "min_check_worthiness": 0.7,
        "domains": ["politics", "science", "health"],
        "max_claims": 5,
        "include_entities": True
    },
    evidence_hunter_config={
        "max_sources": 7,
        "min_credibility": 0.7,
        "trusted_domains": ["edu", "gov", "org"],
        "search_depth": "thorough",
        "max_age": 365,  # Only sources from the last year
        "include_news": True,
        "include_social": False
    },
    verdict_writer_config={
        "verdict_scale": "five_point",
        "explanation_detail": "detailed",
        "include_confidence": True,
        "include_sources": True,
        "include_alternatives": True,
        "max_explanation_length": 1000,
        "citation_style": "inline"
    }
)

# Process a claim with the custom configuration
result = factchecker.check_claim(
    "COVID-19 vaccines have been tested in clinical trials with tens of thousands of participants."
)
```

### Using Different Models

```python
# Configure with specific models for each agent
factchecker = VeriFact(
    claim_detector_model="gpt-4o",
    evidence_hunter_model="gpt-4o",
    verdict_writer_model="gpt-4o-mini",
    temperature=0.1  # Lower temperature for more consistent results
)
```

## API Integration

### Using the FastAPI Server

First, run the API server:

```bash
# Start the API server
verifact serve --port 8000 --host 0.0.0.0
```

Then, use it from any client:

```python
import requests
import json

# Send a request to the API
response = requests.post(
    "http://localhost:8000/api/v1/factcheck",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "text": "The Earth is approximately 4.54 billion years old. Water covers about 71% of the Earth's surface.",
        "options": {
            "min_check_worthiness": 0.7,
            "domains": ["science"],
            "max_claims": 5,
            "explanation_detail": "detailed"
        }
    }
)

# Process the results
results = response.json()
for claim in results["claims"]:
    print(f"Claim: {claim['text']}")
    print(f"Verdict: {claim['verdict']}")
    print(f"Confidence: {claim['confidence']}")
    print(f"Explanation: {claim['explanation']}")
    print("---")
```

## Using Individual Agents

### ClaimDetector

```python
from verifact.agents import ClaimDetector

detector = ClaimDetector(
    min_check_worthiness=0.7,
    max_claims=5
)

text = """
The Earth is approximately 4.54 billion years old. Water covers about 71% of the
Earth's surface. Mount Everest is the highest mountain on Earth with a height of
8,848.86 meters above sea level. I think chocolate ice cream is the best flavor.
"""

claims = detector.detect_claims(text)
print(f"Detected {len(claims)} claims:")
for claim in claims:
    print(f"- {claim.text} (Worthiness: {claim.check_worthiness:.2f})")
```

### EvidenceHunter

```python
from verifact.agents import EvidenceHunter

hunter = EvidenceHunter(
    max_sources=5,
    trusted_domains=["edu", "gov", "org"]
)

claim = {
    "text": "The Earth is approximately 4.54 billion years old",
    "domain": "science"
}

evidence = hunter.gather_evidence(claim)
print(f"Found {len(evidence)} pieces of evidence:")
for i, e in enumerate(evidence):
    print(f"{i+1}. {e.text}")
    print(f"   Source: {e.source.title} ({e.source.url})")
    print(f"   Stance: {e.stance}, Relevance: {e.relevance:.2f}")
    print("---")
```

### VerdictWriter

```python
from verifact.agents import VerdictWriter

writer = VerdictWriter(
    verdict_scale="five_point",
    explanation_detail="detailed"
)

claim = {
    "text": "The Earth is approximately 4.54 billion years old",
    "domain": "science"
}

evidence = [...]  # Evidence from EvidenceHunter

verdict = writer.generate_verdict(claim, evidence)
print(f"Verdict: {verdict.verdict}")
print(f"Confidence: {verdict.confidence}")
print(f"Explanation: {verdict.explanation}")
```

## Processing Multiple Claims

### Batch Processing

```python
claims = [
    "The Earth is approximately 4.54 billion years old.",
    "Water covers about 71% of the Earth's surface.",
    "Mount Everest is the highest mountain on Earth.",
    "The average adult human body contains about 60% water."
]

# Process multiple claims in batch
results = factchecker.check_claims(claims)

for claim, result in zip(claims, results):
    print(f"Claim: {claim}")
    print(f"Verdict: {result.verdict}")
    print(f"Confidence: {result.confidence}")
    print("---")
```

### Async Processing

```python
import asyncio
from verifact import VeriFact

async def process_claims_async():
    factchecker = VeriFact()

    claims = [
        "The Earth is approximately 4.54 billion years old.",
        "Water covers about 71% of the Earth's surface.",
        "Mount Everest is the highest mountain on Earth.",
        "The average adult human body contains about 60% water."
    ]

    # Process claims concurrently
    tasks = [factchecker.check_claim_async(claim) for claim in claims]
    results = await asyncio.gather(*tasks)

    for claim, result in zip(claims, results):
        print(f"Claim: {claim}")
        print(f"Verdict: {result.verdict}")
        print(f"Confidence: {result.confidence}")
        print("---")

# Run the async function
asyncio.run(process_claims_async())
```

## Error Handling

```python
from verifact import VeriFact, VerifactError

factchecker = VeriFact()

try:
    result = factchecker.check_claim("The Earth is approximately 4.54 billion years old.")
    print(f"Verdict: {result.verdict}")
except VerifactError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

For more advanced examples and use cases, see the [advanced examples](./advanced_usage.md) documentation.
