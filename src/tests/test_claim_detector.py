import asyncio
from pprint import pprint
from verifact_agents.claim_detector import process_claims, Claim

# Sample text to test claim detection
SAMPLE_TEXT = """
The Earth is round.
"""

def format_claim(claim: Claim) -> dict:
    """Format a claim object for pretty printing."""
    return {
        "text": claim.text,
        "domain": claim.domain,
        "scores": {
            "check_worthiness": f"{claim.check_worthiness:.2f}",
            "specificity": f"{claim.specificity_score:.2f}",
            "public_interest": f"{claim.public_interest_score:.2f}",
            "impact": f"{claim.impact_score:.2f}",
            "confidence": f"{claim.confidence:.2f}"
        },
        "entities": claim.entities
    }

async def test_claim_detection():
    """Test the claim detection functionality with a sample text."""
    print("\n=== Testing Claim Detection ===\n")
    print(f"Input Text:\n{SAMPLE_TEXT}\n")
    
    try:
        # Directly use process_claims to test the core functionality
        claims = await process_claims(SAMPLE_TEXT)
        print(f"Number of claims detected: {len(claims)}\n")
        
        for i, claim in enumerate(claims, 1):
            print(f"Claim {i}:")
            pprint(format_claim(claim), indent=2, width=100)
            print("\n" + "-"*80 + "\n")
            
    except Exception as e:
        print(f"Error processing text: {str(e)}\n")

if __name__ == "__main__":
    asyncio.run(test_claim_detection())