import pytest
from pydantic import ValidationError

# Adjust the import path based on your project structure.
# This assumes 'src' is in your PYTHONPATH or you're running pytest from the project root.
from verifact_agents.claim_detector import Claim, claim_detector_agent, PROMPT

# --- Fixtures ---
# Fixtures are a way to provide data or set up resources for your tests.

@pytest.fixture
def valid_claim_data() -> dict:
    """Provides a dictionary with valid data for a Claim instance."""
    return {
        "text": "The Earth is round.",
        "normalized_text": "The Earth has a spherical shape.",
        "check_worthiness_score": 0.9,
        "specificity_score": 0.8,
        "public_interest_score": 0.7,
        "impact_score": 0.6,
        "detection_confidence": 0.95,
        "domain": "Science",
        "entities": [{"text": "Earth", "type": "Planet"}],
        "compound_claim_parts": None,
        "rank": 1
    }

# --- Tests for the Claim Pydantic Model ---

def test_claim_creation_valid_data(valid_claim_data):
    """Test that a Claim can be successfully created with valid data."""
    try:
        claim = Claim(**valid_claim_data)
        # Check a few key fields to ensure data is loaded correctly
        assert claim.text == valid_claim_data["text"]
        assert claim.normalized_text == valid_claim_data["normalized_text"]
        assert claim.check_worthiness_score == valid_claim_data["check_worthiness_score"]
        assert claim.rank == valid_claim_data["rank"]
        assert claim.entities == valid_claim_data["entities"]
    except ValidationError as e:
        pytest.fail(f"Claim creation failed with valid data: {e}")

def test_claim_missing_required_field(valid_claim_data):
    """Test that ValidationError is raised if a required field (e.g., 'text') is missing."""
    invalid_data = valid_claim_data.copy()
    del invalid_data["text"]  # 'text' is a required field

    # pytest.raises is a context manager to check for expected exceptions
    with pytest.raises(ValidationError) as excinfo:
        Claim(**invalid_data)
    
    # Optionally, you can inspect the exception details
    assert "text" in str(excinfo.value).lower() # Check that the error message mentions 'text'
    assert "field required" in str(excinfo.value).lower()

@pytest.mark.parametrize("score_field,invalid_value", [
    ("check_worthiness_score", -0.1),
    ("check_worthiness_score", 1.1),
    ("specificity_score", -0.5),
    ("specificity_score", 1.5),


    ("public_interest_score", -0.01),
    ("public_interest_score", 2.0),
    ("impact_score", -1.0),
    ("impact_score", 1.0001),
    ("detection_confidence", -0.2),
    ("detection_confidence", 1.2),
])
def test_claim_score_out_of_range(valid_claim_data, score_field, invalid_value):
    """Test that scores must be between 0.0 and 1.0."""
    invalid_data = valid_claim_data.copy()
    invalid_data[score_field] = invalid_value
    
    with pytest.raises(ValidationError) as excinfo:
        Claim(**invalid_data)
    
    # Check that the error message mentions the problematic field
    assert score_field in str(excinfo.value)

def test_claim_default_values(valid_claim_data):
    """Test default values for optional fields like 'entities' and 'compound_claim_parts'."""
    data = valid_claim_data.copy()
    del data["entities"]             # entities has default_factory=[]
    del data["compound_claim_parts"] # compound_claim_parts has default=None
    print("====>data:", data)

    claim = Claim(**data)
    
    assert claim.entities == []
    assert claim.compound_claim_parts is None

def test_claim_extra_fields_forbidden(valid_claim_data):
    """Test that extra fields are not allowed due to model_config = {'extra': 'forbid'}."""
    data_with_extra = valid_claim_data.copy()
    data_with_extra["unexpected_field"] = "some_value"
    
    with pytest.raises(ValidationError) as excinfo:
        Claim(**data_with_extra)

    assert "unexpected_field" in str(excinfo.value)
    assert "extra inputs are not permitted" in str(excinfo.value).lower()

def test_claim_invalid_data_type_for_field(valid_claim_data):
    """Test that providing an incorrect data type for a field raises ValidationError."""
    invalid_data = valid_claim_data.copy()
    invalid_data["rank"] = "not-an-integer" # rank should be an int
    
    with pytest.raises(ValidationError) as excinfo:
        Claim(**invalid_data)
    assert "rank" in str(excinfo.value) # Check that the error message mentions 'rank'

# --- Tests for the claim_detector_agent Instance ---

def test_claim_detector_agent_instantiation():
    """Test that the claim_detector_agent is instantiated and has basic properties."""
    assert claim_detector_agent is not None
    assert claim_detector_agent.name == "ClaimDetector"
    
    assert claim_detector_agent.output_type.__origin__ == list # Checks if it's a list type
    assert claim_detector_agent.output_type.__args__[0] == Claim # Checks if the list contains Claim

    # Check if instructions are loaded (at least that it's not empty)
    assert claim_detector_agent.instructions == PROMPT
    assert PROMPT.strip() != "" # Ensure the PROMPT string itself is not empty

    # Note: Testing the agent's actual processing (which calls an LLM)
    # is an integration test and would require mocking os.getenv or the Agent's call method.
    # For an MVP unit test, checking instantiation and configuration is a good start.

# You can add more tests here, for example:
# - Test specific constraints on 'entities' (e.g., must be list of dicts with 'text' and 'type')
# - Test 'compound_claim_parts' (e.g., must be list of strings if not None)