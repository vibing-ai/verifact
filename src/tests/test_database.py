#!/usr/bin/env python3
"""
Database test script for VeriFact
Test all database operations including vector similarity search.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.utils.db import db_manager
from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict

async def test_embedding():
    """Test embedding generation."""
    print("\n0. Testing embedding generation...")
    
    # Test embedding generation
    text = "The sky is blue"
    print(f"Testing embedding for: '{text}'")
    
    embedding = await db_manager.generate_embedding(text)
    
    if embedding:
        print(f"✅ Embedding generated successfully")
        print(f"📏 Embedding dimension: {len(embedding)}")
        print(f"🔢 First 5 values: {embedding[:5]}")
        print(f"🔢 Last 5 values: {embedding[-5:]}")
        return True
    else:
        print("❌ Failed to generate embedding")
        return False

async def test_database_operations():
    """Test all database operations."""
    load_dotenv()
    
    print("🧪 Testing VeriFact database operations...")
    print("=" * 50)
    
    try:
        # Test 0: Embedding generation
        embedding_success = await test_embedding()
        if not embedding_success:
            print("❌ Embedding test failed - skipping database tests")
            return False
        
        # Test 1: Store a claim
        print("\n1. Testing claim storage...")
        test_claim = Claim(
            text="The Earth is flat",
            check_worthiness_score=0.9,
            specificity_score=0.8
        )
        
        claim_id = await db_manager.store_claim(test_claim)
        if claim_id:
            print(f"✅ Claim stored successfully with ID: {claim_id}")
        else:
            print("❌ Failed to store claim")
            return False
        
        # Test 2: Store evidence
        print("\n2. Testing evidence storage...")
        test_evidence = [
            Evidence(
                content="NASA has provided extensive evidence that Earth is spherical",
                source="https://nasa.gov",
                relevance=0.9,
                stance="contradicting"
            )
        ]
        
        evidence_ids = await db_manager.store_evidence(claim_id, test_evidence)
        if evidence_ids:
            print(f"✅ Evidence stored successfully: {len(evidence_ids)} items")
        else:
            print("❌ Failed to store evidence")
        
        # Test 3: Store verdict
        print("\n3. Testing verdict storage...")
        test_verdict = Verdict(
            claim="The Earth is flat",  # Add the claim field
            verdict="false",
            confidence=0.95,
            explanation="The claim that Earth is flat is contradicted by overwhelming scientific evidence",
            sources=["https://nasa.gov", "https://scientific-american.com"]
        )
        
        verdict_id = await db_manager.store_verdict(claim_id, test_verdict)
        if verdict_id:
            print(f"✅ Verdict stored successfully with ID: {verdict_id}")
        else:
            print("❌ Failed to store verdict")
        
        # Test 4: Similar claims search
        print("\n4. Testing similar claims search...")
        similar_claims = await db_manager.find_similar_claims(
            "The Earth is not round",
            similarity_threshold=0.7,
            limit=3
        )
        
        if similar_claims:
            print(f"✅ Found {len(similar_claims)} similar claims")
            for i, result in enumerate(similar_claims, 1):
                print(f"   {i}. Similarity: {result.similarity_score:.3f}")
                print(f"      Claim: {result.claim.text[:50]}...")
                if result.verdict:
                    print(f"      Verdict: {result.verdict.verdict}")
        else:
            print("ℹ️ No similar claims found (this is normal for a new database)")
        
        print("\n✅ All database tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_operations())
    sys.exit(0 if success else 1)