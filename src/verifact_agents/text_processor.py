"""Text processing utilities for VeriFact.

This module provides text preprocessing, cleaning, and entity extraction functionality
using spaCy for natural language processing tasks.
"""

import re
import spacy

class TextProcessor:
    """Handles text preprocessing, sentence splitting, and entity extraction using spaCy."""
    def __init__(self):
        """Initialize the text processor with spaCy model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            # If model not found, download it
            spacy.cli.download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

    def preprocess_text(self, text: str) -> str:
        """Clean and normalize input text."""
        if not text or not isinstance(text, str):
            return ""
        # Basic cleaning
        text = text.strip()
        # Remove extra whitespace
        text = " ".join(text.split())
        # Normalize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:\'"-]', '', text)
        return text

    def split_sentences(self, text: str) -> list[str]:
        """Split text into sentences using spaCy."""
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents]

    def extract_entities(self, text: str) -> list[dict]:
        """Extract named entities from text using spaCy."""
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
        return entities

    def normalize_text(self, text: str) -> str:
        """Normalize text to a standard format.
        
        This function:
        1. Removes extra whitespace
        2. Normalizes quotes
        3. Handles special characters and dashes
        4. Ensures proper sentence ending
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Basic cleaning
        text = text.strip()
        
        # Handle special characters and dashes
        # Replace em dash, en dash, and other dash variants with a space
        text = re.sub(r'[—–−]', ' ', text)
        
        # Remove extra whitespace (including any created by dash replacement)
        text = " ".join(text.split())
        
        # Normalize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        
        # Remove other special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:\'"-]', '', text)
        
        # Ensure proper sentence ending
        if text and text[-1] not in ".!?":
            text += "."
            
        return text
