import pytest
from src.verifact_agents.verdict_writer import VerdictWriter, Verdict

@pytest.mark.asyncio
async def test_verdict_writer_returns_valid_verdict():
    writer = VerdictWriter()
    claim = "Bananas are a good source of potassium."
    evidence = [
        {
            "content": "Bananas contain around 422 mg of potassium per medium fruit, making them a good dietary source.",
            "source": "Healthline",
            "relevance": 0.9,
            "stance": "supporting"
        },
        {
            "content": "Potatoes and beans contain more potassium than bananas, but bananas are still a decent source.",
            "source": "Harvard School of Public Health",
            "relevance": 0.8,
            "stance": "neutral"
        }
    ]

    verdict = await writer.run(claim=claim, evidence=evidence, detail_level="standard")

    assert isinstance(verdict, Verdict)
    assert verdict.claim == claim
    assert verdict.verdict in ["true", "false", "partially true", "unverifiable"]
    assert 0.0 <= verdict.confidence <= 1.0
    assert isinstance(verdict.explanation, str) and len(verdict.explanation.strip()) > 0
    assert isinstance(verdict.sources, list) and all(isinstance(s, str) for s in verdict.sources)
    assert len(verdict.sources) > 0

@pytest.mark.asyncio
async def test_verdict_writer_brief_detail():
    writer = VerdictWriter()
    claim = "Water freezes at 0 degrees Celsius."
    evidence = [
        {
            "content": "Under standard atmospheric conditions, water freezes at 0°C.",
            "source": "Britannica",
            "relevance": 0.95,
            "stance": "supporting"
        }
    ]

    verdict = await writer.run(claim=claim, evidence=evidence, detail_level="brief")

    assert isinstance(verdict.explanation, str)
    assert len(verdict.explanation.split()) <= 30  # brief explanation is usually short

@pytest.mark.asyncio
async def test_verdict_writer_detailed_includes_sources():
    writer = VerdictWriter()
    claim = "The Earth revolves around the Sun."
    evidence = [
        {
            "content": "Astronomical evidence and observations confirm the heliocentric model.",
            "source": "NASA",
            "relevance": 0.99,
            "stance": "supporting"
        }
    ]

    verdict = await writer.run(claim=claim, evidence=evidence, detail_level="detailed")

    assert any(source.lower().startswith("http") == False for source in verdict.sources)
    assert "nasa" in " ".join(verdict.sources).lower()
    assert "sun" in verdict.explanation.lower() or "earth" in verdict.explanation.lower()

@pytest.mark.asyncio
async def test_confidence_score_considers_evidence_relevance():
    writer = VerdictWriter()
    claim = "Cats are better pets than dogs."
    evidence = [
        {"content": "Cats require less maintenance.", "source": "PetGuide", "relevance": 0.9, "stance": "supporting"},
        {"content": "Dogs are more loyal and emotionally supportive.", "source": "DogWorld", "relevance": 0.85, "stance": "contradicting"},
    ]
    verdict = await writer.run(claim=claim, evidence=evidence, detail_level="standard")
    assert 0.4 <= verdict.confidence <= 0.6  # Mixed evidence should yield moderate confidence

@pytest.mark.asyncio
async def test_explanation_maintains_political_neutrality():
    writer = VerdictWriter()
    claim = "Voter ID laws reduce election fraud."
    evidence = [
        {"content": "Some studies suggest voter ID laws deter fraud.", "source": "Heritage Foundation", "relevance": 0.8, "stance": "supporting"},
        {"content": "Other studies show minimal fraud cases regardless of ID laws.", "source": "Brennan Center", "relevance": 0.9, "stance": "contradicting"},
    ]
    verdict = await writer.run(claim=claim, evidence=evidence, detail_level="detailed")
    explanation = verdict.explanation.lower()
    assert "republican" not in explanation
    assert "democrat" not in explanation
    assert "bias" not in explanation

@pytest.mark.asyncio
async def test_alternative_perspectives_are_included():
    writer = VerdictWriter()
    claim = "Electric cars are better for the environment."
    evidence = [
        {"content": "EVs emit less CO2 over their lifetime.", "source": "EPA", "relevance": 0.9, "stance": "supporting"},
        {"content": "Battery production has environmental impacts.", "source": "Nature", "relevance": 0.8, "stance": "contradicting"},
    ]
    verdict = await writer.run(claim=claim, evidence=evidence, detail_level="detailed")
    explanation = verdict.explanation.lower()
    assert "battery" in explanation or "production" in explanation
    assert any(term in explanation for term in ["emissions", "co2", "co₂", "co 2"])

@pytest.mark.asyncio
async def test_explanation_detail_levels_vary():
    writer = VerdictWriter()
    claim = "Electric cars are better for the environment than gas cars."
    evidence = [
        {
            "content": "Electric vehicles produce fewer greenhouse gas emissions over their lifetime.",
            "source": "EPA",
            "relevance": 0.95,
            "stance": "supporting"
        },
        {
            "content": "Battery production for electric vehicles involves mining and emissions.",
            "source": "Nature",
            "relevance": 0.8,
            "stance": "contradicting"
        }
    ]

    brief = await writer.run(claim=claim, evidence=evidence, detail_level="brief")
    standard = await writer.run(claim=claim, evidence=evidence, detail_level="standard")
    detailed = await writer.run(claim=claim, evidence=evidence, detail_level="detailed")

    # Ensure increasing richness in explanation
    assert len(brief.explanation.split()) < len(standard.explanation.split()) < len(detailed.explanation.split())

    # Optional: Check sources and content presence in detailed output
    assert len(detailed.sources) >= 2
    explanation = detailed.explanation.lower()
    assert "battery" in explanation
    assert "emissions" in explanation or "co2" in explanation 