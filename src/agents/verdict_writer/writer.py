"""
VerdictWriter agent for generating verdicts based on evidence.
"""

import os
from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field
from openai.agents import Agent, Runner
from src.utils.model_config import ModelManager
from src.agents.claim_detector.models import Claim
from src.agents.evidence_hunter.hunter import Evidence
from src.utils.logger import get_component_logger
from src.agents.interfaces import IVerdictWriter

# Create a logger for this module
logger = get_component_logger("verdict_writer")


class Verdict(BaseModel):
    """A verdict on a claim based on evidence."""
    claim: str
    verdict: Literal["true", "false", "partially true", "unverifiable"] = Field(
        description="The verdict on the claim: true, false, partially true, or unverifiable"
    )
    confidence: float = Field(
        description="Confidence in the verdict (0-1)",
        ge=0.0,
        le=1.0
    )
    explanation: str = Field(
        description="Detailed explanation of the verdict with reasoning"
    )
    sources: List[str] = Field(
        description="List of sources used to reach the verdict",
        min_items=1
    )
    evidence_summary: Optional[str] = Field(
        default=None,
        description="Summary of the key evidence considered in the verdict"
    )
    alternative_perspectives: Optional[str] = Field(
        default=None,
        description="Alternative viewpoints or interpretations when evidence is mixed"
    )
    key_evidence: Optional[List[Dict]] = Field(
        default=None,
        description="List of key evidence pieces with their relevance to the verdict"
    )
    citation_metadata: Optional[Dict] = Field(
        default=None,
        description="Metadata about citations including source quality and recency"
    )


