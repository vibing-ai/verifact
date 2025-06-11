from agents import Agent as OpenAIAgent
from src.verifact_agents import ClaimDetector

def test_imports():
    print("Successfully imported OpenAI Agent")
    print("Successfully imported VeriFact ClaimDetector")

def test_agent_imports():
    """Test that agent classes can be imported successfully."""
    assert OpenAIAgent is not None
    assert ClaimDetector is not None

if __name__ == "__main__":
    test_imports() 