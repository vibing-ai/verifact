"""
Example of migrating from the old agent architecture to the new one.

This script demonstrates how to transition from the legacy implementation
to the new architecture with proper separation of concerns.
"""

import asyncio
from typing import List, Dict, Any

# Import from legacy implementations
from src.agents.claim_detector.models import Claim as LegacyClaim
from src.agents.evidence_hunter.hunter import Evidence as LegacyEvidence, EvidenceHunter as LegacyEvidenceHunter
from src.agents.verdict_writer.writer import Verdict as LegacyVerdict, VerdictWriter as LegacyVerdictWriter

# Import from new implementations
from src.agents.dto import Claim, Evidence, Verdict, DTOFactory
from src.agents.factory import AgentFactory
from src.agents.orchestrator import FactcheckPipeline
from src.agents.transition import (
    adapt_claim_detector, adapt_evidence_hunter, adapt_verdict_writer,
    convert_to_legacy_claim, convert_to_legacy_evidence, convert_to_legacy_verdict
)


async def legacy_workflow():
    """Example of a workflow using the legacy architecture."""
    print("=== Legacy Workflow ===")
    
    # Create agent instances directly (tight coupling)
    evidence_hunter = LegacyEvidenceHunter()
    verdict_writer = LegacyVerdictWriter()
    
    # Sample claim in legacy format
    legacy_claim = LegacyClaim(
        text="The Earth is flat",
        original_text="The Earth is flat",
        check_worthiness=0.9,
        confidence=0.8
    )
    
    # Process the claim with direct agent calls
    print("Processing legacy claim:", legacy_claim.text)
    
    # Gather evidence
    evidence = await evidence_hunter.gather_evidence(legacy_claim)
    print(f"Found {len(evidence)} pieces of evidence.")
    
    # Generate verdict
    verdict = await verdict_writer.generate_verdict(
        legacy_claim, evidence, explanation_detail="standard"
    )
    
    # Print the result
    print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.2f})")
    print(f"Explanation: {verdict.explanation[:150]}...")


async def transition_workflow():
    """Example of a transitional workflow mixing legacy and new components."""
    print("\n=== Transition Workflow ===")
    
    # Create a legacy evidence hunter and wrap it with the adapter
    legacy_evidence_hunter = LegacyEvidenceHunter()
    adapted_evidence_hunter = adapt_evidence_hunter(legacy_evidence_hunter)
    
    # Create a legacy verdict writer and wrap it with the adapter
    legacy_verdict_writer = LegacyVerdictWriter()
    adapted_verdict_writer = adapt_verdict_writer(legacy_verdict_writer)
    
    # Create a new claim detector using the factory
    claim_detector = AgentFactory.create_claim_detector()
    
    # Sample text to process
    text = "The Earth is flat according to some conspiracy theorists."
    
    print("Processing text:", text)
    
    # 1. Use the new claim detector
    claims = await claim_detector.detect_claims(text, min_check_worthiness=0.5)
    if not claims:
        print("No claims detected.")
        return
    
    claim = claims[0]
    print(f"Detected claim: {claim.text}")
    
    # 2. Use the adapted legacy evidence hunter
    evidence = await adapted_evidence_hunter.gather_evidence(claim)
    print(f"Found {len(evidence)} pieces of evidence.")
    
    # 3. Use the adapted legacy verdict writer
    verdict = await adapted_verdict_writer.generate_verdict(claim, evidence)
    
    # Print the result
    print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.2f})")
    print(f"Explanation: {verdict.explanation[:150]}...")


async def mixed_pipeline_workflow():
    """Example of using the new pipeline with adapted legacy components."""
    print("\n=== Mixed Pipeline Workflow ===")
    
    # Create a mix of new and legacy components
    claim_detector = AgentFactory.create_claim_detector()
    
    legacy_evidence_hunter = LegacyEvidenceHunter()
    adapted_evidence_hunter = adapt_evidence_hunter(legacy_evidence_hunter)
    
    legacy_verdict_writer = LegacyVerdictWriter()
    adapted_verdict_writer = adapt_verdict_writer(legacy_verdict_writer)
    
    # Create a pipeline with the mixed components
    pipeline = FactcheckPipeline(
        claim_detector=claim_detector,
        evidence_hunter=adapted_evidence_hunter,
        verdict_writer=adapted_verdict_writer,
        min_check_worthiness=0.5,
        max_claims=3
    )
    
    # Sample text to process
    text = """
    The Earth is flat and this has been proven by multiple scientific experiments.
    The COVID-19 vaccine contains microchips that allow the government to track people.
    """
    
    print("Processing text through mixed pipeline...")
    
    # Process the text through the pipeline
    verdicts = await pipeline.process_text(text)
    
    # Print the results
    print(f"Generated {len(verdicts)} verdicts:")
    for i, verdict in enumerate(verdicts, 1):
        print(f"\n--- Verdict {i} ---")
        print(f"Claim: {verdict.claim}")
        print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.2f})")
        print(f"Explanation: {verdict.explanation[:150]}...")


async def fully_migrated_workflow():
    """Example of a fully migrated workflow using the new architecture."""
    print("\n=== Fully Migrated Workflow ===")
    
    # Define configuration for the pipeline and its agents
    config: Dict[str, Any] = {
        "parallelism": 3,
        "min_check_worthiness": 0.6,
        "max_claims": 2,
        "claim_detector": {},
        "evidence_hunter": {},
        "verdict_writer": {
            "explanation_detail": "detailed"
        }
    }
    
    # Create the fully migrated pipeline using the factory
    from src.agents.orchestrator import FactcheckPipelineFactory
    pipeline = FactcheckPipelineFactory.create_pipeline(config)
    
    # Sample text to factcheck
    text = "Vaccines cause autism according to several studies."
    
    print("Processing text through fully migrated pipeline...")
    
    # Process the text through the pipeline
    verdicts = await pipeline.process_text(text)
    
    # Print the results
    print(f"Generated {len(verdicts)} verdicts:")
    for i, verdict in enumerate(verdicts, 1):
        print(f"\n--- Verdict {i} ---")
        print(f"Claim: {verdict.claim}")
        print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.2f})")
        print(f"Explanation: {verdict.explanation[:150]}...")


async def main():
    """Run all example workflows."""
    # 1. Legacy workflow - old architecture
    await legacy_workflow()
    
    # 2. Transition workflow - mix of old and new components
    await transition_workflow()
    
    # 3. Mixed pipeline workflow - new pipeline with adapted legacy components
    await mixed_pipeline_workflow()
    
    # 4. Fully migrated workflow - entirely new architecture
    await fully_migrated_workflow()
    
    print("\nMigration progression complete!")


if __name__ == "__main__":
    asyncio.run(main()) 