"""Unit tests for the claim detection system components. Testing claim detection,
claim rules, and text processing."""

import pytest
from verifact_agents.text_processor import TextProcessor
from verifact_agents.claim_rules import ClaimRules, calculate_scores
from verifact_agents.claim_detector import process_claims, Claim, calculate_confidence

# Test constants
TEST_SENTENCE = "The Earth is round."

@pytest.fixture
def text_processor_fixture():
    """Provide a TextProcessor instance for testing."""
    return TextProcessor()

@pytest.fixture
def processed_text_fixture(text_processor_fixture):
    """Fixture that provides the processed version of our test sentence."""
    return text_processor_fixture.normalize_text(TEST_SENTENCE)

class TestTextProcessor:
    """Tests for the TextProcessor component."""

    def test_normalize_text(self, text_processor_fixture):
        """Test that text is properly normalized.
        
        Tests various text normalization scenarios including:
        - Extra whitespace handling
        - Quote normalization
        - Special character removal
        - Sentence ending
        """
        # Test basic normalization with extra whitespace
        assert text_processor_fixture.normalize_text("  The   Earth   is   round  ") == "The Earth is round."
        
        # Test quote normalization
        assert text_processor_fixture.normalize_text('"The Earth" is round') == '"The Earth" is round.'
        assert text_processor_fixture.normalize_text("'The Earth' is round") == "'The Earth' is round."
        
        # Test special character handling
        assert text_processor_fixture.normalize_text("The Earth...is round!") == "The Earth...is round!"
        assert text_processor_fixture.normalize_text("The Earth—is round") == "The Earth is round."
        
        # Test newlines and tabs
        assert text_processor_fixture.normalize_text("The Earth\nis round") == "The Earth is round."
        assert text_processor_fixture.normalize_text("The Earth\tis round") == "The Earth is round."
        
        # Test empty and whitespace-only strings
        assert text_processor_fixture.normalize_text("") == ""
        assert text_processor_fixture.normalize_text("   ") == ""
        assert text_processor_fixture.normalize_text("\n\t") == ""
        
        # Test sentence ending
        assert text_processor_fixture.normalize_text("The Earth is round") == "The Earth is round."
        assert text_processor_fixture.normalize_text("The Earth is round!") == "The Earth is round!"
        assert text_processor_fixture.normalize_text("The Earth is round?") == "The Earth is round?"

    def test_extract_entities(self, text_processor_fixture, processed_text_fixture):
        """Test entity extraction from our test sentence."""
        entities = text_processor_fixture.extract_entities(processed_text_fixture)
        assert len(entities) > 0
        # Check that "Earth" is recognized as an entity
        assert any(entity["text"] == "Earth" for entity in entities)
        
    def test_split_sentences(self, text_processor_fixture):
        """Test sentence splitting with our test sentence."""
        sentences = text_processor_fixture.split_sentences(TEST_SENTENCE)
        assert len(sentences) == 1
        assert sentences[0] == TEST_SENTENCE

class TestClaimRules:
    """Tests for the ClaimRules component."""
    
    def test_domain_detection(self, processed_text_fixture):
        """Test that our sentence is properly classified into a domain."""
        # Check all rules to see which domain matches
        matching_domains = set()
        for rule in ClaimRules.get_default_rules():
            if rule.pattern.search(processed_text_fixture.lower()):
                matching_domains.add(rule.domain)
        
        # Our sentence should match either 'nature' or 'general' domain
        assert matching_domains.intersection({'nature', 'general'})
        
    def test_score_calculation(self, processed_text_fixture):
        """Test score calculation for our test sentence."""
        # Test with both possible domains
        for domain in ['nature', 'general']:
            specificity, public_interest, impact, check_worthiness = calculate_scores(
                processed_text_fixture, domain
            )
            # Verify all scores are within valid range
            assert all(0.0 <= score <= 1.0 for score in [
                specificity, public_interest, impact, check_worthiness
            ])
            # For nature domain, we expect higher scores
            if domain == 'nature':
                assert specificity >= 0.7
                assert public_interest >= 0.6
                assert impact >= 0.5

class TestClaimDetector:
    """Tests for the main ClaimDetector component."""
    
    @pytest.mark.asyncio
    async def test_process_claims(self, processed_text_fixture):
        """Test the complete claim processing pipeline."""
        claims = await process_claims(TEST_SENTENCE)

        # Verify we got exactly one claim
        assert len(claims) == 1
        claim = claims[0]

        # Verify claim structure
        assert isinstance(claim, Claim)
        assert claim.text == processed_text_fixture
        assert claim.domain in ['nature', 'general']
        assert hasattr(claim, 'context')  # Verify context field exists
        assert isinstance(claim.context, str)  # Verify context is a string

        # Verify all scores are present and valid
        assert 0.0 <= claim.check_worthiness <= 1.0
        assert 0.0 <= claim.specificity_score <= 1.0
        assert 0.0 <= claim.public_interest_score <= 1.0
        assert 0.0 <= claim.impact_score <= 1.0
        assert 0.0 <= claim.confidence <= 1.0

        # Verify entities
        assert len(claim.entities) > 0
        assert any("Earth" in entity for entity in claim.entities)

    def test_confidence_calculation(self, processed_text_fixture):
        """Test confidence calculation for our test sentence."""
        # Test with both possible domains
        for domain in ['nature', 'general']:
            confidence = calculate_confidence(
                normalized_text=processed_text_fixture,
                domain=domain,
                entities=["Earth"],
                specificity=0.7
            )
            assert 0.0 <= confidence <= 1.0
            # Nature domain should have higher confidence
            if domain == 'nature':
                assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in claim processing."""
        # Test empty input
        with pytest.raises(ValueError):
            await process_claims("")

        # Test None input
        with pytest.raises(ValueError):
            await process_claims(None)
