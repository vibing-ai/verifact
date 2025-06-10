import os
from typing import Literal, Optional

from pydantic import BaseModel, Field
from agents import Agent, Runner

class Verdict(BaseModel):
    """A verdict on a claim based on evidence.
    
    Attributes:
        claim: The original claim being fact-checked
        verdict: The verdict on the claim (true, false, partially true, or unverifiable)
        confidence: Confidence in the verdict (0-1)
        explanation: Explanation of the verdict with reasoning and citations
        sources: List of sources used to reach the verdict
        alternative_perspectives: Optional list of alternative viewpoints when evidence is mixed
    """

    claim: str
    verdict: Literal["true", "false", "partially true", "unverifiable"] = Field(
        description="The verdict on the claim: true, false, partially true, or unverifiable"
    )
    confidence: float = Field(
        description="Confidence in the verdict (0-1)", ge=0.0, le=1.0
    )
    explanation: str = Field(
        description="Explanation of the verdict with reasoning and citations"
    )
    sources: list[str] = Field(
        description="List of sources used to reach the verdict", min_length=1
    )
    alternative_perspectives: Optional[list[str]] = Field(
        description="Alternative perspectives or interpretations when evidence is mixed",
        default_factory=list
    )

PROMPT = """
You are a verdict writing agent. Your job is to analyze evidence and determine
the accuracy of a claim, providing a clear explanation and citing sources.

---

Claim: {claim}

Evidence provided:
{evidence}

Explanation detail level: {detail_level}

---

You must output:
- claim: The original claim being fact-checked
- verdict: true, false, partially true, or unverifiable
- confidence: from 0.0 to 1.0
- explanation: A clear explanation tailored to the detail level
- sources: List of sources cited in the explanation
- alternative_perspectives: List of alternative viewpoints when evidence is mixed

---

Instructions:

1. Assess the credibility and relevance of each evidence entry.
2. Classify evidence by stance: supporting, contradicting, neutral.
3. Weigh supporting vs. contradicting evidence and determine consensus.
4. Use source credibility (e.g., peer-reviewed > blog) and relevance score.
5. Cite sources in explanation as [n] and include the list of sources.
6. Adjust the explanation based on detail level:
   - brief: One sentence summary with 1–2 sources (max 30 words)
   - standard: 2–3 sentences with key evidence
   - detailed: Comprehensive analysis with all evidence and perspectives
7. For confidence scoring:
   - 0.9-1.0: Overwhelming evidence from multiple high-credibility sources, all supporting
   - 0.7-0.89: Strong evidence from reliable sources, mostly supporting
   - 0.4-0.69: Mixed evidence or limited sources
   - 0.1-0.39: Weak or contradictory evidence
   - 0.0-0.09: Insufficient evidence
   IMPORTANT: When evidence is mixed (both supporting and contradicting), confidence MUST be between 0.4 and 0.6

Guidelines:
- Maintain political neutrality
- Write for a non-expert audience
- Be transparent about uncertainty or lack of evidence
- If evidence is mixed, include alternative perspectives
- Consider evidence relevance when assigning confidence scores
- For mixed evidence, confidence MUST be between 0.4 and 0.6
"""

def format_evidence_block(evidence: list[dict]) -> str:
    """Converts a list of evidence dicts to a readable block for the LLM.
    
    Args:
        evidence: List of evidence dictionaries containing content, source, relevance, and stance
        
    Returns:
        Formatted string with numbered evidence entries
    """
    formatted = []
    for i, e in enumerate(evidence, 1):
        formatted.append(
            f"{i}. [{e.get('stance')}] \"{e.get('content')}\" — {e.get('source')} (relevance: {e.get('relevance', 1.0)})"
        )
    return "\n".join(formatted)

class VerdictWriter:
    """Agent responsible for generating verdicts based on evidence.
    
    The VerdictWriter analyzes evidence and produces well-reasoned verdicts with
    proper citations and explanations. It supports multiple detail levels and
    includes alternative perspectives when evidence is mixed.
    
    Attributes:
        agent: The underlying Agent instance
    """

    def __init__(self, model: Optional[str] = None):
        """Initialize the VerdictWriter agent.
        
        Args:
            model: Optional model name to override the default
        """
        self.agent = Agent(
            name="VerdictWriter",
            instructions=PROMPT,
            output_type=Verdict,
            tools=[],
            model=model or os.getenv("VERDICT_WRITER_MODEL"),
        )

    async def run(
        self,
        claim: str,
        evidence: list[dict],
        detail_level: Literal["brief", "standard", "detailed"] = "standard",
    ) -> Verdict:
        """Generate a verdict for a claim based on evidence.
        
        Args:
            claim: The claim to fact-check
            evidence: List of evidence dictionaries with content, source, relevance, and stance
            detail_level: Level of detail for the explanation (brief, standard, or detailed)
            
        Returns:
            Verdict object containing the verdict, confidence, explanation, and sources
        """
        prompt_input = PROMPT.format(
            claim=claim,
            evidence=format_evidence_block(evidence),
            detail_level=detail_level,
        )

        result = await Runner.run(self.agent, prompt_input)
        verdict = result.final_output_as(Verdict)
        verdict.claim = claim  # Ensure claim is set correctly
        verdict.sources = list(set(filter(None, verdict.sources)))  # Deduplicate and remove empty
        return verdict
