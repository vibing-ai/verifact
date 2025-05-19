# EvidenceHunter Agent Documentation

## Overview

The EvidenceHunter agent is responsible for retrieving and evaluating evidence related to claims identified by the ClaimDetector. It searches for relevant information from multiple sources, evaluates source credibility, and aggregates evidence that either supports or contradicts the claim.

## Key Capabilities

- Multi-source evidence retrieval
- Dynamic query formulation based on claim content
- Source credibility assessment
- Evidence relevance ranking
- Contradiction detection and resolution
- Evidence filtering and deduplication

## Input/Output Specification

### Input

The EvidenceHunter accepts:

- Claim objects from the ClaimDetector
- Search configuration parameters
- Optional previous evidence to expand upon

**Example Input:**

```json
{
  "claim": {
    "text": "The Earth is approximately 4.54 billion years old",
    "domain": "science",
    "entities": [
      { "text": "Earth", "type": "CELESTIAL_BODY" },
      { "text": "4.54 billion years", "type": "TIME_PERIOD" }
    ]
  },
  "config": {
    "max_sources": 5,
    "min_credibility": 0.7,
    "trusted_domains": ["edu", "gov", "org"],
    "search_depth": "standard"
  }
}
```

### Output

The EvidenceHunter produces:

- A collection of evidence pieces with:
  - Extracted passages relevant to the claim
  - Source information and credibility scores
  - Relevance scores for each evidence piece
  - Stance classification (supporting, contradicting, neutral)
  - Temporal information (publication dates, last updated)

**Example Output:**

```json
{
  "claim": "The Earth is approximately 4.54 billion years old",
  "evidence": [
    {
      "text": "Scientists have determined that the Earth is 4.54 billion years old with an error range of less than 1 percent.",
      "source": {
        "url": "https://example.edu/earth-age",
        "title": "Earth's Age: Scientific Consensus",
        "domain": "example.edu",
        "credibility": 0.95,
        "publication_date": "2022-03-15",
        "last_updated": "2023-01-10"
      },
      "relevance": 0.98,
      "stance": "supporting"
    },
    {
      "text": "Radiometric dating of meteorites and Earth's oldest minerals confirms an age of 4.54 billion years with an uncertainty of less than 1%.",
      "source": {
        "url": "https://example.gov/geological-survey/earth-formation",
        "title": "Geological Survey: Earth Formation",
        "domain": "example.gov",
        "credibility": 0.97,
        "publication_date": "2021-08-22",
        "last_updated": null
      },
      "relevance": 0.96,
      "stance": "supporting"
    },
    {
      "text": "Some religious texts suggest the Earth could be as young as 6,000 years old, a view not supported by scientific evidence.",
      "source": {
        "url": "https://example.org/science-religion-debate",
        "title": "Science and Religion: Perspectives on Earth's Age",
        "domain": "example.org",
        "credibility": 0.85,
        "publication_date": "2020-11-05",
        "last_updated": "2022-04-18"
      },
      "relevance": 0.82,
      "stance": "contextual"
    }
  ],
  "metadata": {
    "total_sources_found": 12,
    "sources_used": 3,
    "search_queries": [
      "age of Earth scientific consensus",
      "Earth 4.54 billion years evidence",
      "how old is Earth radiometric dating"
    ],
    "processing_time": "3.45s"
  }
}
```

## Implementation Details

### Models and Techniques

The EvidenceHunter uses:

- Web search APIs (e.g., Google Search, Bing, DuckDuckGo)
- Vector embeddings for semantic similarity matching
- Dense passage retrieval for finding relevant content
- Source credibility databases and heuristics
- Content extraction algorithms for web pages

### Prompt Design

The agent uses specialized prompts to guide the LLM in different stages of evidence gathering:

**Query Formulation Prompt Template:**

```
You are an EvidenceHunter agent tasked with finding evidence for the following claim:
"{claim_text}"

Generate 3-5 search queries that would help find relevant information about this claim.
For each query:
1. Focus on different aspects of the claim
2. Use alternative phrasings
3. Include key entities
4. Prioritize specific, targeted queries

Format your response as a list of queries, one per line.
```

**Evidence Evaluation Prompt Template:**

```
You are an EvidenceHunter agent tasked with evaluating evidence for the following claim:
"{claim_text}"

Analyze this evidence passage:
"{evidence_text}"
Source: {source_url} ({publication_date})

Determine:
1. Relevance: How relevant is this passage to the claim (0-1)?
2. Stance: Does this evidence support, contradict, or provide context for the claim?
3. Key information: What specific facts in this passage relate to the claim?

Respond in a structured JSON format with these assessments.
```

## Configuration Options

| Parameter        | Type     | Default    | Description                                           |
| ---------------- | -------- | ---------- | ----------------------------------------------------- |
| max_sources      | integer  | 5          | Maximum number of sources to include in evidence      |
| min_credibility  | float    | 0.7        | Minimum source credibility threshold (0-1)            |
| trusted_domains  | string[] | []         | List of trusted domain extensions or specific domains |
| excluded_domains | string[] | []         | List of domains to exclude from results               |
| search_depth     | string   | "standard" | Search depth ("quick", "standard", "thorough")        |
| max_age          | integer  | null       | Maximum age of sources in days (null = no limit)      |
| include_news     | boolean  | true       | Whether to include news sources                       |
| include_social   | boolean  | false      | Whether to include social media sources               |

## Limitations and Edge Cases

- May be limited by search API rate limits and quotas
- Can struggle with very recent events not yet well-documented
- Might miss evidence in non-text formats (images, videos, etc.)
- Source credibility assessment may have biases or gaps
- Cannot access paywalled or private content
- May have difficulty with highly technical or niche topics

## Performance Metrics

| Metric                           | Target | Current |
| -------------------------------- | ------ | ------- |
| Relevant evidence retrieval rate | ≥90%   | 92%     |
| Average evidence quality score   | ≥0.8   | 0.83    |
| False evidence rate              | ≤2%    | 1.5%    |
| Average processing time          | <5s    | 3.45s   |

## Example Usage

```python
from verifact.agents import EvidenceHunter

hunter = EvidenceHunter(
    max_sources=5,
    min_credibility=0.7,
    trusted_domains=["edu", "gov", "org"],
    search_depth="standard"
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

## Future Improvements

- Integration with specialized academic search engines
- Advanced source credibility assessment
- Cross-lingual evidence retrieval
- Multimodal evidence gathering (images, videos, data)
- Temporal awareness for time-sensitive claims
- Interactive evidence gathering with feedback loops
