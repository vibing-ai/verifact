"""Unit tests for the AI-driven claim detection system."""

import os
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

from verifact_agents.claim_detector import (
    MAX_CLAIMS_PER_REQUEST,
    MIN_TEXT_LENGTH,
    Claim,
    claim_detector,
    process_claims,
)

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
API_KEY = os.getenv("OPENAI_API_KEY")

# Check if API key is set
if not API_KEY:
    error_msg = "OPENAI_API_KEY not set"
    raise ValueError(error_msg)

# Test constants
VALID_LONG_ENOUGH_TEXT = "This is a valid text for processing." * 2  # ensure it's > MIN_TEXT_LENGTH
HIGH_CHECKWORTHINESS_THRESHOLD = 0.85
TEST_CHECKWORTHINESS_SCORE = 0.8
TEST_CONFIDENCE_SCORE = 0.9

# Add these constants at the top with the other constants
EXPECTED_DEDUPLICATED_COUNT = 2
HIGHER_SCORE_VALUE = 0.8


def setup_mock_agent_response(mock_runner_run, claims_to_return):
    """Helper to setup mock agent response."""
    mock_runner_run.return_value = MagicMock(
        final_output_as=MagicMock(return_value=claims_to_return)
    )


@pytest.fixture
def single_claim():
    """Provide a single test claim."""
    return Claim(
        text="The study found that 75% of participants showed improvement",
        context="This was a primary finding.",
        check_worthiness=0.8,
        domain="Science",
        confidence=0.9,
        entities=["study", "participants"],
    )


@pytest.fixture
def multiple_claims(single_claim):
    """Provide multiple test claims."""
    return [
        single_claim,
        Claim(
            text="Researchers noted the sample size was small.",
            context="A limitation mentioned in the paper.",
            check_worthiness=0.7,
            domain="Science",
            confidence=0.85,
            entities=["researchers", "sample size"],
        ),
        Claim(
            text="Company X reported $2.3 billion in revenue.",
            context="From their Q3 earnings call.",
            check_worthiness=0.9,
            domain="Business",
            confidence=0.95,
            entities=["Company X"],
        ),
    ]


def assert_valid_claim(claim, expected_text=None, expected_domain=None, expected_score=None):
    """Helper to validate claim structure."""
    assert isinstance(claim, Claim)
    if expected_text:
        assert expected_text in claim.text
    if expected_domain:
        assert claim.domain == expected_domain
    if expected_score:
        assert claim.check_worthiness == expected_score
    assert isinstance(claim.entities, list)
    assert isinstance(claim.context, str)


