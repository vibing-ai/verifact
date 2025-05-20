"""
Entity extraction for the ClaimDetector agent.

This module handles the extraction and classification of named entities from claims.
"""

import re
from typing import List, Dict, Any, Optional
from openai.agents import Agent

from src.utils.logger import get_component_logger, log_performance
from src.utils.cache import entity_cache
from src.agents.claim_detector.models import Entity, EntityType


class EntityExtractor:
    """Entity extraction functionality for the ClaimDetector."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the EntityExtractor.
        
        Args:
            model_name: Optional name of the model to use
        """
        # Get component-specific logger
        self.logger = get_component_logger("entity_extractor")
        self.logger.debug("Initializing EntityExtractor")
        
        # Cache for entities
        self.entity_cache = entity_cache
        
        # The model name to use, will be set by detector
        self.model_name = model_name
        
        # Agent will be created on demand by detector
        self.agent = None
    
    def set_agent(self, agent: Agent):
        """
        Set the entity extraction agent.
        
        Args:
            agent: The Agent instance to use for entity extraction
        """
        self.agent = agent
    
    @log_performance(operation="extract_entities", level="debug")
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract named entities from text using pattern matching and NLP.
        
        Args:
            text: The text to extract entities from
            
        Returns:
            List of Entity objects
        """
        # Check cache first
        cache_key = f"entities:{hash(text)}"
        cached_entities = self.entity_cache.get(cache_key)
        if cached_entities:
            self.logger.debug(f"Cache hit for entities from text: {text[:30]}...")
            return cached_entities
        
        entities = []
        
        # Extract dates with regex
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DD/MM/YYYY or MM/DD/YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY/MM/DD
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b',
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b',
            r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
            r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',
        ]
        
        for pattern in date_patterns:
            for match in re.finditer(pattern, text):
                date_text = match.group(0)
                entities.append(Entity(
                    text=date_text,
                    type=EntityType.DATE,
                    relevance=1.0
                ))
        
        # Extract money amounts
        money_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
            r'\d+(?:,\d{3})*(?:\.\d{2})?\s+(?:dollars|USD|euros|EUR|pounds|GBP)',
        ]
        
        for pattern in money_patterns:
            for match in re.finditer(pattern, text):
                money_text = match.group(0)
                entities.append(Entity(
                    text=money_text,
                    type=EntityType.MONEY,
                    relevance=1.0
                ))
        
        # Extract percentages
        percent_patterns = [
            r'\d+(?:\.\d+)?\s*%',
            r'\d+(?:\.\d+)?\s+percent',
        ]
        
        for pattern in percent_patterns:
            for match in re.finditer(pattern, text):
                percent_text = match.group(0)
                entities.append(Entity(
                    text=percent_text,
                    type=EntityType.PERCENT,
                    relevance=1.0
                ))
        
        # Extract quantities with numbers
        number_patterns = [
            r'\b\d+(?:,\d{3})*(?:\.\d+)?\b',
        ]
        
        for pattern in number_patterns:
            for match in re.finditer(pattern, text):
                number_text = match.group(0)
                # Skip if already part of a date, money or percent
                skip = False
                for entity in entities:
                    if number_text in entity.text:
                        skip = True
                        break
                
                if not skip:
                    entities.append(Entity(
                        text=number_text,
                        type=EntityType.NUMBER,
                        relevance=0.8  # Lower relevance for standalone numbers
                    ))
        
        # Use the entity agent for more complex entities if available
        if self.agent:
            try:
                agent_entities = self.agent.run(text)
                
                # Merge regex-based entities with agent-based entities,
                # but avoid duplicates
                existing_texts = {entity.text for entity in entities}
                for agent_entity in agent_entities:
                    if agent_entity.text not in existing_texts:
                        entities.append(agent_entity)
            except Exception as e:
                self.logger.warning(f"Error extracting entities with agent: {str(e)}")
        
        # Cache the results
        self.entity_cache.set(cache_key, entities)
        
        return entities
    
    def normalize_entity(self, entity: Entity) -> Entity:
        """
        Normalize an entity to its canonical form.
        
        Args:
            entity: The entity to normalize
            
        Returns:
            Entity with normalized_text field filled
        """
        # Make a copy of the entity
        result = entity.copy()
        
        # Normalize based on entity type
        if entity.type == EntityType.DATE:
            # Try to normalize date format (this is a simplified example)
            # In a real implementation, this would parse and reformat dates
            date_text = entity.text
            # Just strip extra spaces as a minimal normalization
            normalized = ' '.join(date_text.split())
            result.normalized_text = normalized
            
        elif entity.type == EntityType.MONEY:
            # Normalize currency amounts
            money_text = entity.text
            # Remove currency symbols, commas, and convert to standard format
            cleaned = money_text.replace('$', '').replace(',', '')
            # Extract the numeric value
            match = re.search(r'\d+(\.\d+)?', cleaned)
            if match:
                amount = float(match.group(0))
                result.normalized_text = f"{amount:.2f}"
            
        elif entity.type == EntityType.PERCENT:
            # Normalize percentages
            percent_text = entity.text
            # Extract the numeric value
            match = re.search(r'\d+(\.\d+)?', percent_text)
            if match:
                value = float(match.group(0))
                result.normalized_text = f"{value:.1f}%"
            
        elif entity.type == EntityType.NUMBER:
            # Normalize numbers
            number_text = entity.text
            # Remove commas and convert to standard format
            cleaned = number_text.replace(',', '')
            try:
                # Convert to numeric value
                value = float(cleaned)
                # Use integer format if it's a whole number
                if value.is_integer():
                    result.normalized_text = str(int(value))
                else:
                    result.normalized_text = str(value)
            except ValueError:
                # If conversion fails, keep original
                pass
            
        else:
            # For other entity types, just clean up whitespace
            if entity.text:
                result.normalized_text = ' '.join(entity.text.split())
        
        return result 