class VerdictWriter(IVerdictWriter):
    """Agent for generating verdicts based on evidence."""
    
    def __init__(self, model_name: Optional[str] = None, 
                 explanation_detail: Literal["brief", "standard", "detailed"] = "standard",
                 citation_style: Literal["inline", "footnote", "academic"] = "inline",
                 include_alternative_perspectives: bool = True):
        """
        Initialize the VerdictWriter agent.
        
        Args:
            model_name: Optional name of the model to use
            explanation_detail: Level of detail for the explanation (brief, standard, detailed)
            citation_style: Style for citing sources (inline, footnote, academic)
            include_alternative_perspectives: Whether to include alternative viewpoints
        """
        # Create a ModelManager instance for this agent
        self.model_manager = ModelManager(agent_type="verdict_writer")
        
        # Override the model name if explicitly provided
        if model_name:
            self.model_manager.model_name = model_name
            # Rebuild fallback chain with new primary model
            self.model_manager.fallback_models = [model_name] + self.model_manager.fallback_models[1:]
        
        # Log model information
        logger.info(f"Using model: {self.model_manager.model_name} for verdict writing")
        # Default model is deepseek/deepseek-chat:free, which excels at reasoning
        if "deepseek" in self.model_manager.model_name.lower():
            logger.info("DeepSeek Chat is optimized for superior reasoning and evidence synthesis")
        
        # Store configuration parameters
        self.explanation_detail = explanation_detail
        self.citation_style = citation_style
        self.include_alternative_perspectives = include_alternative_perspectives
        
        # Configure OpenAI for Agent SDK
        self.model_manager.configure_openai_for_agent()
        
        # Create the agent for analyzing evidence and generating verdicts
        self.agent = Agent(
            name="VerdictWriter",
            instructions=f"""
            You are a verdict writing agent. Your job is to analyze evidence and determine
            the accuracy of a claim, providing a detailed explanation and citing sources.
            
            Your verdict should:
            1. Classify the claim as true, false, partially true, or unverifiable
            2. Assign a confidence score (0-1)
            3. Provide a detailed explanation of your reasoning
            4. Cite all sources used
            5. Summarize key evidence
            {f"6. Present alternative perspectives" if include_alternative_perspectives else ""}
            
            Guidelines for evidence assessment:
            - Base your verdict solely on the provided evidence
            - Weigh contradicting evidence according to source credibility and relevance
            - Consider the relevance score (0-1) as an indicator of how directly the evidence addresses the claim
            - Treat higher relevance and credibility sources as more authoritative
            - Evaluate stance ("supporting", "contradicting", "neutral") for each piece of evidence
            - When sources conflict, prefer more credible, more recent, and more directly relevant sources
            - Identify consensus among multiple independent sources as especially strong evidence
            
            Guidelines for confidence scoring:
            - Assign high confidence (0.8-1.0) only when evidence is consistent, highly credible, and comprehensive
            - Use medium confidence (0.5-0.79) when evidence is mixed or from fewer sources
            - Use low confidence (0-0.49) when evidence is minimal, outdated, or from less credible sources
            - When evidence is insufficient, label as "unverifiable" with appropriate confidence based on limitations
            - For partially true claims, explain precisely which parts are true and which are false
            
            Guidelines for explanations (current detail level: {explanation_detail}):
            - Brief: Provide a 1-2 sentence summary focusing on core evidence only
            - Standard: Write several paragraphs covering main evidence and reasoning
            - Detailed: Give a comprehensive explanation with all evidence, alternative views, and nuanced analysis
            
            Citation guidelines (current style: {citation_style}):
            - Inline: Cite sources directly in the explanation text (e.g., "According to [Source], ...")
            - Footnote: Use numbered references in the explanation with full citations in the sources list
            - Academic: Use formal citation format with author, publication, date in the sources list
            
            Your explanation must be:
            - Clear and accessible to non-experts
            - Factual rather than judgmental
            - Politically neutral and unbiased
            - Properly cited with all sources attributed
            - Transparent about limitations and uncertainty
            
            When evidence is mixed or contradictory, clearly present the different perspectives
            and explain how you reached your conclusion based on the balance of evidence.
            """,
            output_type=Verdict,
            model=self.model_manager.model_name,
            **self.model_manager.parameters
        )
    
    def _assess_evidence_quality(self, evidence: Evidence) -> float:
        """
        Calculate an evidence quality score based on credibility, relevance, and other factors.
        
        Args:
            evidence: The evidence to assess
            
        Returns:
            float: A quality score (0-1)
        """
        # Start with the relevance score
        quality_score = evidence.relevance
        
        # Include credibility if available in the source
        source_credibility = 0.7  # Default credibility when not specified
        if hasattr(evidence, 'source_credibility'):
            source_credibility = evidence.source_credibility
        
        # Adjust based on stance (this could be customized)
        stance_factor = {
            "supporting": 1.0,
            "contradicting": 1.0,
            "neutral": 0.8,
            "contextual": 0.7
        }.get(evidence.stance.lower(), 0.7)
        
        # Combine factors, ensuring the score stays in the 0-1 range
        combined_score = (quality_score * 0.6) + (source_credibility * 0.3) + (stance_factor * 0.1)
        return min(max(combined_score, 0.0), 1.0)
    
    def _rank_evidence(self, evidence_list: List[Evidence]) -> List[Dict]:
        """
        Rank evidence by quality and return with quality scores.
        
        Args:
            evidence_list: List of evidence to rank
            
        Returns:
            List of dictionaries with evidence and its quality score
        """
        ranked_evidence = []
        for evidence in evidence_list:
            quality_score = self._assess_evidence_quality(evidence)
            ranked_evidence.append({
                "evidence": evidence,
                "quality_score": quality_score
            })
        
        # Sort by quality score in descending order
        ranked_evidence.sort(key=lambda x: x["quality_score"], reverse=True)
        return ranked_evidence
    
    def _calculate_confidence_score(self, claim: str, evidence_list: List[Evidence]) -> float:
        """
        Calculate a confidence score (0-1) based on evidence quality, quantity, and consistency.
        
        Args:
            claim: The claim text
            evidence_list: List of evidence to evaluate
            
        Returns:
            float: Confidence score from 0 to 1
        """
        # If no evidence, confidence is very low
        if not evidence_list:
            return 0.1
            
        # Calculate base confidence from evidence quantity
        evidence_count = len(evidence_list)
        if evidence_count >= 5:
            quantity_score = 1.0
        elif evidence_count >= 3:
            quantity_score = 0.8
        elif evidence_count == 2:
            quantity_score = 0.6
        else:
            quantity_score = 0.4
            
        # Calculate quality score (average of top 3 evidence pieces)
        ranked_evidence = self._rank_evidence(evidence_list)
        top_evidence = ranked_evidence[:min(3, len(ranked_evidence))]
        if top_evidence:
            average_quality = sum(item["quality_score"] for item in top_evidence) / len(top_evidence)
        else:
            average_quality = 0.3
            
        # Check stance consistency
        stances = [e.stance.lower() for e in evidence_list]
        if len(set(stances)) == 1:
            # All evidence has same stance
            consistency_score = 1.0
        elif stances.count("supporting") >= 2 and stances.count("contradicting") == 0:
            # Multiple supporting, no contradicting
            consistency_score = 0.9
        elif stances.count("contradicting") >= 2 and stances.count("supporting") == 0:
            # Multiple contradicting, no supporting
            consistency_score = 0.9
        elif abs(stances.count("supporting") - stances.count("contradicting")) <= 1:
            # Evidence is split/conflicted
            consistency_score = 0.4
        else:
            # Mixed but with a clear majority
            consistency_score = 0.7
            
        # Combine scores with weights
        combined_score = (quantity_score * 0.3) + (average_quality * 0.5) + (consistency_score * 0.2)
        
        # Ensure final score is between 0.1 and 1.0
        return min(max(combined_score, 0.1), 1.0)
        
    def _format_citations(self, evidence_list: List[Evidence], style: str) -> List[str]:
        """
        Format citations according to the specified style.
        
        Args:
            evidence_list: List of evidence to cite
            style: Citation style (inline, footnote, academic)
            
        Returns:
            List of formatted citations
        """
        citations = []
        
        for i, evidence in enumerate(evidence_list):
            source = evidence.source
            
            # Extract domain from URL
            try:
                from urllib.parse import urlparse
                domain = urlparse(source).netloc
            except:
                domain = source
                
            if style == "inline":
                # Simple format with just the domain
                citation = f"{domain}"
            elif style == "footnote":
                # Numbered reference
                citation = f"[{i+1}] {source}"
            elif style == "academic":
                # More formal citation with date if available
                import datetime
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                citation = f"{domain}. Retrieved from {source} on {date}."
            else:
                # Default format
                citation = source
                
            citations.append(citation)
            
        return citations
    
    def _format_evidence_for_prompt(self, evidence_list: List[Evidence], detail_level: str) -> str:
        """
        Format evidence for inclusion in the prompt, with different detail levels.
        
        Args:
            evidence_list: List of evidence to format
            detail_level: Level of detail to include (brief, standard, detailed)
            
        Returns:
            Formatted evidence string
        """
        # Rank the evidence
        ranked_evidence = self._rank_evidence(evidence_list)
        
        evidence_text = []
        
        # Determine how many evidence items to include based on detail level
        if detail_level == "brief":
            # Include just top 3 evidence pieces
            top_evidence = ranked_evidence[:min(3, len(ranked_evidence))]
        elif detail_level == "standard":
            # Include top 5 evidence pieces
            top_evidence = ranked_evidence[:min(5, len(ranked_evidence))]
        else:  # detailed
            # Include all evidence
            top_evidence = ranked_evidence
            
        # Format each evidence item
        for i, item in enumerate(top_evidence):
            evidence = item["evidence"]
            quality = item["quality_score"]
            
            # Create an evidence entry
            entry = f"EVIDENCE {i+1} (Relevance: {evidence.relevance:.2f}, Quality: {quality:.2f}, Stance: {evidence.stance}):\n"
            entry += f"Source: {evidence.source}\n"
            
            # Adjust content length based on detail level
            if detail_level == "brief":
                # Truncate to first 100 characters
                content = f"{evidence.content[:100]}..." if len(evidence.content) > 100 else evidence.content
            elif detail_level == "standard":
                # Truncate to first 300 characters
                content = f"{evidence.content[:300]}..." if len(evidence.content) > 300 else evidence.content
            else:  # detailed
                # Include full content
                content = evidence.content
                
            entry += f"Content: {content}\n\n"
            evidence_text.append(entry)
            
        return "\n".join(evidence_text)
    
    async def generate_verdict(self, claim: Claim, evidence: List[Evidence], 
                         explanation_detail: Optional[Literal["brief", "standard", "detailed"]] = None,
                         citation_style: Optional[Literal["inline", "footnote", "academic"]] = None,
                         include_alternative_perspectives: Optional[bool] = None) -> Verdict:
        """
        Generate a verdict for the claim based on evidence.
        
        Args:
            claim: The claim to generate a verdict for
            evidence: List of evidence pieces related to the claim
            explanation_detail: Level of detail for the explanation (brief, standard, detailed)
            citation_style: Style for citing sources (inline, footnote, academic)
            include_alternative_perspectives: Whether to include alternative viewpoints
            
        Returns:
            Verdict: A verdict with explanation and sources
        """
        # Use provided parameters or instance defaults
        explanation_detail = explanation_detail or self.explanation_detail
        citation_style = citation_style or self.citation_style
        if include_alternative_perspectives is None:
            include_alternative_perspectives = self.include_alternative_perspectives
            
        # Calculate confidence score based on evidence
        confidence_score = self._calculate_confidence_score(claim.text, evidence)
        
        # Format evidence based on detail level
        formatted_evidence = self._format_evidence_for_prompt(evidence, explanation_detail)
        
        # Format citations
        citations = self._format_citations(evidence, citation_style)
        
        # Create the prompt for verdict generation
        prompt = f"""
        CLAIM: {claim.text}
        
        EVIDENCE:
        {formatted_evidence}
        
        GUIDELINES:
        - Explanation detail level: {explanation_detail}
        - Citation style: {citation_style}
        - Include alternative perspectives: {"Yes" if include_alternative_perspectives else "No"}
        - Assign a confidence score around {confidence_score:.2f} unless you have strong reasons to change it
        
        Based on the evidence above, determine if the claim is true, false, partially true, or unverifiable.
        Provide a {'brief' if explanation_detail == 'brief' else 'detailed'} explanation with appropriate citations.
        """
        
        logger.info(f"Generating verdict for claim: {claim.text[:50]}...")
        
        try:
            # Execute the agent
            result = await Runner.run(self.agent, prompt)
            
            # Get the output verdict
            verdict = result.output
            
            # Update sources with formatted citations
            verdict.sources = citations
            
            # Log verdict generation
            logger.info(f"Generated verdict: {verdict.verdict} with confidence {verdict.confidence:.2f}")
            
            # Update token usage tracking
            if hasattr(result, "usage") and result.usage:
                self.model_manager._update_token_usage({"usage": result.usage})
                
            return verdict
            
        except Exception as e:
            logger.error(f"Error generating verdict: {str(e)}", exc_info=True)
            raise 