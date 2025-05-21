#!/usr/bin/env python3
"""Test script for VeriFact components with proper environment setup."""

import asyncio
import json
import os
import sys
import time
from pprint import pprint

# Import .env variables (if file exists)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("❌ python-dotenv not installed, skipping .env loading")

# Add the current directory to the Python path
sys.path.insert(0, ".")

# Set environment variables for testing
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"
os.environ["SUPABASE_DISABLE"] = "true"  # Disable real database connection
os.environ["REDIS_ENABLED"] = "false"   # Use in-memory cache

# Fix the logging issue - use standard logging instead of structured logger
os.environ["USE_STRUCTURED_LOGGING"] = "false"

# Configure logging for testing
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Hide noisy debug logs from external libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

class ComponentTester:
    """Tests individual components of the VeriFact system."""
    
    def __init__(self):
        self.results = {}
    
    async def test_claim_detector(self):
        """Test the ClaimDetector component."""
        print("\n=== Testing ClaimDetector ===")
        
        try:
            # Patch the logging to avoid the LogRecord error
            from src.utils.logging import structured_logger
            original_make_record = logging.Logger.makeRecord
            
            def patched_make_record(self, *args, **kwargs):
                if len(args) > 8:
                    args = args[:8]
                return original_make_record(self, *args, **kwargs)
            
            logging.Logger.makeRecord = patched_make_record
            
            from src.verifact_agents.claim_detector import ClaimDetector
            
            # Initialize with test configuration
            detector = ClaimDetector(min_check_worthiness=0.3, max_claims=3)
            
            test_text = "The Earth is round. The sun is hot. Climate change is caused by human activities."
            
            print(f"Detecting claims in: '{test_text}'")
            start_time = time.time()
            claims = await detector.detect_claims(test_text)
            duration = time.time() - start_time
            
            print(f"Found {len(claims)} claims in {duration:.2f} seconds:")
            
            for i, claim in enumerate(claims):
                print(f"\nClaim {i+1}:")
                print(f"  Text: {claim.text}")
                print(f"  Check-worthiness: {getattr(claim, 'check_worthiness', getattr(claim, 'checkworthy', 'N/A'))}")
                if hasattr(claim, 'domain'):
                    print(f"  Domain: {claim.domain}")
                    
            self.results["claim_detector"] = {
                "success": True,
                "claims_detected": len(claims),
                "duration": duration
            }
            
            # Return first claim for subsequent tests
            return claims[0] if claims else None
            
        except Exception as e:
            print(f"❌ Error in ClaimDetector: {e}")
            import traceback
            traceback.print_exc()
            self.results["claim_detector"] = {
                "success": False,
                "error": str(e)
            }
            return None
    
    async def test_evidence_hunter(self, claim=None):
        """Test the EvidenceHunter component."""
        print("\n=== Testing EvidenceHunter ===")
        
        try:
            from src.verifact_agents.evidence_hunter import EvidenceHunter
            from src.verifact_agents.claim_detector.detector import Claim
            from src.verifact_agents.claim_detector.models import ClaimDomain
            
            # Create a test claim if none provided
            if claim is None:
                claim = Claim(
                    text="The Earth is approximately 4.54 billion years old",
                    original_text="The Earth is approximately 4.54 billion years old",
                    normalized_text="The Earth is approximately 4.54 billion years old",
                    check_worthiness=0.9,
                    specificity_score=0.8,
                    public_interest_score=0.7,
                    impact_score=0.6,
                    confidence=0.95,
                    domain=ClaimDomain.SCIENCE,
                    entities=[],
                    rank=1
                )
            
            # Initialize with test configuration
            hunter = EvidenceHunter()
            
            print(f"Gathering evidence for claim: '{claim.text}'")
            start_time = time.time()
            evidence = await hunter.gather_evidence(claim)
            duration = time.time() - start_time
            
            print(f"Found {len(evidence)} pieces of evidence in {duration:.2f} seconds:")
            
            for i, evidence_item in enumerate(evidence[:3]):  # Show first 3 items
                print(f"\nEvidence {i+1}:")
                print(f"  Source: {getattr(evidence_item, 'source', 'N/A')}")
                print(f"  Stance: {getattr(evidence_item, 'stance', 'N/A')}")
                
                # Get content (might be 'content' or 'text' attribute)
                content = getattr(evidence_item, 'content', getattr(evidence_item, 'text', 'N/A'))
                print(f"  Content: {content[:100]}..." if len(content) > 100 else f"  Content: {content}")
                
            self.results["evidence_hunter"] = {
                "success": True,
                "evidence_found": len(evidence),
                "duration": duration
            }
            
            return evidence
            
        except Exception as e:
            print(f"❌ Error in EvidenceHunter: {e}")
            import traceback
            traceback.print_exc()
            self.results["evidence_hunter"] = {
                "success": False,
                "error": str(e)
            }
            return []
    
    async def test_verdict_writer(self, claim=None, evidence=None):
        """Test the VerdictWriter component."""
        print("\n=== Testing VerdictWriter ===")
        
        try:
            from src.verifact_agents.verdict_writer import VerdictWriter
            from src.verifact_agents.claim_detector.detector import Claim
            from src.verifact_agents.claim_detector.models import ClaimDomain
            from src.verifact_agents.evidence_hunter.hunter import Evidence
            
            # Create test data if not provided
            if claim is None:
                claim = Claim(
                    text="The Earth is approximately 4.54 billion years old",
                    original_text="The Earth is approximately 4.54 billion years old",
                    normalized_text="The Earth is approximately 4.54 billion years old",
                    check_worthiness=0.9,
                    specificity_score=0.8,
                    public_interest_score=0.7,
                    impact_score=0.6,
                    confidence=0.95,
                    domain=ClaimDomain.SCIENCE,
                    entities=[],
                    rank=1
                )
                
            if not evidence:
                evidence = [
                    Evidence(
                        content="Scientists have determined that the Earth is 4.54 billion years old with an error range of less than 1 percent.",
                        source="https://example.edu/earth-age",
                        relevance=0.95,
                        stance="supporting"
                    ),
                    Evidence(
                        content="Based on radiometric dating of meteorites, the age of Earth is estimated to be around 4.54 billion years.",
                        source="https://example.gov/earth-science",
                        relevance=0.93,
                        stance="supporting"
                    )
                ]
            
            # Initialize with test configuration
            writer = VerdictWriter()
            
            print(f"Generating verdict for claim: '{claim.text}'")
            start_time = time.time()
            verdict = await writer.generate_verdict(claim, evidence)
            duration = time.time() - start_time
            
            print(f"Verdict generated in {duration:.2f} seconds:")
            print(f"  Verdict: {verdict.verdict}")
            print(f"  Confidence: {verdict.confidence}")
            print(f"  Explanation: {verdict.explanation[:200]}..." if len(verdict.explanation) > 200 else f"  Explanation: {verdict.explanation}")
            print(f"  Sources: {verdict.sources}")
            
            self.results["verdict_writer"] = {
                "success": True,
                "verdict": verdict.verdict,
                "confidence": verdict.confidence,
                "duration": duration
            }
            
            return verdict
            
        except Exception as e:
            print(f"❌ Error in VerdictWriter: {e}")
            import traceback
            traceback.print_exc()
            self.results["verdict_writer"] = {
                "success": False,
                "error": str(e)
            }
            return None
    
    async def test_pipeline(self):
        """Test the complete pipeline."""
        print("\n=== Testing Complete Pipeline ===")
        
        try:
            from src.pipeline.factcheck_pipeline import create_default_pipeline, PipelineConfig
            
            # Create a pipeline with default configuration
            config = PipelineConfig()
            pipeline = create_default_pipeline(config=config)
            
            test_text = "The Earth is approximately 4.54 billion years old. Water covers about 71% of the Earth's surface."
            
            print(f"Processing text through pipeline: '{test_text}'")
            start_time = time.time()
            results = await pipeline.process_text(test_text)
            duration = time.time() - start_time
            
            print(f"Pipeline processed {len(results)} claims in {duration:.2f} seconds:")
            
            for i, result in enumerate(results):
                print(f"\nResult {i+1}:")
                print(f"  Claim: {result['claim']['text'] if 'claim' in result and 'text' in result['claim'] else 'Unknown'}")
                print(f"  Verdict: {result['verdict'] if 'verdict' in result else 'Unknown'}")
                print(f"  Confidence: {result['confidence'] if 'confidence' in result else 'Unknown'}")
                print(f"  Evidence: {len(result['evidence']) if 'evidence' in result else 0} pieces")
            
            self.results["pipeline"] = {
                "success": True,
                "claims_processed": len(results),
                "duration": duration
            }
            
        except Exception as e:
            print(f"❌ Error in Pipeline: {e}")
            import traceback
            traceback.print_exc()
            self.results["pipeline"] = {
                "success": False,
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all component tests in sequence."""
        claim = await self.test_claim_detector()
        evidence = await self.test_evidence_hunter(claim)
        await self.test_verdict_writer(claim, evidence)
        await self.test_pipeline()
        
        print("\n=== Test Results Summary ===")
        for component, result in self.results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            print(f"{component}: {status}")
            if not result.get("success", False):
                print(f"  Error: {result.get('error', 'Unknown error')}")

async def main():
    """Run the test script."""
    print("\n=== VeriFact Component Tests ===")
    tester = ComponentTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
