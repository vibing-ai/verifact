"""OpenRouter configuration for OpenAI client.

This module configures the OpenAI client to use OpenRouter instead of the OpenAI API.
It should be imported before any other imports that use the OpenAI client.
"""

import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Configure OpenAI client to use OpenRouter
openai.api_key = OPENROUTER_API_KEY
openai.base_url = "https://openrouter.ai/api/v1"
openai.default_headers = {
    "HTTP-Referer": "https://verifact.ai",  # Replace with your site URL
    "X-Title": "VeriFact",  # Replace with your site name
}

# Configure OpenAI Agents SDK to use OpenRouter
# This is a workaround until the SDK supports custom base URLs
os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY
os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"
