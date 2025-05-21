"""Agent interfaces for the VeriFact factchecking system.

This module defines the specific interfaces for each agent type, building on the
base Agent protocol. These interfaces establish clear contracts for agent implementations.
"""

from typing import Protocol

from src.verifact_agents.base import Agent
from src.verifact_agents.dto import Claim, Evidence, Verdict


class ClaimDetector(Agent[str, list[Claim]], Protocol):
    """Agent responsible for detecting claims in text.

    This agent analyzes input text and extracts check-worthy factual claims.
    """

    async def detect_claims(
        self,
        text: str,
        min_check_worthiness: float | None = None,
        expected_claims: list[dict] | None = None,
        max_claims: int | None = None,
    ) -> list[Claim]:
        """Detect factual claims in the provided text.

        Args:
            text: The text to analyze for claims
            min_check_worthiness: Minimum threshold for considering a claim check-worthy (0-1)
            expected_claims: Optional list of claims expected to be found (for validation)
            max_claims: Maximum number of claims to return, ranked by check-worthiness

        Returns:
            List[Claim]: A list of detected claims
        """
        ...

    async def process(self, input_data: str) -> list[Claim]:
        """Process the input text and return detected claims.

        This method fulfills the base Agent protocol by calling detect_claims.

        Args:
            input_data: The text to analyze for claims

        Returns:
            List[Claim]: A list of detected claims
        """
        return await self.detect_claims(input_data)


class EvidenceHunter(Agent[Claim, list[Evidence]], Protocol):
    """Agent responsible for finding evidence for claims.

    This agent gathers evidence related to a claim from various sources.
    """

    async def gather_evidence(self, claim: Claim) -> list[Evidence]:
        """Gather evidence for the provided claim.

        Args:
            claim: The claim to gather evidence for

        Returns:
            List[Evidence]: A list of evidence pieces
        """
        ...

    async def process(self, input_data: Claim) -> list[Evidence]:
        """Process the input claim and return gathered evidence.

        This method fulfills the base Agent protocol by calling gather_evidence.

        Args:
            input_data: The claim to gather evidence for

        Returns:
            List[Evidence]: A list of evidence pieces
        """
        return await self.gather_evidence(input_data)


class VerdictWriter(Agent[tuple[Claim, list[Evidence]], Verdict], Protocol):
    """Agent responsible for generating verdicts based on evidence.

    This agent analyzes a claim and its evidence to generate a factchecking verdict.
    """

    async def generate_verdict(
        self,
        claim: Claim,
        evidence: list[Evidence],
        explanation_detail: str | None = None,
        citation_style: str | None = None,
        include_alternative_perspectives: bool | None = None,
    ) -> Verdict:
        """Generate a verdict for the claim based on evidence.

        Args:
            claim: The claim to generate a verdict for
            evidence: List of evidence pieces related to the claim
            explanation_detail: Level of detail for the explanation (brief, standard, detailed)
            citation_style: Style for citing sources (inline, footnote, academic)
            include_alternative_perspectives: Whether to include alternative viewpoints

        Returns:
            Verdict: A verdict with explanation and sources
        """
        ...

    async def process(self, input_data: tuple[Claim, list[Evidence]]) -> Verdict:
        """Process the input claim and evidence and return a verdict.

        This method fulfills the base Agent protocol by calling generate_verdict.

        Args:
            input_data: A tuple containing (claim, evidence_list)

        Returns:
            Verdict: A verdict with explanation and sources
        """
        claim, evidence = input_data
        return await self.generate_verdict(claim, evidence)


# Legacy interfaces for backward compatibility
class IClaimDetector(ClaimDetector, Protocol):
    """Legacy interface for claim detection, maintained for backward compatibility."""

    pass


class IEvidenceHunter(EvidenceHunter, Protocol):
    """Legacy interface for evidence hunting, maintained for backward compatibility."""

    pass


class IVerdictWriter(VerdictWriter, Protocol):
    """Legacy interface for verdict writing, maintained for backward compatibility."""

    pass
