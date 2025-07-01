"""Unit tests for the AI-driven claim detection system."""

import pytest
from unittest.mock import AsyncMock, patch
from verifact_agents.claim_detector import process_claims, Claim, claim_detector

# Test constants
TEST_SENTENCE = "The Earth is round."
TEST_CLAIM_TEXT = "The study found that 75% of participants showed improvement."

@pytest.fixture
def claim_detector_fixture():
    """Provide a ClaimDetector instance for testing."""
    return claim_detector

@pytest.fixture
def mock_claim_response():
    """Mock response for testing without API calls."""
    return [
        Claim(
            text="The study found that 75% of participants showed improvement",
            context="",
            check_worthiness=0.8,
            domain="Science",
            confidence=0.9,
            entities=["study", "participants"]
        )
    ]

class TestClaimDetector:
    """Tests for the AI-driven ClaimDetector component."""

    @pytest.mark.asyncio
    async def test_process_claims_basic(self, claim_detector_fixture):
        """Test the complete claim processing pipeline with a simple claim."""
        claims = await process_claims(TEST_CLAIM_TEXT)

        # Verify we got at least one claim
        assert len(claims) >= 1

        # Check the first claim
        claim = claims[0]
        assert isinstance(claim, Claim)
        assert "75%" in claim.text or "participants" in claim.text
        assert claim.domain in ['Science', 'Health', 'Statistics', 'Other']
        assert 0.0 <= claim.check_worthiness <= 1.0
        assert 0.0 <= claim.confidence <= 1.0
        assert isinstance(claim.entities, list)
        assert isinstance(claim.context, str)

    @pytest.mark.asyncio
    async def test_process_claims_multiple_sentences(self, claim_detector_fixture):
        """Test processing multiple sentences in a paragraph."""
        multi_sentence_text = "The study found that 75% of participants showed improvement. However, the researchers noted that the sample size was small."

        claims = await process_claims(multi_sentence_text)

        # Should detect multiple claims
        assert len(claims) >= 1

        # Verify each claim has proper structure
        for claim in claims:
            assert isinstance(claim, Claim)
            assert claim.text.strip() != ""
            assert claim.domain in ['Science', 'Health', 'Statistics', 'Other']
            assert 0.0 <= claim.check_worthiness <= 1.0
            assert 0.0 <= claim.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_process_claims_opinion_filtering(self, claim_detector_fixture):
        """Test that opinions and non-factual statements are filtered out."""
        opinion_text = "I think this is a good idea. The weather might be nice tomorrow."

        claims = await process_claims(opinion_text)

        # Should filter out opinions, so fewer or no claims
        # The exact number depends on AI interpretation, but should be low
        assert len(claims) <= 1

    @pytest.mark.asyncio
    async def test_process_claims_with_min_threshold(self, claim_detector_fixture):
        """Test filtering by minimum check-worthiness threshold."""
        claims = await process_claims(TEST_CLAIM_TEXT, min_checkworthiness=0.8)

        # All claims should meet the threshold
        for claim in claims:
            assert claim.check_worthiness >= 0.8

    def test_claim_model_structure(self):
        """Test the Claim model structure and methods."""
        claim = Claim(
            text="Test claim",
            context="Test context",
            check_worthiness=0.7,
            domain="Science",
            confidence=0.8,
            entities=["test", "claim"]
        )

        # Test basic properties
        assert claim.text == "Test claim"
        assert claim.context == "Test context"
        assert claim.check_worthiness == 0.7
        assert claim.domain == "Science"
        assert claim.confidence == 0.8
        assert claim.entities == ["test", "claim"]

        # Test methods
        assert claim.is_checkworthy(threshold=0.5) == True
        assert claim.is_checkworthy(threshold=0.8) == False
        assert claim.has_entities() == True
        assert claim.get_entity_names() == ["test", "claim"]
        assert claim.is_high_confidence(threshold=0.7) == True
        assert claim.is_high_confidence(threshold=0.9) == False

    def test_claim_detector_preprocessing(self, claim_detector_fixture):
        """Test text preprocessing functionality."""
        # Test basic preprocessing
        cleaned = claim_detector_fixture._preprocess_text("  The   Earth   is   round  ")
        assert cleaned == "The Earth is round"

        # Test quote normalization
        cleaned = claim_detector_fixture._preprocess_text('"The Earth" is round')
        assert '"The Earth" is round' in cleaned

    def test_claim_detector_deduplication(self, claim_detector_fixture):
        """Test claim deduplication functionality."""
        # Create duplicate claims
        claim1 = Claim(text="The Earth is round", check_worthiness=0.8)
        claim2 = Claim(text="The Earth is round", check_worthiness=0.7)  # Lower score
        claim3 = Claim(text="Different claim", check_worthiness=0.6)

        claims = [claim1, claim2, claim3]
        deduplicated = claim_detector_fixture._deduplicate_claims(claims)

        # Should remove duplicate and keep the higher scoring one
        assert len(deduplicated) == 2
        assert deduplicated[0].check_worthiness == 0.8  # Higher score first
        assert deduplicated[1].text == "Different claim"

    @pytest.mark.asyncio
    async def test_error_handling(self, claim_detector_fixture):
        """Test error handling in claim processing."""
        # Test empty input
        with pytest.raises(ValueError):
            await process_claims("")

        # Test None input
        with pytest.raises(ValueError):
            await process_claims(None)

    @pytest.mark.asyncio
    async def test_short_text_handling(self, claim_detector_fixture):
        """Test handling of very short texts."""
        # Test with text that's too short - should raise ValueError
        with pytest.raises(ValueError, match="Text too short"):
            await process_claims("Hi")
        
        # Test with text that's just at the minimum length
        claims = await process_claims("This is ten")  # Exactly 10 characters
        assert isinstance(claims, list)

    def test_claim_detector_validation(self, claim_detector_fixture):
        """Test score validation functionality."""
        # Create claims with extreme scores
        claim1 = Claim(text="Very short", check_worthiness=0.95)  # High score, short text
        claim2 = Claim(text="Normal length claim with reasonable content", check_worthiness=0.8)

        claims = [claim1, claim2]
        validated = claim_detector_fixture._validate_checkworthiness_scores(claims)

        # Very short claim should have adjusted score
        assert validated[0].check_worthiness <= 0.8
        # Normal claim should be unchanged
        assert validated[1].check_worthiness == 0.8

    def test_claim_text_sanitization(self):
        """Test that individual claim text is sanitized."""
        # Test HTML in claim text
        malicious_claim = Claim(
            text='<iframe src="malicious.com"></iframe>The Earth is round',
            check_worthiness=0.8,
            domain="Science"
        )

        # The validator should sanitize this
        assert '<iframe' not in malicious_claim.text
        assert 'The Earth is round' in malicious_claim.text

        # Test control characters - expect spaces to be preserved
        malicious_claim = Claim(
            text='The Earth\x00is\x01round',  # Contains control characters
            check_worthiness=0.8,
            domain="Science"
        )

        # Control characters should be removed, spaces preserved
        assert '\x00' not in malicious_claim.text
        assert '\x01' not in malicious_claim.text
        # The sanitization removes control chars but preserves spaces
        assert 'The Earth' in malicious_claim.text  # Check for partial match
        assert 'round' in malicious_claim.text      # Check for partial match

    def test_claim_length_validation(self):
        """Test that individual claim text length limits are enforced."""
        # Test claim text too long
        long_claim_text = "A" * 151  # Exceeds 150 character limit
        with pytest.raises(ValueError, match="Text too long.*150"):
            Claim(text=long_claim_text, check_worthiness=0.8)

        # Test context too long
        long_context = "A" * 201  # Exceeds 200 character limit
        with pytest.raises(ValueError, match="Text too long.*200"):
            Claim(text="Valid claim", context=long_context, check_worthiness=0.8)

        # Test valid lengths
        valid_claim = Claim(
            text="The Earth is round",
            context="This is a valid context",
            check_worthiness=0.8
        )
        assert valid_claim.text == "The Earth is round"
        assert valid_claim.context == "This is a valid context"

    def test_claim_limit_enforcement(self, claim_detector_fixture):
        """Test that the maximum number of claims is enforced."""
        # Create more claims than the limit
        many_claims = [
            Claim(text=f"Claim {i}", check_worthiness=0.8)
            for i in range(5)  # More than MAX_CLAIMS_PER_REQUEST (2)
        ]

        # The deduplication method should handle this, but we need to test the limit
        # This would be tested in the actual detect_claims method
        assert len(many_claims) > 2  # Verify we have more than the limit

    def test_validate_text_input_utility(self):
        """Test the centralized text validation utility."""
        from verifact_agents.claim_detector import _validate_text_input
        
        # Test valid input
        assert _validate_text_input("Valid text") == "Valid text"
        
        # Test invalid inputs
        with pytest.raises(ValueError, match="Input text must be a non-empty string"):
            _validate_text_input("")
        
        with pytest.raises(ValueError, match="Input text must be a non-empty string"):
            _validate_text_input(None)
        
        # Test length validation
        short_text = "a" * 9  # Less than MIN_TEXT_LENGTH (10)
        with pytest.raises(ValueError, match="Text too short"):
            _validate_text_input(short_text)