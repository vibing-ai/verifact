# ClaimDetector Agent Documentation

## Overview

The ClaimDetector agent is responsible for identifying factual claims in text that warrant verification. It analyzes input text to extract check-worthy factual statements, distinguishing them from opinions, questions, or other non-verifiable content.

## Default Model

The ClaimDetector uses **Qwen 3-8b:free** as its default model, selected for:

- Superior structured JSON output capabilities
- Strong entity extraction and classification
- Excellent performance for identifying factual statements
- Efficient balance of performance and resource usage

Alternative models include:

- meta-llama/llama-3.3-8b-instruct:free (good general performance)
- microsoft/phi-4-reasoning:free (strong reasoning with lower VRAM needs)

## Key Capabilities

- Identifies explicit and implicit factual claims
- Assigns check-worthiness scores to each claim
- Normalizes claims into standard formats
- Extracts entities and relationships from claims
- Classifies claims by domain (e.g., politics, science, health)

## Input/Output Specification

### Input

The ClaimDetector accepts:

- Raw text containing potential claims
- Optional context metadata
- Configuration parameters

**Example Input:**

```json
{
  "text": "The Earth is approximately 4.54 billion years old. I think chocolate ice cream is the best flavor. Water covers about 71% of the Earth's surface.",
  "context": {
    "source": "example scientific article",
    "publication_date": "2023-05-15"
  },
  "config": {
    "min_check_worthiness": 0.7,
    "domains": ["science", "geography"],
    "max_claims": 5
  }
}
```

### Output

The ClaimDetector produces:

- An array of extracted claims, each containing:
  - Normalized claim text
  - Original context
  - Check-worthiness score (0-1)
  - Confidence score (0-1)
  - Domain classification
  - Extracted entities

**Example Output:**

```json
{
  "claims": [
    {
      "text": "The Earth is approximately 4.54 billion years old",
      "original_text": "The Earth is approximately 4.54 billion years old.",
      "context": "example scientific article (2023-05-15)",
      "check_worthiness": 0.95,
      "confidence": 0.98,
      "domain": "science",
      "entities": [
        { "text": "Earth", "type": "CELESTIAL_BODY" },
        { "text": "4.54 billion years", "type": "TIME_PERIOD" }
      ]
    },
    {
      "text": "Water covers about 71% of Earth's surface",
      "original_text": "Water covers about 71% of the Earth's surface.",
      "context": "example scientific article (2023-05-15)",
      "check_worthiness": 0.91,
      "confidence": 0.97,
      "domain": "geography",
      "entities": [
        { "text": "Water", "type": "SUBSTANCE" },
        { "text": "71%", "type": "PERCENTAGE" },
        { "text": "Earth", "type": "CELESTIAL_BODY" }
      ]
    }
  ],
  "metadata": {
    "num_claims_detected": 2,
    "num_claims_filtered": 1,
    "processing_time": "0.24s"
  }
}
```

## Implementation Details

### Models and Techniques

The ClaimDetector uses:

- Natural Language Processing (NLP) for text parsing and understanding
- Named Entity Recognition (NER) for entity extraction
- Domain-specific classification models
- Check-worthiness scoring algorithms

### Prompt Design

The agent uses a carefully crafted prompt that instructs the LLM to:

1. Identify statements presented as facts
2. Distinguish between factual claims and opinions
3. Determine how check-worthy each claim is
4. Extract relevant entities and relationships
5. Normalize claims to a standard format

**Simplified Prompt Template:**

```
You are a ClaimDetector agent tasked with identifying factual claims in text.
Analyze the following text and extract claims that can be factually verified.
For each claim:
1. Extract the exact claim text
2. Assign a check-worthiness score (0-1)
3. Identify key entities
4. Categorize by domain (politics, health, science, etc.)
Only include statements presented as facts, not opinions or subjective statements.

Text to analyze:
{input_text}
```

## Configuration Options

| Parameter            | Type     | Default | Description                                            |
| -------------------- | -------- | ------- | ------------------------------------------------------ |
| min_check_worthiness | float    | 0.7     | Minimum threshold for considering a claim check-worthy |
| domains              | string[] | []      | Specific domains to focus on (empty = all domains)     |
| max_claims           | integer  | 10      | Maximum number of claims to return                     |
| include_entities     | boolean  | true    | Whether to extract and include entities in results     |
| include_context      | boolean  | true    | Whether to include original context in results         |

## Limitations and Edge Cases

- May struggle with highly technical domain-specific claims
- Can have difficulty with implicit claims that require background knowledge
- Satire or figurative language might be misinterpreted as factual claims
- Claims expressed across multiple sentences might not be properly connected

## Performance Metrics

| Metric                  | Target | Current |
| ----------------------- | ------ | ------- |
| Precision               | ≥85%   | 87%     |
| Recall                  | ≥80%   | 83%     |
| F1 Score                | ≥82%   | 85%     |
| Average processing time | <500ms | 240ms   |

## Example Usage

```python
from verifact.agents import ClaimDetector

detector = ClaimDetector(
    min_check_worthiness=0.7,
    domains=["politics", "science"],
    max_claims=5
)

text = """
The United States has 50 states. The President serves a four-year term.
I believe the Constitution is the greatest document ever written.
The Earth revolves around the Sun and completes an orbit every 365.25 days.
"""

claims = detector.detect_claims(text)
for claim in claims:
    print(f"Claim: {claim.text}")
    print(f"Check-worthiness: {claim.check_worthiness}")
    print(f"Domain: {claim.domain}")
    print("---")
```

## Future Improvements

- Improved detection of implicit claims
- Better handling of claims that span multiple sentences
- Domain-specific specialized claim detection
- Multilingual claim detection capabilities
- Real-time learning from user feedback
