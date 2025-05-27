"""
Basic pipeline execution:
uses monkeypatched agents (claim_detector_agent, evidence_hunter_agent, verdict_writer_agent) and Runner.run()
instead of real agents.

1. Testing if the full VerifactManager.run() pipeline executes successfully with mocked agents.
2. Testing if a claim goes through detection, evidence gathering, and verdict generation using mocked data
with a range of verdict cases: "false", "partially true", "unverifiable", and "true".
a. The verdict text returned matches the expected result.
b. The sources in the verdict match the mock evidence source.
c. The evidence content and source returned from the mock agent match what was injected

"""
import pytest
from tests.mocks.mock_agents import MockAgent
from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict

@pytest.mark.asyncio
@pytest.mark.parametrize("claim_text, verdict_text, evidence_content, evidence_source", [
    (
        "The moon is made of cheese",
        "false",
        "Scientific consensus disproves this",
        "https://nasa.gov"
    ),
    (
        "The Great Wall of China is visible from space",
        "partially true",
        "Astronauts report visibility depends on conditions",
        "https://esa.int"
    ),
    (
        "Aliens built the pyramids",
        "unverifiable",
        "There is no direct evidence confirming or denying alien involvement",
        "https://historychannel.com"
    ),
    (
        "Water boils at 100 degrees Celsius at sea level",
        "true",
        "This is a well-documented scientific fact",
        "https://science.org"
    ),
])
async def test_factcheck_pipeline(monkeypatch, claim_text, verdict_text, evidence_content, evidence_source):
    # Prepare mock data
    claims = [Claim(text=claim_text)]
    evidence = [Evidence(content=evidence_content, source=evidence_source, relevance=0.9, stance="neutral")]
    verdict = Verdict(
        claim=claim_text,
        verdict=verdict_text,
        confidence=0.85,
        explanation=f"Mock explanation for verdict '{verdict_text}'.",
        sources=[evidence_source]
    )

    # Patch agent instances
    monkeypatch.setattr("src.verifact_manager.claim_detector_agent", MockAgent(claims))
    monkeypatch.setattr("src.verifact_manager.evidence_hunter_agent", MockAgent(evidence))
    monkeypatch.setattr("src.verifact_manager.verdict_writer_agent", MockAgent(verdict))

    # Import manager after monkeypatching
    import src.verifact_manager as vm

    # Patch Runner.run
    async def mock_runner_run(agent, input_data):
        return await agent.process(input_data)

    monkeypatch.setattr(vm.Runner, "run", mock_runner_run)

    # Run pipeline
    manager = vm.VerifactManager()
    result = await manager.run(claim_text)

    evidence_result, verdict_result = result[0]

    # Verdict checks
    assert verdict_result.verdict == verdict_text
    assert evidence_source in verdict_result.sources

    # Evidence checks
    assert evidence_result is not None
    assert len(evidence_result) > 0
    assert evidence_result[0].content == evidence_content
    assert evidence_result[0].source == evidence_source
