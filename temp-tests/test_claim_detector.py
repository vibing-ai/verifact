#!/usr/bin/env python3
"""Simple test for ClaimDetector component."""

import asyncio
import sys
from pprint import pprint
import pytest
from src.verifact_agents.claim_detector.detector import ClaimDetector
from unittest.mock import patch, MagicMock

# Add the current directory to the Python path
sys.path.insert(0, ".")

async def test_claim_detector():
    """Test the ClaimDetector component."""
    print("Importing ClaimDetector...")
    try:
        from src.verifact_agents.claim_detector import ClaimDetector
        print("Successfully imported ClaimDetector")
    except ImportError as e:
        print(f"Failed to import ClaimDetector: {e}")
        return
    
    print("\nInitializing ClaimDetector...")
    try:
        detector = ClaimDetector()
        print("Successfully initialized ClaimDetector")
    except Exception as e:
        print(f"Failed to initialize ClaimDetector: {e}")
        return
    
    test_text = "The Earth is round. The sun is hot. Climate change is caused by human activities."
    
    print(f"\nDetecting claims in: '{test_text}'")
    try:
        start_time = asyncio.get_event_loop().time()
        claims = await detector.detect_claims(test_text)
        end_time = asyncio.get_event_loop().time()
        
        print(f"\nFound {len(claims)} claims in {end_time - start_time:.2f} seconds:")
        
        for i, claim in enumerate(claims):
            print(f"\nClaim {i+1}:")
            print(f"  Text: {claim.text}")
            print(f"  Check-worthiness: {getattr(claim, 'check_worthiness', getattr(claim, 'checkworthy', 'N/A'))}")
            if hasattr(claim, 'domain'):
                print(f"  Domain: {claim.domain}")
            if hasattr(claim, 'confidence'):
                print(f"  Confidence: {claim.confidence}")
            if hasattr(claim, 'entities') and claim.entities:
                print(f"  Entities: {len(claim.entities)}")
                for entity in claim.entities[:3]:  # Show first 3 entities
                    print(f"    - {entity.text} ({entity.type})")
    except Exception as e:
        print(f"Error detecting claims: {e}")

@patch('src.utils.model_config.ModelManager')
@patch('src.utils.logging.structured_logger.get_structured_logger')
def test_initialization(mock_get_logger, mock_model_manager):
    """Test that the claim detector can be imported and mocked."""
    # Setup the mocks
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    mock_model_manager.return_value.model_name = "gpt-4"
    
    # Import the class inside the test to avoid import errors during collection
    from src.verifact_agents.claim_detector.detector import ClaimDetector
    
    # Create the detector with the mocked dependencies
    detector = ClaimDetector()
    
    # Verify it was created successfully
    assert detector is not None
    # Check that logging was set up
    assert mock_get_logger.called

def test_claim_detector_import():
    """Test that the claim detector module can be imported."""
    import src.verifact_agents.claim_detector
    assert src.verifact_agents.claim_detector is not None

if __name__ == "__main__":
    asyncio.run(test_claim_detector()) 