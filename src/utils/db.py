import os
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging
from datetime import datetime
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from openai import OpenAI
from pydantic import BaseModel

# Import your existing models
from src.verifact_agents.claim_detector import Claim as AgentClaim
from src.verifact_agents.evidence_hunter import Evidence as AgentEvidence
from src.verifact_agents.verdict_writer import Verdict as AgentVerdict

logger = logging.getLogger(__name__)

# Database Models
class DBClaim(BaseModel):
    id: Optional[UUID] = None
    text: str
    embedding: Optional[List[float]] = None
    context: Optional[str] = None
    check_worthiness_score: Optional[float] = None
    specificity_score: Optional[float] = None
    public_interest_score: Optional[float] = None
    impact_score: Optional[float] = None
    domain: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DBEvidence(BaseModel):
    id: Optional[UUID] = None
    claim_id: UUID
    content: str
    source_url: str
    relevance_score: float
    stance: str
    credibility_score: Optional[float] = None
    created_at: Optional[datetime] = None

class DBVerdict(BaseModel):
    id: Optional[UUID] = None
    claim_id: UUID
    verdict: str
    confidence_score: float
    explanation: str
    sources: List[str]
    created_at: Optional[datetime] = None

class SimilarClaimResult(BaseModel):
    """Result of similarity search with claim and verdict info"""
    claim: DBClaim
    verdict: Optional[DBVerdict]
    similarity_score: float

class DatabaseManager:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        # Initialize Supabase client
        options = ClientOptions(
            schema="public",
            headers={"X-Client-Info": "verifact/1.0.0"}
        )
        self.supabase: Client = create_client(
            self.supabase_url, 
            self.supabase_key,
            options=options
        )
        
        # Initialize OpenAI client for embeddings
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        else:
            logger.warning("OPENAI_API_KEY not set. Vector search will be disabled.")
            self.openai_client = None
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI."""
        if not self.openai_api_key:
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def store_claim(self, claim: AgentClaim) -> Optional[UUID]:
        """Store a claim with its embedding."""
        try:
            # Generate embedding
            embedding = await self.generate_embedding(claim.text)
            
            # Prepare claim data
            claim_data = {
                "text": claim.text,
                "embedding": embedding,
                "context": getattr(claim, 'context', None),
                "check_worthiness_score": getattr(claim, 'check_worthiness_score', None),
                "specificity_score": getattr(claim, 'specificity_score', None),
                "public_interest_score": getattr(claim, 'public_interest_score', None),
                "impact_score": getattr(claim, 'impact_score', None),
                "domain": getattr(claim, 'domain', None),
                "entities": getattr(claim, 'entities', None)
            }
            
            # Remove None values
            claim_data = {k: v for k, v in claim_data.items() if v is not None}
            
            response = self.supabase.table("claims").insert(claim_data).execute()
            
            if response.data:
                return response.data[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error storing claim: {e}")
            return None
    
    async def store_evidence(self, claim_id: UUID, evidence_list: List[AgentEvidence]) -> List[UUID]:
        """Store evidence for a claim."""
        evidence_ids = []
        
        try:
            for evidence in evidence_list:
                evidence_data = {
                    "claim_id": str(claim_id),
                    "content": evidence.content,
                    "source_url": evidence.source,
                    "relevance_score": evidence.relevance,
                    "stance": evidence.stance,
                    "credibility_score": getattr(evidence, 'credibility_score', None)
                }
                
                response = self.supabase.table("evidence").insert(evidence_data).execute()
                
                if response.data:
                    evidence_ids.append(response.data[0]['id'])
                    
        except Exception as e:
            logger.error(f"Error storing evidence: {e}")
        
        return evidence_ids
    
    async def store_verdict(self, claim_id: UUID, verdict: AgentVerdict) -> Optional[UUID]:
        """Store a verdict for a claim."""
        try:
            verdict_data = {
                "claim_id": str(claim_id),
                "verdict": verdict.verdict,
                "confidence_score": verdict.confidence,
                "explanation": verdict.explanation,
                "sources": verdict.sources
            }
            
            response = self.supabase.table("verdicts").insert(verdict_data).execute()
            
            if response.data:
                return response.data[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error storing verdict: {e}")
            return None
    
    async def find_similar_claims(self, claim_text: str, similarity_threshold: float = 0.8, limit: int = 5) -> List[SimilarClaimResult]:
        """Find similar claims with their verdicts using vector similarity search."""
        try:
            # Generate embedding for the query
            query_embedding = await self.generate_embedding(claim_text)
            
            if not query_embedding:
                logger.warning("Could not generate embedding for similarity search")
                return []
            
            # Perform vector similarity search
            response = self.supabase.rpc(
                'match_claims_with_verdicts',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': similarity_threshold,
                    'match_count': limit
                }
            ).execute()
            
            similar_claims = []
            
            for result in response.data:
                claim = DBClaim(**result['claim'])
                verdict = DBVerdict(**result['verdict']) if result.get('verdict') else None
                similarity_score = result.get('similarity', 0.0)
                
                similar_claims.append(SimilarClaimResult(
                    claim=claim,
                    verdict=verdict,
                    similarity_score=similarity_score
                ))
            
            return similar_claims
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    async def get_claim_with_evidence_and_verdict(self, claim_id: UUID) -> Optional[Tuple[DBClaim, List[DBEvidence], Optional[DBVerdict]]]:
        """Get a complete claim with its evidence and verdict."""
        try:
            # Get claim
            claim_response = self.supabase.table("claims").select("*").eq("id", str(claim_id)).execute()
            if not claim_response.data:
                return None
            
            claim = DBClaim(**claim_response.data[0])
            
            # Get evidence
            evidence_response = self.supabase.table("evidence").select("*").eq("claim_id", str(claim_id)).execute()
            evidence_list = [DBEvidence(**ev) for ev in evidence_response.data]
            
            # Get verdict
            verdict_response = self.supabase.table("verdicts").select("*").eq("claim_id", str(claim_id)).execute()
            verdict = DBVerdict(**verdict_response.data[0]) if verdict_response.data else None
            
            return (claim, evidence_list, verdict)
            
        except Exception as e:
            logger.error(f"Error retrieving claim data: {e}")
            return None
    
    async def get_recent_verdicts(self, limit: int = 10) -> List[Tuple[DBClaim, DBVerdict]]:
        """Get recent verdicts with their claims."""
        try:
            response = self.supabase.table("verdicts").select(
                "*, claims(*)"
            ).order("created_at", desc=True).limit(limit).execute()
            
            results = []
            for result in response.data:
                claim = DBClaim(**result['claims'])
                verdict = DBVerdict(**{k: v for k, v in result.items() if k != 'claims'})
                results.append((claim, verdict))
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving recent verdicts: {e}")
            return []

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
async def insert_claim(content: str) -> Optional[UUID]:
    """Legacy function for inserting claims."""
    claim = AgentClaim(text=content)
    return await db_manager.store_claim(claim)

async def get_all_claims():
    """Legacy function for getting all claims."""
    try:
        response = db_manager.supabase.table("claims").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting claims: {e}")
        return []

async def delete_all_claims():
    """Legacy function for deleting all claims."""
    try:
        response = db_manager.supabase.table("claims").delete().gt("id", "00000000-0000-0000-0000-000000000000").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error deleting claims: {e}")
        return []