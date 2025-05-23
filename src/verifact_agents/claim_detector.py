from pydantic import BaseModel, Field
from typing import List, Dict, Any
from agents import Agent, Runner
import os
import logging

logger = logging.getLogger(__name__)

class Claim(BaseModel):
    """A factual claim that requires verification."""
    text: str
    normalized_text: str = ""
    check_worthiness: float = 0.0
    specificity_score: float = 0.0
    public_interest_score: float = 0.0
    impact_score: float = 0.0
    confidence: float = 0.0
    domain: str = ""
    entities: Dict[str, List[str]] = Field(default_factory=dict)
    compound_parts: List[str] = Field(default_factory=list)
    rank: int = 0
    context: str = ""

class ClaimScore(BaseModel):
    """A factual claim that requires verification."""
    claim: str
    check_worthiness: float = 0.0
    specificity_score: float = 0.0
    public_interest_score: float = 0.0
    impact_score: float = 0.0
    confidence: float = 0.0
    rank: int = 0

class ClaimEntity(BaseModel):
    """A factual claim that requires verification."""
    claim: str
    entities: List[str] = Field(default_factory=list)

class ClaimDomain(BaseModel):
    """A factual claim that requires verification."""
    claim: str
    domain: List[str] = Field(default_factory=list)

class ClaimDetector:
    """Modular claim detection system that breaks down the process into discrete tasks."""
    
    def __init__(self, model: str = None):
        """Initialize the claim detector with a specific model.
        
        Args:
            model: The model to use for claim detection. If None, uses the CLAIM_DETECTOR_MODEL env var.
        """
        self.model = model or os.getenv("CLAIM_DETECTOR_MODEL")
        self.task_agents = {}
    
    async def process(self, text: str) -> List[Claim]:
        """Process text through the full claim detection pipeline.
        
        Args:
            text: The text to analyze for claims
            
        Returns:
            A list of Claim objects representing the detected claims
        """
        logger.info("Processing text for claim detection")
        
        # 1. Extract normalized atomic claims
        normalized_claims = await self.extract_normalized_claims(text)
        if not normalized_claims:
            logger.info("No claims identified in the text")
            return []
        
        # 2. Score and Rank claims
        ordered_claims = await self.score_and_rank_claims(normalized_claims, text)
        logger.info(f"Claims scored: {ordered_claims}")
        
        # 3. Extract entities
        claim_entities = await self.extract_entities(normalized_claims)
        logger.info(f"Claims with entities: {claim_entities}")

        # 4. Classify domains
        claim_domains = await self.classify_domains(normalized_claims)
        logger.info(f"Claims with domains: {claim_domains}")
        
        # 5. Combine results into Claim objects
        claims = []
        for i, curr_claim in enumerate(ordered_claims):
            normalized_claim = curr_claim.claim
            claim = Claim(
                text=normalized_claim,
                normalized_text=normalized_claim,
                context=text,
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
                    claim.entities = {"entity": entity_item.entities}
                    break
            
            # Add domain
            for domain_item in claim_domains:
                if domain_item.claim == normalized_claim:
                    claim.domain = domain_item.domain[0] if domain_item.domain else ""
                    break
            
            claims.append(claim)

        # Pretty Print claims 
        for claim in claims:
            logger.info(f"\nClaim: {claim}")
        
        logger.info(f"Identified and processed {len(claims)} claims")
        return claims
    
    async def extract_normalized_claims(self, text: str) -> List[str]:
        """Extract, normalize, and split compound claims in one operation.
        
        This combines the previous identify_claims, normalize_claims, and split_compound_claims
        steps into a single operation for efficiency.
        
        Args:
            text: The text to analyze for claims
            
        Returns:
            A list of strings, each containing a normalized atomic claim
        """
        logger.info("Extracting normalized atomic claims")
        
        extract_prompt = """
        Extract factual claims from the following text. For each claim:
        1. Identify if it's a factual claim that can be verified
        2. Normalize it by removing qualifiers and standardizing terminology
        3. Split compound claims into separate atomic claims
        
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
        
        Text: {text}
        """
        
        if "extract_normalized" not in self.task_agents:
            self.task_agents["extract_normalized"] = Agent(
                name="ClaimExtractor",
                instructions=extract_prompt,
                output_type=List[str],
                tools=[],
                model=self.model,
            )
        
        result = await Runner.run(
            self.task_agents["extract_normalized"], 
            extract_prompt.format(text=text)
        )
        
        normalized_claims = result.final_output_as(List[str])
        logger.info(f"Extracted {len(normalized_claims)} normalized atomic claims")
        logger.info(f"Claim(s) extracted: {normalized_claims}")
        return normalized_claims
    
    async def score_and_rank_claims(self, claims: List[str], context: str) -> List[ClaimScore]:
        """Score each claim's check-worthiness, specificity, public interest, and impact."""
        logger.info("Scoring and ranking claims")
        
        scoring_prompt = """
        You are a fact-checking evaluation system. For each claim below, provide a detailed scoring analysis and rank the claims by their overall priority for fact-checking.

        Evaluate each claim on the following dimensions, using a score between 0 and 1:
        - **check_worthiness**: How important is it to verify this claim?
        - **specificity_score**: How specific and concrete is the claim?
        - **public_interest_score**: How much public interest does this claim have?
        - **impact_score**: What potential impact could this claim have if believed?
        - **confidence**: How confident are you that this is a factual, verifiable claim?

        After scoring, calculate an overall **priority rank** for each claim using these scores. Claims with higher check_worthiness, public interest, impact, and specificity should generally rank higher.

        Instructions:
        - Rank 1 indicates the highest priority for fact-checking.
        - Return all claims **in order of ascending rank** (i.e., highest priority claim first).
        - Be objective based on the claim content and any provided context.

        Claims to evaluate:
        {claims}

        Context (if relevant):
        {context}

        Return the output as a list of JSON objects. Each object must include:
        - "claim": the original claim
        - The five score fields: check_worthiness, specificity_score, public_interest_score, impact_score, confidence
        - "rank": an integer indicating overall priority (1 = highest)
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