class TestClaimDetector:
    """Tests for the AI-driven ClaimDetector component."""

    @pytest.mark.asyncio
    @patch("verifact_agents.claim_detector.Runner.run")
    async def test_process_claims_basic(self, mock_runner_run, single_claim):
        """Test the complete claim processing pipeline with a simple claim, using mocked agent."""
        setup_mock_agent_response(mock_runner_run, [single_claim])

        claims = await process_claims(VALID_LONG_ENOUGH_TEXT)

        mock_runner_run.assert_called_once()
        assert len(claims) == 1
        assert_valid_claim(
            claims[0],
            expected_text=single_claim.text,
            expected_domain="Science",
            expected_score=0.8,
        )

    @pytest.mark.asyncio
    @patch("verifact_agents.claim_detector.Runner.run")
    async def test_process_claims_limit_enforcement(self, mock_runner_run, multiple_claims):
        """Test that MAX_CLAIMS_PER_REQUEST is enforced."""
        setup_mock_agent_response(mock_runner_run, multiple_claims)

        claims = await process_claims(VALID_LONG_ENOUGH_TEXT)

        mock_runner_run.assert_called_once()
        assert len(claims) == MAX_CLAIMS_PER_REQUEST

    @pytest.mark.asyncio
    @patch("verifact_agents.claim_detector.Runner.run")
    async def test_process_claims_opinion_filtering_mocked(self, mock_runner_run):
        """Test that opinions (empty list from agent) are handled."""
        opinion_text = "I think this is a good idea. The weather might be nice tomorrow."
        setup_mock_agent_response(mock_runner_run, [])

        claims = await process_claims(opinion_text)

        mock_runner_run.assert_called_once()
        assert len(claims) == 0

    @pytest.mark.asyncio
    @patch("verifact_agents.claim_detector.Runner.run")
    async def test_process_claims_with_min_threshold_mocked(self, mock_runner_run, multiple_claims):
        """Test filtering by minimum check-worthiness threshold with mocked agent."""
        # Return claims sorted by check_worthiness desc by the agent
        sorted_mock_claims = sorted(multiple_claims, key=lambda c: c.check_worthiness, reverse=True)
        setup_mock_agent_response(mock_runner_run, sorted_mock_claims)

        claims = await process_claims(
            VALID_LONG_ENOUGH_TEXT, min_checkworthiness=HIGH_CHECKWORTHINESS_THRESHOLD
        )

        assert len(claims) == 1  # Only "Company X reported..." (0.9)
        assert claims[0].check_worthiness >= HIGH_CHECKWORTHINESS_THRESHOLD

    def test_claim_model_structure(self, single_claim):
        """Test the Claim model structure and methods."""
        # Test basic properties
        assert single_claim.text == "The study found that 75% of participants showed improvement"
        assert single_claim.context == "This was a primary finding."
        assert single_claim.check_worthiness == TEST_CHECKWORTHINESS_SCORE
        assert single_claim.domain == "Science"
        assert single_claim.confidence == TEST_CONFIDENCE_SCORE
        assert single_claim.entities == ["study", "participants"]

        # Test methods
        assert single_claim.is_checkworthy(threshold=0.5)
        assert not single_claim.is_checkworthy(threshold=0.9)
        assert single_claim.has_entities()
        assert single_claim.get_entity_names() == ["study", "participants"]
        assert single_claim.is_high_confidence(threshold=0.7)
        assert not single_claim.is_high_confidence(threshold=0.95)

    @pytest.mark.parametrize(
        ("input_text", "expected_contains"),
        [
            ("  The   Earth   is   round  ", "The Earth is round"),
            ('"The Earth" is round', '"The Earth" is round'),
            ("Earth - round", "Earth round"),
            ("Um, the Earth, uh, is round", "the Earth, , is round"),
            ("Earth vs. Moon etc.", "Earth versus Moon etcetera"),
        ],
    )
    def test_text_preprocessing(self, input_text, expected_contains):
        """Test text preprocessing functionality."""
        # This test was missing - it tests the text preprocessing
        processed_text = claim_detector._preprocess_text(input_text)
        assert expected_contains in processed_text

    def test_claim_detector_deduplication_basic(self, multiple_claims):
        """Test basic deduplication with exact duplicates."""
        # Create duplicate claims
        duplicate_claims = [
            multiple_claims[0],  # Original
            Claim(text=multiple_claims[0].text, check_worthiness=0.7),  # Duplicate with lower score
            multiple_claims[1],  # Different claim
        ]

        deduplicated = claim_detector._deduplicate_claims(duplicate_claims)
        assert len(deduplicated) == EXPECTED_DEDUPLICATED_COUNT
        assert {claim.text for claim in deduplicated} == {
            multiple_claims[0].text,
            multiple_claims[1].text,
        }

    def test_claim_detector_deduplication_sorting(self, multiple_claims):
        """Test that deduplicated claims are sorted by check_worthiness."""
        deduplicated = claim_detector._deduplicate_claims(multiple_claims)

        # Check sorting by check_worthiness (descending)
        for i in range(len(deduplicated) - 1):
            assert deduplicated[i].check_worthiness >= deduplicated[i + 1].check_worthiness

    def test_claim_detector_deduplication_highest_score_kept(self):
        """Test that highest scoring duplicate is kept."""
        claims_in = [
            Claim(text="Duplicate", check_worthiness=0.7),
            Claim(text="Unique1", check_worthiness=0.9),
            Claim(text="Duplicate", check_worthiness=0.8),
        ]

        deduplicated = claim_detector._deduplicate_claims(claims_in)

        # Find the duplicate claim that was kept
        duplicate_claims = [c for c in deduplicated if c.text == "Duplicate"]
        assert len(duplicate_claims) == 1
        assert duplicate_claims[0].check_worthiness == HIGHER_SCORE_VALUE  # Higher score kept

    @pytest.mark.parametrize("invalid_input", ["", None, "Hi"])
    @pytest.mark.asyncio
    async def test_invalid_inputs(self, invalid_input):
        """Test various invalid inputs."""
        if len(str(invalid_input or "")) < MIN_TEXT_LENGTH:
            with pytest.raises(ValueError, match="Text too short"):
                await process_claims(invalid_input)

    @pytest.mark.asyncio
    @patch("verifact_agents.claim_detector.Runner.run")
    async def test_short_text_handling(self, mock_runner_run, single_claim):
        """Test handling of very short texts."""
        # Test with text that's just at the minimum length
        setup_mock_agent_response(mock_runner_run, [single_claim])
        claims = await process_claims("This is ten")  # Exactly 10 characters
        assert isinstance(claims, list)
        mock_runner_run.assert_called_once()

    def test_claim_text_sanitization(self):
        """Test that individual claim text is sanitized."""
        # Test HTML in claim text
        malicious_claim = Claim(
            text='<iframe src="malicious.com"></iframe>The Earth is round',
            check_worthiness=0.8,
            domain="Science",
        )

        # The validator should sanitize this
        assert "<iframe" not in malicious_claim.text
        assert "The Earth is round" in malicious_claim.text

        # Test control characters
        malicious_claim = Claim(
            text="The Earth\x00is\x01round",  # Contains control characters
            check_worthiness=0.8,
            domain="Science",
        )

        # Control characters should be removed
        assert "\x00" not in malicious_claim.text
        assert "\x01" not in malicious_claim.text
        assert "The Earth" in malicious_claim.text
        assert "round" in malicious_claim.text

        # Test other dangerous patterns
        dangerous_patterns = [
            ('<script>alert("XSS")</script>', "<script"),
            ("javascript:doSomething()", "javascript:"),
            ('prefix <iframe src="evil.com"> suffix', "<iframe"),
            ("Text with onmouseover=attack()", "onmouseover="),
            ("data:text/html,Hello There", "data:text/html"),
            ("vbscript:anotherAttack()", "vbscript:"),
        ]

        for dangerous_input, forbidden_trace in dangerous_patterns:
            full_text = f"SafePrefix {dangerous_input} SafeSuffix"
            claim = Claim(text=full_text, check_worthiness=0.5)

            # Check that the specific forbidden trace is NOT in the sanitized text
            assert forbidden_trace.lower() not in claim.text.lower(), (
                f"Forbidden trace '{forbidden_trace}' was found in sanitized text '{claim.text}' for input '{dangerous_input}'"
            )

            # Check that non-dangerous parts are preserved
            assert "SafePrefix" in claim.text
            assert "SafeSuffix" in claim.text

    @pytest.mark.parametrize(
        ("field", "value", "expected_error"),
        [
            ("text", "A" * 151, "Text too long.*150"),
            ("context", "A" * 201, "Text too long.*200"),
        ],
    )
    def test_claim_length_validation(self, field, value, expected_error):
        """Test that individual claim field length limits are enforced."""
        # Determine which claim to create based on the field
        if field == "text":

            def claim_to_create():
                return Claim(text=value, check_worthiness=0.8)
        else:

            def claim_to_create():
                return Claim(text="Valid claim", context=value, check_worthiness=0.8)

        with pytest.raises(ValueError, match=expected_error):
            claim_to_create()

    def test_valid_claim_lengths(self):
        """Test that valid claim lengths are accepted."""
        valid_claim = Claim(
            text="The Earth is round", context="This is a valid context", check_worthiness=0.8
        )
        assert valid_claim.text == "The Earth is round"
        assert valid_claim.context == "This is a valid context"

    @pytest.mark.asyncio
    async def test_real_agent_integration(self):
        """Integration test with real agent."""
        # Test factual claim
        factual_claims = await process_claims(
            "The study found that 75% of participants showed improvement."
        )
        assert len(factual_claims) > 0
        assert all(isinstance(claim, Claim) for claim in factual_claims)

        # Test opinion (should return fewer or no claims)
        opinion_claims = await process_claims("I think this is a good idea.")
        # Either empty or lower scores than factual claims
        if len(opinion_claims) > 0:
            factual_avg_score = sum(c.check_worthiness for c in factual_claims) / len(
                factual_claims
            )
            opinion_avg_score = sum(c.check_worthiness for c in opinion_claims) / len(
                opinion_claims
            )
            assert opinion_avg_score < factual_avg_score

        # Test edge case
        assert isinstance(await process_claims("This is exactly ten characters long."), list)
