"""
UI components for the VeriFact web interface.

This module contains functions for rendering UI components in the Chainlit interface.
"""

import datetime
import chainlit as cl
from typing import Dict, List, Any, Optional

from src.models.feedback import Feedback


async def create_feedback_form(fact_check_id: str, claim_text: str) -> None:
    """
    Create a feedback form for a fact-checked claim.
    
    Args:
        fact_check_id: Unique ID for the fact-check
        claim_text: The text of the claim that was fact-checked
    """
    # Create select for accuracy rating
    accuracy_select = cl.Select(
        id=f"accuracy_{fact_check_id}",
        label="Accuracy of the verdict",
        values=[
            cl.SelectOption(value="very_accurate", label="Very Accurate"),
            cl.SelectOption(value="somewhat_accurate", label="Somewhat Accurate"),
            cl.SelectOption(value="neutral", label="Neutral"),
            cl.SelectOption(value="somewhat_inaccurate", label="Somewhat Inaccurate"),
            cl.SelectOption(value="very_inaccurate", label="Very Inaccurate"),
        ],
        initial_value="neutral"
    )
    
    # Create select for helpfulness rating
    helpfulness_select = cl.Select(
        id=f"helpfulness_{fact_check_id}",
        label="Helpfulness of the fact-check",
        values=[
            cl.SelectOption(value="very_helpful", label="Very Helpful"),
            cl.SelectOption(value="somewhat_helpful", label="Somewhat Helpful"),
            cl.SelectOption(value="neutral", label="Neutral"),
            cl.SelectOption(value="somewhat_unhelpful", label="Somewhat Unhelpful"),
            cl.SelectOption(value="very_unhelpful", label="Very Unhelpful"),
        ],
        initial_value="neutral"
    )
    
    # Create text area for additional comments
    comments_text = cl.Textarea(
        id=f"comments_{fact_check_id}",
        label="Additional Comments",
        placeholder="Please provide any additional feedback about this fact-check...",
        tooltip="Optional comments about the fact-check"
    )
    
    # Create submit button
    submit_button = cl.Action(
        name="Submit Feedback",
        value=fact_check_id,
        id=f"feedback_{fact_check_id}",
        label="Submit Feedback"
    )
    
    # Create feedback form container
    await cl.Message(
        content=f"### Feedback Form\nPlease rate the fact-check for the claim:\n*\"{claim_text}\"*",
        elements=[accuracy_select, helpfulness_select, comments_text],
        actions=[submit_button]
    ).send()


async def create_claim_cards(claims: List[Dict[str, Any]], show_confidence: bool = True) -> None:
    """
    Create cards displaying claim information.
    
    Args:
        claims: List of claims with their properties
        show_confidence: Whether to display confidence scores
    """
    for i, claim in enumerate(claims):
        # Format the claim card content
        claim_content = f"### Claim {i+1}\n\n**Text:** {claim['text']}\n\n"
        
        if show_confidence and 'check_worthiness' in claim:
            confidence_str = f"{claim['check_worthiness'] * 100:.1f}%" if claim['check_worthiness'] else "N/A"
            claim_content += f"**Check-worthiness:** {confidence_str}\n\n"
        
        if 'domain' in claim:
            claim_content += f"**Domain:** {claim['domain']}\n\n"
        
        if 'entities' in claim and claim['entities']:
            claim_content += "**Key Entities:**\n"
            for entity in claim['entities'][:5]:  # Show only top 5 entities
                entity_type = entity.get('type', 'unknown').replace('_', ' ').title()
                claim_content += f"- {entity.get('text', 'Unknown')}: {entity_type}\n"
            claim_content += "\n"
        
        # Send the claim card
        await cl.Message(content=claim_content).send()


async def create_evidence_display(evidence_list: List[Dict[str, Any]], 
                                 detailed: bool = True, 
                                 show_confidence: bool = True) -> str:
    """
    Create markdown content displaying evidence for a claim.
    
    Args:
        evidence_list: List of evidence items
        detailed: Whether to show detailed evidence
        show_confidence: Whether to display confidence scores
    
    Returns:
        Formatted markdown string with evidence display
    """
    if not evidence_list:
        return "*No evidence found*"
    
    evidence_content = ""
    
    for i, evidence in enumerate(evidence_list):
        relevance = evidence.get('relevance', 0) * 100
        relevance_icon = "🟢" if relevance > 75 else "🟡" if relevance > 50 else "🔴"
        
        # Source formatting
        source = evidence.get('source', 'Unknown source')
        source_url = evidence.get('source_url', '')
        source_date = evidence.get('publication_date', '')
        if source_date:
            try:
                # Try to parse the date to a more readable format
                if isinstance(source_date, str):
                    source_date = datetime.datetime.fromisoformat(source_date.replace('Z', '+00:00'))
                source_date_str = source_date.strftime('%b %d, %Y')
            except:
                source_date_str = source_date
        else:
            source_date_str = ''
        
        # Source line with URL if available
        if source_url:
            source_line = f"**Source:** [{source}]({source_url})"
        else:
            source_line = f"**Source:** {source}"
        
        if source_date_str:
            source_line += f" • {source_date_str}"
        
        # Evidence content
        if detailed:
            evidence_content += f"### Evidence {i+1} {relevance_icon}\n\n"
            evidence_content += f"{source_line}\n\n"
            
            if show_confidence and 'relevance' in evidence:
                evidence_content += f"**Relevance:** {relevance:.1f}%\n\n"
            
            # Add the evidence text
            evidence_content += f"{evidence.get('text', 'No text available')}\n\n"
            
            # Add a separator except for the last item
            if i < len(evidence_list) - 1:
                evidence_content += "---\n\n"
        else:
            # Simple format for non-detailed view
            evidence_content += f"- {relevance_icon} **{source}**: "
            evidence_content += f"{evidence.get('text', 'No text available')[:100]}...\n"
    
    return evidence_content


async def create_verdict_display(verdict: Dict[str, Any], 
                                show_confidence: bool = True) -> str:
    """
    Create markdown content displaying a verdict for a claim.
    
    Args:
        verdict: The verdict data
        show_confidence: Whether to display confidence scores
    
    Returns:
        Formatted markdown string with verdict display
    """
    # Get the verdict rating and determine the emoji
    rating = verdict.get('rating', 'Unknown')
    rating_emoji = "✅" if rating == "True" else "❌" if rating == "False" else "⚠️" if rating == "Partially True" else "❓"
    
    verdict_content = f"## Verdict: {rating_emoji} {rating}\n\n"
    
    # Add confidence score if available and requested
    if show_confidence and 'confidence' in verdict:
        confidence = verdict.get('confidence', 0) * 100
        verdict_content += f"**Confidence:** {confidence:.1f}%\n\n"
    
    # Add explanation
    verdict_content += f"{verdict.get('explanation', 'No explanation available')}\n\n"
    
    # Add sources summary if available
    if 'sources_summary' in verdict and verdict['sources_summary']:
        verdict_content += f"**Sources Summary:** {verdict['sources_summary']}\n\n"
    
    # Add limitations if available
    if 'limitations' in verdict and verdict['limitations']:
        verdict_content += f"**Limitations:** {verdict['limitations']}\n\n"
    
    return verdict_content 