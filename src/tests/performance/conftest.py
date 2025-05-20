"""
Pytest configuration for performance tests.

This module contains fixtures specific to performance and benchmark tests.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def benchmark_claims():
    """Return a set of benchmark claims for performance testing."""
    return [
        "The Earth is approximately 4.54 billion years old.",
        "Water covers about 71% of the Earth's surface.",
        "Mount Everest is the highest mountain on Earth with a height of 8,848.86 meters above sea level.",
        "The human genome contains approximately 20,000-25,000 genes.",
        "The average global temperature has risen by about 1.1°C since the pre-industrial period.",
        "The speed of light in a vacuum is exactly 299,792,458 meters per second.",
        "The First World War lasted from 1914 to 1918.",
        "The United States Declaration of Independence was adopted on July 4, 1776.",
        "The Great Wall of China is approximately 21,196 kilometers long.",
        "The Mona Lisa was painted by Leonardo da Vinci."
    ]


@pytest.fixture
def benchmark_texts():
    """Return a set of longer benchmark texts for performance testing."""
    return [
        # Scientific text
        """The Earth is approximately 4.54 billion years old, with an error range of about 50 million years. 
        This age has been determined through radiometric dating of meteorites and the oldest-known Earth rocks.
        Water covers about 71% of the Earth's surface, with oceans holding about 96.5% of all Earth's water.""",
        
        # Historical text
        """The First World War, also known as the Great War, lasted from 1914 to 1918 and involved many of the 
        world's nations. The United States Declaration of Independence was adopted by the Continental Congress 
        on July 4, 1776, announcing that the thirteen American colonies were no longer subject to British rule.""",
        
        # Mixed claims text
        """The human genome contains approximately 20,000-25,000 genes, far fewer than initially predicted. 
        The average global temperature has risen by about 1.1°C since the pre-industrial period, primarily 
        due to human activities. Mount Everest is the highest mountain on Earth with a height of 8,848.86 
        meters above sea level. I personally think that climate change is the biggest threat we face today."""
    ]


@pytest.fixture
def benchmark_config():
    """Return a configuration for benchmark tests."""
    return {
        "iterations": 5,
        "warm_up": 1,
        "timeout": 300,  # seconds
        "models": [
            {
                "name": "gpt-3.5-turbo",
                "provider": "openai",
                "temperature": 0.1
            },
            {
                "name": "gpt-4-turbo",
                "provider": "openai",
                "temperature": 0.1
            }
        ]
    }

# Add performance-specific fixtures here 