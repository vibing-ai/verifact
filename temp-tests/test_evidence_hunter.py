#!/usr/bin/env python3
"""Simple test for EvidenceHunter component."""

import asyncio
import sys
from pprint import pprint

# Add the current directory to the Python path
sys.path.insert(0, ".")

async def test_evidence_hunter():
    """Test the EvidenceHunter component."""
    print("Importing required components...")
    try:
        from src.verifact_agents.claim_detector.detector import Claim
        from src.verifact_agents.evidence_hunter import EvidenceHunter
        print("Successfully imported EvidenceHunter and dependencies")
    except ImportError as e:
        print(f"Failed to import components: {e}")
        return
    
    print("\nInitializing EvidenceHunter...")
    try:
        hunter = EvidenceHunter()
        print("Successfully initialized EvidenceHunter")
    except Exception as e:
        print(f"Failed to initialize EvidenceHunter: {e}")
        return
    
    # Create a simple test claim
    test_claim = Claim(
        text="The Earth is approximately 4.54 billion years old",
        checkworthy=True
    )
    
    print(f"\nGathering evidence for claim: '{test_claim.text}'")
    try:
        start_time = asyncio.get_event_loop().time()
        evidence = await hunter.gather_evidence(test_claim)
        end_time = asyncio.get_event_loop().time()
        
        print(f"\nFound {len(evidence)} pieces of evidence in {end_time - start_time:.2f} seconds:")
        
        for i, evidence_item in enumerate(evidence):
            print(f"\nEvidence {i+1}:")
            print(f"  Source: {getattr(evidence_item, 'source', 'N/A')}")
            print(f"  Stance: {getattr(evidence_item, 'stance', 'N/A')}")
            print(f"  Relevance: {getattr(evidence_item, 'relevance', 'N/A')}")
            
            # Get the content attribute (might be 'content' or 'text' depending on implementation)
            content = getattr(evidence_item, 'content', getattr(evidence_item, 'text', 'N/A'))
            
            # Show a preview of the content
            print(f"  Content: {content[:200]}..." if len(content) > 200 else f"  Content: {content}")
            
    except Exception as e:
        print(f"Error gathering evidence: {e}")

def test_evidence_hunter_import():
    """Test that the evidence hunter module can be imported."""
    import src.verifact_agents.evidence_hunter
    assert src.verifact_agents.evidence_hunter is not None

if __name__ == "__main__":
    asyncio.run(test_evidence_hunter()) 