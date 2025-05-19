# VerdictWriter Agent Documentation

## Overview

The VerdictWriter agent is responsible for synthesizing evidence gathered by the EvidenceHunter to generate verdicts about claims identified by the ClaimDetector. It analyzes evidence, evaluates contradictions, produces a final verdict, and provides a clear, well-reasoned explanation with source citations.

## Key Capabilities

- Evidence synthesis and weighting
- Contradictory evidence reconciliation
- Confidence score determination
- Natural language explanation generation
- Citation management
- Uncertainty handling
- Bias detection and mitigation

## Input/Output Specification

### Input

The VerdictWriter accepts:

- The original claim from the ClaimDetector
- A collection of evidence from the EvidenceHunter
- Configuration parameters for verdict format and explanation detail

**Example Input:**

```json
{
  "claim": {
    "text": "The Earth is approximately 4.54 billion years old",
    "domain": "science"
  },
  "evidence": [
    {
      "text": "Scientists have determined that the Earth is 4.54 billion years old with an error range of less than 1 percent.",
      "source": {
        "url": "https://example.edu/earth-age",
        "title": "Earth's Age: Scientific Consensus",
        "domain": "example.edu",
        "credibility": 0.95,
        "publication_date": "2022-03-15"
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
        "publication_date": "2021-08-22"
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
        "publication_date": "2020-11-05"
      },
      "relevance": 0.82,
      "stance": "contextual"
    }
  ],
  "config": {
    "verdict_scale": "five_point",
    "explanation_detail": "detailed",
    "include_confidence": true,
    "include_sources": true
  }
}
```

### Output

The VerdictWriter produces:

- A verdict object containing:
  - Truth rating (categorical or numerical)
  - Confidence score
  - Natural language explanation
  - Key evidence summary
  - Evidence citations
  - Alternative perspectives (when applicable)

**Example Output:**

```json
{
  "claim": "The Earth is approximately 4.54 billion years old",
  "verdict": "True",
  "confidence": 0.95,
  "explanation": "The claim that the Earth is approximately 4.54 billion years old is rated as TRUE with high confidence based on multiple reliable scientific sources. Radiometric dating of meteorites and Earth's oldest minerals consistently confirms this age with an uncertainty of less than 1%. This represents the scientific consensus based on decades of research in geology, physics, and astronomy. While some religious perspectives suggest a much younger Earth (around 6,000 years old), these views are not supported by scientific evidence and rely on different epistemological frameworks.",
  "evidence_summary": [
    "Scientific consensus places Earth's age at 4.54 billion years based on radiometric dating",
    "Multiple independent studies confirm this age with less than 1% uncertainty",
    "This dating method uses decay rates of radioactive isotopes in rocks and meteorites"
  ],
  "sources": [
    {
      "url": "https://example.edu/earth-age",
      "title": "Earth's Age: Scientific Consensus",
      "citation": "[1] Earth's Age: Scientific Consensus. Example University (2022). https://example.edu/earth-age"
    },
    {
      "url": "https://example.gov/geological-survey/earth-formation",
      "title": "Geological Survey: Earth Formation",
      "citation": "[2] Geological Survey: Earth Formation. Example Government Geological Survey (2021). https://example.gov/geological-survey/earth-formation"
    }
  ],
  "alternative_perspectives": [
    {
      "view": "Young Earth perspective",
      "description": "Some religious interpretations suggest an Earth age of approximately 6,000 years based on biblical chronology, though this view is not supported by scientific evidence.",
      "source": "https://example.org/science-religion-debate"
    }
  ],
  "metadata": {
    "evidence_count": 3,
    "supporting_evidence": 2,
    "contradicting_evidence": 0,
    "contextual_evidence": 1,
    "processing_time": "1.87s"
  }
}
```

## Implementation Details

### Models and Techniques

The VerdictWriter uses:

- Large Language Models for reasoning and explanation generation
- Evidence weighting algorithms based on source credibility and relevance
- Natural language generation with templates
- Structured output formatting
- Citation management systems

### Verdict Categories

The agent can use different verdict scales:

**Binary Scale:**

- True
- False

**Three-Point Scale:**

- True
- Partly True/False
- False

**Five-Point Scale:**

- True
- Mostly True
- Mixed
- Mostly False
- False

**Additional Categories:**

- Unverifiable
- Misleading
- Exaggerated
- Outdated

### Prompt Design

The agent uses a carefully crafted prompt to guide the LLM in verdict generation:

**Verdict Generation Prompt Template:**

```
You are a VerdictWriter agent tasked with determining the accuracy of a claim based on evidence.

CLAIM: {claim_text}

EVIDENCE:
{evidence_collection}

Analyze the evidence and determine a verdict for this claim. Follow these steps:

1. Assess the relevance and credibility of each evidence piece
2. Weigh supporting vs. contradicting evidence
3. Consider source credibility and recency
4. Determine a verdict: {verdict_scale_options}
5. Assign a confidence score (0-1)
6. Write a clear explanation with reasoning
7. Cite sources properly
8. Note any limitations or alternative perspectives

Your verdict should be fair, accurate, and based solely on the evidence provided.
Provide your response in the specified JSON format.
```

## Configuration Options

| Parameter              | Type    | Default       | Description                                                   |
| ---------------------- | ------- | ------------- | ------------------------------------------------------------- |
| verdict_scale          | string  | "three_point" | Verdict scale to use ("binary", "three_point", "five_point")  |
| explanation_detail     | string  | "standard"    | Level of explanation detail ("brief", "standard", "detailed") |
| include_confidence     | boolean | true          | Whether to include confidence scores                          |
| include_sources        | boolean | true          | Whether to include source citations                           |
| include_alternatives   | boolean | true          | Whether to include alternative perspectives                   |
| max_explanation_length | integer | 500           | Maximum length of explanation in characters                   |
| citation_style         | string  | "inline"      | Citation style ("inline", "footnote", "endnote")              |

## Limitations and Edge Cases

- May struggle with highly complex or interdisciplinary claims
- Cannot verify claims requiring specialized domain knowledge without sufficient evidence
- Confidence scores may be calibrated differently across domains
- Explanations may oversimplify complex scientific or technical concepts
- Cannot fully account for evolving truths in rapidly changing fields
- May have difficulty with claims containing ambiguous language or implicit assumptions

## Performance Metrics

| Metric                             | Target | Current |
| ---------------------------------- | ------ | ------- |
| Agreement with expert factcheckers | ≥80%   | 83%     |
| Explanation clarity rating         | ≥4/5   | 4.2/5   |
| Proper source citation rate        | ≥95%   | 97%     |
| Average processing time            | <3s    | 1.87s   |

## Example Usage

```python
from verifact.agents import VerdictWriter

writer = VerdictWriter(
    verdict_scale="five_point",
    explanation_detail="detailed",
    include_confidence=True,
    include_sources=True
)

claim = {
    "text": "The Earth is approximately 4.54 billion years old",
    "domain": "science"
}

evidence = [...] # Evidence collection from EvidenceHunter

verdict = writer.generate_verdict(claim, evidence)
print(f"Verdict: {verdict.verdict}")
print(f"Confidence: {verdict.confidence}")
print(f"Explanation: {verdict.explanation}")
print("\nSources:")
for i, source in enumerate(verdict.sources):
    print(f"{i+1}. {source.citation}")
```

## Future Improvements

- Improved reasoning about uncertainty and evidence gaps
- Better handling of conflicting evidence of similar credibility
- Enhanced explanation generation with user-appropriate language complexity
- Multimedia explanation capabilities with charts and visuals
- Dialogue-based verdict clarification
- Expert feedback incorporation for continuous improvement
