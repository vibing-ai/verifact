import asyncio
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from agents import Agent, Runner
import os
import logging

logger = logging.getLogger(__name__)

class Claim(BaseModel):
    text: str
    check_worthiness: float = 0.0
    specificity_score: float = 0.0
    public_interest_score: float = 0.0
    impact_score: float = 0.0
    confidence: float = 0.0
    domains: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    rank: int = 0

class ClaimScore(BaseModel):
    claim: str
    check_worthiness: float = 0.0
    specificity_score: float = 0.0
    public_interest_score: float = 0.0
    impact_score: float = 0.0
    confidence: float = 0.0
    rank: int = 0

class ClaimEntity(BaseModel):
    claim: str
    entities: List[str] = Field(default_factory=list)

class ClaimDomain(BaseModel):
    claim: str
    domain: List[str] = Field(default_factory=list)

class ClaimDetector:
    """Modular claim detection system that breaks down the process into discrete tasks."""
    
    def __init__(self, model: str = None):
        self.model = model or os.getenv("CLAIM_DETECTOR_MODEL")
        self.task_agents = {}
    
    async def process(self, text: str) -> List[Claim]:
        logger.info("Processing text for claim detection")
        
        # Extract normalized factual claims
        normalized_claims = await self.extract_normalized_claims(text)
        if not normalized_claims:
            logger.info("No claims identified in the text")
            return []
        
        # Run tasks to score, extract entities, and classify domains in parallel
        tasks = [
            self.score_claims(normalized_claims, text),
            self.extract_entities(normalized_claims),
            self.classify_domains(normalized_claims)
        ]
        scored_claims, claim_entities, claim_domains = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        for i, result in enumerate([scored_claims, claim_entities, claim_domains]):
            if isinstance(result, Exception):
                logger.error(f"Error in task {i}: {result}", exc_info=True)
                raise result

        # Rank claims
        ordered_claims = await self.rank_claims(scored_claims)
        logger.info(f"Claims ranked: {ordered_claims}")
        
        # Combine results into Claim objects
        claims = []
        for i, curr_claim in enumerate(ordered_claims):
            normalized_claim = curr_claim.claim
            claim = Claim(
                text=normalized_claim,
                rank=curr_claim.rank,
                check_worthiness=curr_claim.check_worthiness,
                specificity_score=curr_claim.specificity_score,
                public_interest_score=curr_claim.public_interest_score,
                impact_score=curr_claim.impact_score,
                confidence=curr_claim.confidence
            )
            
            # Add entities
            for entity_item in claim_entities:
                if entity_item.claim == normalized_claim:
                    claim.entities = entity_item.entities
                    break
            
            # Add domain
            for domain_item in claim_domains:
                if domain_item.claim == normalized_claim:
                    claim.domains = domain_item.domain if domain_item.domain else ""
                    break
            
            claims.append(claim)
        
        logger.info(f"Identified and processed {len(claims)} claims")
        return claims
    
    async def extract_normalized_claims(self, text: str) -> List[str]:
        logger.info("Extracting normalized atomic claims")
        
        extract_prompt = """
        Extract factual claims from the following text. For each claim:
        1. Identify if it's a factual claim that can be verified
        2. Avoid extracting non-factual claims
        
        FACTUAL CLAIMS:
        - Are statements presented as facts
        - Can be verified with evidence
        - Make specific, measurable assertions
        - Examples: statistical claims, historical facts, scientific statements
        
        NOT FACTUAL CLAIMS:
        - Personal opinions ("I think pizza is delicious")
        - Subjective judgments ("This is the best movie")
        - Hypotheticals ("If it rains tomorrow...")
        - Pure predictions about future events ("Next year's winner will be...")
        - Questions ("Is climate change real?")
        
        Return a list of strings, each containing a factual claim.
        
        Text: {text}
        """
        
        if "extract_factual_claims" not in self.task_agents:
            self.task_agents["extract_factual_claims"] = Agent(
                name="ClaimExtractor",
                instructions=extract_prompt,
                output_type=List[str],
                tools=[],
                model=self.model,
            )
        
        result = await Runner.run(
            self.task_agents["extract_factual_claims"], 
            extract_prompt.format(text=text)
        )
        
        factual_claims = result.final_output_as(List[str])
        logger.info(f"Extracted {len(factual_claims)} factual claims")
        
        noramlized_claims = await self.normalize_claims(factual_claims)

        return noramlized_claims

    async def normalize_claims(self, claims: List[str]) -> List[str]:
        extract_prompt = """
        Normalize each factual claims from the following list of claims:
        1. Normalize it by removing qualifiers and standardizing terminology
        2. Split compound claims into separate atomic claims
        
        NORMALIZATION GUIDELINES:
        - Remove unnecessary qualifiers and hedging language
        - Standardize terminology
        - Make implicit subjects explicit
        - Convert to active voice
        - Maintain the core factual assertion
        
        COMPOUND CLAIM EXAMPLE:
        "AI is bad for the environment according to Elon Musk who never lies. He does not support the use of AI in any form becuase he is losing in that industry."
        Should be split into:
        1. "ELon Musk claims that AI is bad for the environment."
        2. "Elon Musk never lies."
        3. "Elon Musk does not support the use of AI in any form."
        4. "Elon Musk is losing in the AI industry."
        
        Return a list of strings, each containing a normalized atomic claim.
        
        Claims: {claims}
        """

        if "normalized_claims" not in self.task_agents:
            self.task_agents["normalized_claims"] = Agent(
                name="ClaimNormalizer",
                instructions=extract_prompt,
                output_type=List[str],
                tools=[],
                model=self.model,
            )
        
        result = await Runner.run(
            self.task_agents["normalized_claims"], 
            extract_prompt.format(claims=claims)
        )
        normalized_claims = result.final_output_as(List[str])
        logger.info(f"Normalized {len(normalized_claims)} claims")
        return normalized_claims
 
    async def score_claims(self, claims: List[str], context: str) -> List[ClaimScore]:
        """Score each claim's check-worthiness, specificity, public interest, impact, and confidence."""
        logger.info("Scoring claims")
        
        scoring_prompt = """
        You are a fact-checking evaluation system. For each claim below, provide a detailed scoring analysis.

        Evaluate each claim on the following dimensions, using a score between 0 and 1:
        - **check_worthiness**: How important is it to verify this claim?
        - **specificity_score**: How specific and concrete is the claim?
        - **public_interest_score**: How much public interest does this claim have?
        - **impact_score**: What potential impact could this claim have if believed?
        - **confidence**: How confident are you that this is a factual, verifiable claim?

        Instructions:
        - Be objective based on the claim content and any provided context.
        - Higher scores indicate greater importance, specificity, public interest, impact, or confidence.

        Claims to evaluate:
        {claims}

        Context (if relevant):
        {context}

        Return the output as a list of JSON objects. Each object must include:
        - "claim": the original claim
        - The five score fields: check_worthiness, specificity_score, public_interest_score, impact_score, confidence
        """
        
        if "score" not in self.task_agents:
            self.task_agents["score"] = Agent(
                name="ClaimScorer",
                instructions=scoring_prompt,
                output_type=List[ClaimScore],
                tools=[],
                model=self.model,
            )
        
        result = await Runner.run(
            self.task_agents["score"],
            scoring_prompt.format(claims=claims, context=context)
        )
        
        scored_claims = result.final_output_as(List[ClaimScore])
                
        logger.info("Claims scored successfully")
        return scored_claims
    
    async def rank_claims(self, scored_claims: List[ClaimScore]) -> List[ClaimScore]:
        """Rank claims by priority based on their scores."""
        logger.info("Ranking claims")
        
        ranking_prompt = """
        You are a fact-checking prioritization system. For the scored claims below, assign priority rankings.

        Calculate an overall **priority rank** for each claim using these scores:
        - check_worthiness: How important is it to verify this claim?
        - specificity_score: How specific and concrete is the claim?
        - public_interest_score: How much public interest does this claim have?
        - impact_score: What potential impact could this claim have if believed?
        - confidence: How confident are you that this is a factual, verifiable claim?

        Claims with higher check_worthiness, public interest, impact, and specificity should generally rank higher.

        Instructions:
        - Rank 1 indicates the highest priority for fact-checking.
        - Return all claims **in order of ascending rank** (i.e., highest priority claim first).
        - Each claim must have a unique rank.

        Scored claims to rank:
        {scored_claims}

        Return the output as a list of JSON objects with the same structure as input, but with added "rank" field.
        Each object must include:
        - "claim": the original claim
        - The five score fields: check_worthiness, specificity_score, public_interest_score, impact_score, confidence
        - "rank": an integer indicating overall priority (1 = highest)
        """
        
        if "rank" not in self.task_agents:
            self.task_agents["rank"] = Agent(
                name="ClaimRanker",
                instructions=ranking_prompt,
                output_type=List[ClaimScore],
                tools=[],
                model=self.model,
            )
        
        result = await Runner.run(
            self.task_agents["rank"],
            ranking_prompt.format(scored_claims=scored_claims)
        )
        
        ranked_claims = result.final_output_as(List[ClaimScore])
        logger.info("Claims ranked successfully")
        return ranked_claims
    
    async def extract_entities(self, claims: List[str]) -> List[ClaimEntity]:
        """Extract and categorize entities mentioned in claims."""
        logger.info("Extracting entities from claims")
        
        entity_prompt = """
        You are an information extraction system. For each claim below, identify the key entities mentioned.

        Entities may include (but are not limited to) the following types:
        - People: Names of specific individuals
        - Organizations: Companies, institutions, agencies, groups
        - Locations: Cities, countries, landmarks, regions
        - Dates: Specific or general time references
        - Numbers: Quantities, statistics, percentages, monetary values
        - Events: Named events, conferences, historical or notable occurrences
        - Scientific Terms: Theories, principles, phenomena (e.g., gravity, evolution)
        - Ideologies/Belief Systems: Political, religious, or philosophical ideas (e.g., democracy, Buddhism)
        - Legal Terms: Laws, doctrines, or legal principles (e.g., antitrust, due process)
        - Products/Technologies: Tools, software, devices (e.g., iPhone, CRISPR, ChatGPT)
        - Legislation/Policies: Specific policies or laws (e.g., GDPR, Affordable Care Act)
        - Publications/Media: Titles of books, films, articles, or reports
        - Measurements/Units: Named units of measure (e.g., kilometers, gigawatts)

        Note: Not every claim will include entities from all categories. Extract only the entities that are explicitly mentioned or implied.

        Claims:
        {claims}

        Return the claims as a list of JSON objects. Each object must include:
        - "claim": the original claim
        - "entities": a flat list of strings representing the identified entities (no category labels)
        """
        
        if "entities" not in self.task_agents:
            self.task_agents["entities"] = Agent(
                name="EntityExtractor",
                instructions=entity_prompt,
                output_type=List[ClaimEntity],
                tools=[],
                model=self.model,
            )
        
        result = await Runner.run(
            self.task_agents["entities"],
            entity_prompt.format(claims=claims)
        )
        
        claims_with_entities = result.final_output_as(List[ClaimEntity])
        logger.info("Entities extracted successfully")
        return claims_with_entities
    
    async def classify_domains(self, claims: List[str]) -> List[ClaimDomain]:
        """Classify claims by domain (politics, science, health, etc.)."""
        logger.info("Classifying claim domains")
        
        domain_prompt = """
        You are a topic classification system. For each claim below, identify the relevant domain or topic area(s) it falls under.

        Each claim may relate to one or more domains. Choose from the following illustrative list:

        - Politics: Government, public policy, political figures, elections
        - Health: Medicine, healthcare, diseases, wellness, medical advice
        - Science: Scientific research, discoveries, space, physics, biology
        - Economics: Finance, business, markets, trade, employment
        - Environment: Climate change, conservation, energy, pollution
        - Social: Society, culture, religion, education, demographics
        - History: Historical events, figures, timelines, wars
        - Sports: Teams, athletes, games, scores, statistics
        - Other: If none of the above clearly apply, label as "other" and briefly specify in a comment (optional)

        Note:
        - Not every domain must be used.
        - Assign all relevant domains to each claim; some may span multiple areas.

        Claims:
        {claims}

        Return the claims as a list of JSON objects. Each object must include:
        - "claim": the original claim
        - "domain": a list of strings representing the identified domain(s)
        """
        
        if "domains" not in self.task_agents:
            self.task_agents["domains"] = Agent(
                name="DomainClassifier",
                instructions=domain_prompt,
                output_type=List[ClaimDomain],
                tools=[],
                model=self.model,
            )
        
        result = await Runner.run(
            self.task_agents["domains"],
            domain_prompt.format(claims=claims)
        )
        
        classified_claims = result.final_output_as(List[ClaimDomain])
        return classified_claims

default_claim_detector = ClaimDetector()
