import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.utils.db import db_manager

async def test_embedding():
    load_dotenv()
    
    # Test embedding generation
    text = "The sky is blue"
    print(f"Testing embedding for: '{text}'")
    
    embedding = await db_manager.generate_embedding(text)
    
    if embedding:
        print(f"✅ Embedding generated successfully")
        print(f"📏 Embedding dimension: {len(embedding)}")
        print(f"🔢 First 5 values: {embedding[:5]}")
        print(f"🔢 Last 5 values: {embedding[-5:]}")
    else:
        print("❌ Failed to generate embedding")

if __name__ == "__main__":
    asyncio.run(test_embedding())