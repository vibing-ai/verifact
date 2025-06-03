"""Text processing utilities for VeriFact.

This module provides text preprocessing, cleaning, and entity extraction functionality
using spaCy for natural language processing tasks.
"""

import spacy
from typing import List
import re

class TextProcessor:
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

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using spaCy."""

        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents]

    def extract_entities(self, text: str) -> List[dict]:
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
        """Normalize text to a standard format."""
        
        text = self.preprocess_text(text)
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        # Ensure ends with period if not ending with punctuation
        if text and not text[-1] in ".!?":
            text += "."
        return text