"""
Agent factory for creating and configuring agent instances.

This module provides a centralized factory for creating configured agent instances,
ensuring proper dependency injection and encapsulation.
"""

from typing import Any, Dict, Optional, TypeVar, cast

# Import concrete implementations (will be replaced with actual implementations)
# These imports should be updated to point to your actual implementations
from src.agents.claim_detector.detector import ClaimDetectorImpl
from src.agents.evidence_hunter.hunter import EvidenceHunter as EvidenceHunterImpl
from src.agents.interfaces import (
    ClaimDetector,
    EvidenceHunter,
    IClaimDetector,
    IEvidenceHunter,
    IVerdictWriter,
    VerdictWriter,
)
from src.agents.verdict_writer.writer import VerdictWriter as VerdictWriterImpl

# Type variable for agent types
T = TypeVar('T')


class AgentFactory:
    """
    Factory for creating agent instances with proper dependency injection.
    
    This factory provides a centralized place for agent creation, configuration,
    and dependency injection. It ensures that agent implementations are properly
    isolated from each other and dependencies are explicit.
    """
    
    @staticmethod
    def create_claim_detector(config: Optional[Dict[str, Any]] = None) -> ClaimDetector:
        """
        Create a configured ClaimDetector instance.
        
        Args:
            config: Optional configuration dictionary for the claim detector
            
        Returns:
            A configured ClaimDetector instance
        """
        config = config or {}
        model_name = config.get("model_name")
        return cast(ClaimDetector, ClaimDetectorImpl(model_name=model_name))
    
    @staticmethod
    def create_evidence_hunter(config: Optional[Dict[str, Any]] = None) -> EvidenceHunter:
        """
        Create a configured EvidenceHunter instance.
        
        Args:
            config: Optional configuration dictionary for the evidence hunter
            
        Returns:
            A configured EvidenceHunter instance
        """
        config = config or {}
        model_name = config.get("model_name")
        return cast(EvidenceHunter, EvidenceHunterImpl(model_name=model_name))
    
    @staticmethod
    def create_verdict_writer(config: Optional[Dict[str, Any]] = None) -> VerdictWriter:
        """
        Create a configured VerdictWriter instance.
        
        Args:
            config: Optional configuration dictionary for the verdict writer
            
        Returns:
            A configured VerdictWriter instance
        """
        config = config or {}
        model_name = config.get("model_name")
        explanation_detail = config.get("explanation_detail", "standard")
        citation_style = config.get("citation_style", "inline")
        include_alternative_perspectives = config.get("include_alternative_perspectives", True)
        
        return cast(VerdictWriter, VerdictWriterImpl(
            model_name=model_name,
            explanation_detail=explanation_detail,
            citation_style=citation_style,
            include_alternative_perspectives=include_alternative_perspectives
        ))
    
    @staticmethod
    def create_agent(agent_type: str, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Create an agent of the specified type with the given configuration.
        
        Args:
            agent_type: The type of agent to create ("claim_detector", "evidence_hunter", "verdict_writer")
            config: Optional configuration dictionary for the agent
            
        Returns:
            A configured agent instance
            
        Raises:
            ValueError: If the agent type is not recognized
        """
        config = config or {}
        
        if agent_type == "claim_detector":
            return AgentFactory.create_claim_detector(config)
        elif agent_type == "evidence_hunter":
            return AgentFactory.create_evidence_hunter(config)
        elif agent_type == "verdict_writer":
            return AgentFactory.create_verdict_writer(config)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    # Legacy factory methods for backward compatibility
    
    @staticmethod
    def create_legacy_claim_detector(config: Optional[Dict[str, Any]] = None) -> IClaimDetector:
        """Create a legacy IClaimDetector instance."""
        return cast(IClaimDetector, AgentFactory.create_claim_detector(config))
    
    @staticmethod
    def create_legacy_evidence_hunter(config: Optional[Dict[str, Any]] = None) -> IEvidenceHunter:
        """Create a legacy IEvidenceHunter instance."""
        return cast(IEvidenceHunter, AgentFactory.create_evidence_hunter(config))
    
    @staticmethod
    def create_legacy_verdict_writer(config: Optional[Dict[str, Any]] = None) -> IVerdictWriter:
        """Create a legacy IVerdictWriter instance."""
        return cast(IVerdictWriter, AgentFactory.create_verdict_writer(config)) 