"""Factory for creating mock data for testing the VeriFact pipeline."""

import random
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict


class MockDataFactory:
    """Factory for creating mock data for testing."""

    # Sample domains for claims
    DOMAINS = ["politics", "health", "science", "economics", "technology", "history", "sports"]

    # Sample languages for multilingual testing
    LANGUAGES = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "zh": "Chinese",
        "ja": "Japanese",
        "ru": "Russian",
        "ar": "Arabic",
    }

    # Sample sources for evidence
    SOURCES = [
        "https://example.com/source1",
        "https://example.com/source2",
        "https://example.com/source3",
        "https://example.com/source4",
        "https://example.com/source5",
        "https://en.wikipedia.org/wiki/Example",
        "https://news.example.com/article1",
        "https://academic.example.edu/paper1",
        "https://government.example.gov/report1",
    ]

    # Sample stances for evidence
    STANCES = ["supporting", "contradicting", "neutral"]

    # Sample verdict types
    VERDICT_TYPES = ["true", "false", "partially true", "unverifiable"]

    @classmethod
    def create_claim(
        cls,
        text: Optional[str] = None,
        domain: Optional[str] = None,
        context: Optional[float] = None,
        language: Optional[str] = None,
        controversial: bool = False,
    ) -> Claim:
        """Create a mock claim.
        
        Args:
            text: The claim text. If None, a random claim will be generated.
            domain: The domain of the claim. If None, a random domain will be chosen.
            context: The context score. If None, a random score will be generated.
            language: The language of the claim. If None, English will be used.
            controversial: Whether the claim should be controversial.
            
        Returns:
            A mock Claim object.
        """
        if text is None:
            domain = domain or random.choice(cls.DOMAINS)
            language_code = language or "en"
            language_name = cls.LANGUAGES.get(language_code, "English")
            
            if domain == "politics":
                if controversial:
                    text = f"The {language_name} government is corrupt and serves only the elite."
                else:
                    text = f"The {language_name} parliament has 500 members."
            elif domain == "health":
                if controversial:
                    text = f"Alternative medicine is more effective than conventional medicine in {language_name}-speaking countries."
                else:
                    text = f"Regular exercise reduces the risk of heart disease in {language_name}-speaking populations."
            elif domain == "science":
                if controversial:
                    text = f"Climate change is not caused by human activities according to {language_name} scientists."
                else:
                    text = f"Water freezes at 0 degrees Celsius at standard pressure according to {language_name} textbooks."
            elif domain == "economics":
                if controversial:
                    text = f"Cryptocurrency will replace traditional banking in {language_name}-speaking countries."
                else:
                    text = f"The GDP of {language_name}-speaking countries grew by 2.5% last year."
            else:
                if controversial:
                    text = f"Social media is destroying society in {language_name}-speaking regions."
                else:
                    text = f"The internet was invented in the 1960s according to {language_name} historical records."
        
        if context is None:
            context = round(random.uniform(0.5, 1.0), 2)
            
        return Claim(text=text, context=context)

    @classmethod
    def create_evidence(
        cls,
        claim: Optional[Claim] = None,
        stance: Optional[str] = None,
        relevance: Optional[float] = None,
        source: Optional[str] = None,
        content: Optional[str] = None,
        malformed: bool = False,
    ) -> Evidence:
        """Create mock evidence for a claim.
        
        Args:
            claim: The claim to create evidence for. If None, a random claim will be created.
            stance: The stance of the evidence. If None, a random stance will be chosen.
            relevance: The relevance score. If None, a random score will be generated.
            source: The source URL. If None, a random source will be chosen.
            content: The evidence content. If None, content will be generated based on the claim.
            malformed: Whether to create malformed evidence (for testing error handling).
            
        Returns:
            A mock Evidence object.
        """
        claim = claim or cls.create_claim()
        stance = stance or random.choice(cls.STANCES)
        relevance = relevance or round(random.uniform(0.5, 1.0), 2)
        source = source or random.choice(cls.SOURCES)
        
        if content is None:
            if stance == "supporting":
                content = f"Research confirms that {claim.text}"
            elif stance == "contradicting":
                content = f"Studies have disproven the claim that {claim.text}"
            else:
                content = f"There is mixed evidence regarding whether {claim.text}"
                
        if malformed:
            # Create malformed evidence for testing error handling
            if random.choice([True, False]):
                source = "invalid-url"
            else:
                content = ""
                
        return Evidence(content=content, source=source, relevance=relevance, stance=stance)

    @classmethod
    def create_evidence_set(
        cls,
        claim: Optional[Claim] = None,
        count: int = 3,
        mixed_stances: bool = True,
        include_malformed: bool = False,
    ) -> List[Evidence]:
        """Create a set of evidence for a claim.
        
        Args:
            claim: The claim to create evidence for. If None, a random claim will be created.
            count: The number of evidence items to create.
            mixed_stances: Whether to include evidence with different stances.
            include_malformed: Whether to include malformed evidence.
            
        Returns:
            A list of Evidence objects.
        """
        claim = claim or cls.create_claim()
        evidence_set = []
        
        for i in range(count):
            if mixed_stances:
                stance = cls.STANCES[i % len(cls.STANCES)]
            else:
                stance = random.choice(cls.STANCES)
                
            malformed = include_malformed and i == count - 1
            evidence = cls.create_evidence(claim=claim, stance=stance, malformed=malformed)
            evidence_set.append(evidence)
            
        return evidence_set

    @classmethod
    def create_verdict(
        cls,
        claim: Optional[Claim] = None,
        evidence: Optional[List[Evidence]] = None,
        verdict_type: Optional[str] = None,
        confidence: Optional[float] = None,
        explanation: Optional[str] = None,
        sources: Optional[List[str]] = None,
    ) -> Verdict:
        """Create a mock verdict for a claim.
        
        Args:
            claim: The claim to create a verdict for. If None, a random claim will be created.
            evidence: The evidence for the claim. If None, random evidence will be created.
            verdict_type: The type of verdict. If None, a random type will be chosen.
            confidence: The confidence score. If None, a score will be generated based on the verdict type.
            explanation: The explanation. If None, an explanation will be generated.
            sources: The sources. If None, sources will be extracted from the evidence.
            
        Returns:
            A mock Verdict object.
        """
        claim = claim or cls.create_claim()
        evidence = evidence or cls.create_evidence_set(claim=claim)
        verdict_type = verdict_type or random.choice(cls.VERDICT_TYPES)
        
        if confidence is None:
            if verdict_type == "true":
                confidence = round(random.uniform(0.8, 1.0), 2)
            elif verdict_type == "false":
                confidence = round(random.uniform(0.8, 1.0), 2)
            elif verdict_type == "partially true":
                confidence = round(random.uniform(0.6, 0.9), 2)
            else:  # unverifiable
                confidence = round(random.uniform(0.3, 0.7), 2)
                
        if sources is None:
            sources = [e.source for e in evidence]
            
        if explanation is None:
            if verdict_type == "true":
                explanation = f"The claim that {claim.text} is true based on multiple reliable sources."
            elif verdict_type == "false":
                explanation = f"The claim that {claim.text} is false according to available evidence."
            elif verdict_type == "partially true":
                explanation = f"The claim that {claim.text} is partially true. While some aspects are accurate, others are not fully supported by evidence."
            else:  # unverifiable
                explanation = f"The claim that {claim.text} cannot be verified with available evidence."
                
        return Verdict(
            claim=claim.text,
            verdict=verdict_type,
            confidence=confidence,
            explanation=explanation,
            sources=sources,
        )

    @classmethod
    def create_scenario(
        cls,
        scenario_type: str,
        claim_count: int = 3,
        evidence_per_claim: int = 3,
    ) -> Dict[str, Any]:
        """Create a complete test scenario.
        
        Args:
            scenario_type: The type of scenario to create. Options:
                - "standard": A mix of different claim types
                - "controversial": Controversial claims
                - "multilingual": Claims in different languages
                - "error_prone": Includes malformed data
                - "high_volume": Many claims and evidence
                - "time_sensitive": Claims about recent events
            claim_count: The number of claims to create.
            evidence_per_claim: The number of evidence items per claim.
            
        Returns:
            A dictionary containing claims, evidence, and verdicts.
        """
        claims = []
        evidence_map = {}
        verdicts = []
        
        if scenario_type == "standard":
            # Create a mix of different claim types
            for i in range(claim_count):
                verdict_type = cls.VERDICT_TYPES[i % len(cls.VERDICT_TYPES)]
                claim = cls.create_claim(domain=random.choice(cls.DOMAINS))
                evidence = cls.create_evidence_set(claim=claim, count=evidence_per_claim)
                verdict = cls.create_verdict(claim=claim, evidence=evidence, verdict_type=verdict_type)
                
                claims.append(claim)
                evidence_map[claim.text] = evidence
                verdicts.append(verdict)
                
        elif scenario_type == "controversial":
            # Create controversial claims
            for i in range(claim_count):
                claim = cls.create_claim(controversial=True)
                evidence = cls.create_evidence_set(claim=claim, count=evidence_per_claim, mixed_stances=True)
                
                # Controversial claims are often partially true or unverifiable
                verdict_type = random.choice(["partially true", "unverifiable"])
                verdict = cls.create_verdict(claim=claim, evidence=evidence, verdict_type=verdict_type)
                
                claims.append(claim)
                evidence_map[claim.text] = evidence
                verdicts.append(verdict)
                
        elif scenario_type == "multilingual":
            # Create claims in different languages
            languages = list(cls.LANGUAGES.keys())
            for i in range(claim_count):
                language = languages[i % len(languages)]
                claim = cls.create_claim(language=language)
                evidence = cls.create_evidence_set(claim=claim, count=evidence_per_claim)
                verdict = cls.create_verdict(claim=claim, evidence=evidence)
                
                claims.append(claim)
                evidence_map[claim.text] = evidence
                verdicts.append(verdict)
                
        elif scenario_type == "error_prone":
            # Create scenarios with potential errors
            for i in range(claim_count):
                claim = cls.create_claim()
                evidence = cls.create_evidence_set(
                    claim=claim,
                    count=evidence_per_claim,
                    include_malformed=(i % 2 == 0)  # Every other claim has malformed evidence
                )
                
                # Some claims have no verdict (to simulate errors)
                if i % 3 != 0:  # 2/3 of claims have verdicts
                    verdict = cls.create_verdict(claim=claim, evidence=evidence)
                    verdicts.append(verdict)
                
                claims.append(claim)
                evidence_map[claim.text] = evidence
                
        elif scenario_type == "high_volume":
            # Create many claims and evidence
            high_claim_count = claim_count * 3
            high_evidence_count = evidence_per_claim * 2
            
            for i in range(high_claim_count):
                claim = cls.create_claim()
                evidence = cls.create_evidence_set(claim=claim, count=high_evidence_count)
                verdict = cls.create_verdict(claim=claim, evidence=evidence)
                
                claims.append(claim)
                evidence_map[claim.text] = evidence
                verdicts.append(verdict)
                
        elif scenario_type == "time_sensitive":
            # Create claims about recent events
            current_year = datetime.now().year
            
            time_claims = [
                f"The Olympics were held in Paris in {current_year}.",
                f"The global temperature reached a record high in {current_year}.",
                f"The presidential election took place in {current_year}.",
                f"The stock market crashed in {current_year}.",
                f"A major peace treaty was signed in {current_year}.",
            ]
            
            for i in range(min(claim_count, len(time_claims))):
                claim = cls.create_claim(text=time_claims[i])
                evidence = cls.create_evidence_set(claim=claim, count=evidence_per_claim)
                
                # Time-sensitive claims are often unverifiable or partially true
                verdict_type = random.choice(["unverifiable", "partially true"])
                verdict = cls.create_verdict(claim=claim, evidence=evidence, verdict_type=verdict_type)
                
                claims.append(claim)
                evidence_map[claim.text] = evidence
                verdicts.append(verdict)
        
        return {
            "claims": claims,
            "evidence_map": evidence_map,
            "verdicts": verdicts,
            "scenario_type": scenario_type,
        }

    @classmethod
    def create_runner_result_mock(cls, output_data: Any) -> Any:
        """Create a mock for the result returned by Runner.run().
        
        Args:
            output_data: The data to return from final_output_as.
            
        Returns:
            A mock object with a final_output_as method.
        """
        class MockRunnerResult:
            def __init__(self, data):
                self.data = data
                self.final_output = str(data)
                
            def final_output_as(self, output_type):
                return self.data
                
        return MockRunnerResult(output_data)
