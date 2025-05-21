"""Tests for the ClaimDetector agent.

This test suite provides comprehensive coverage of the ClaimDetector functionality,
including claim detection, check-worthiness scoring, domain classification, entity extraction,
and handling of edge cases.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verifact_agents.claim_detector.detector import ClaimDetector
from src.verifact_agents.claim_detector.models import Claim, ClaimDomain, Entity

# -- Test Data Fixtures -- #


@pytest.fixture
def simple_claim_text():
    """Simple text with one factual claim."""
    return "The Earth is round."


@pytest.fixture
def multiple_claims_text():
    """Text with multiple factual claims."""
    return "The Earth is round. The sky is blue. Water boils at 100 degrees Celsius."


@pytest.fixture
def opinion_text():
    """Text with opinions rather than factual claims."""
    return (
        "I think chocolate ice cream is the best flavor. In my opinion, dogs are better than cats."
    )


@pytest.fixture
def mixed_text():
    """Text with both factual claims and opinions."""
    return "The Earth is round. I think chocolate ice cream is the best flavor. The sky is blue."


@pytest.fixture
def long_text():
    """A very long text for testing performance and chunking."""
    return " ".join(["The Earth is round."] * 100 + ["The sky is blue."] * 100)


@pytest.fixture
def scientific_claims():
    """Scientific domain claims."""
    return "The Earth orbits the Sun. Water freezes at 0 degrees Celsius. E=mc²."


@pytest.fixture
def political_claims():
    """Political domain claims."""
    return "The United States has 50 states. The UK left the European Union in 2020."


@pytest.fixture
def empty_text():
    """Empty text for edge case testing."""
    return ""


@pytest.fixture
def claim_with_entities():
    """Text with claims containing various entity types."""
    return "Apple CEO Tim Cook announced a new iPhone on September 15, 2023, costing $999."


# -- Mock Fixtures -- #


@pytest.fixture
def simple_claim():
    """A simple claim object."""
    return Claim(
        text="The Earth is round.",
        original_text="The Earth is round.",
        normalized_text="The Earth has a roughly spherical shape.",
        check_worthiness=0.9,
        specificity_score=0.8,
        public_interest_score=0.7,
        impact_score=0.6,
        confidence=0.95,
        domain=ClaimDomain.SCIENCE,
        entities=[
            Entity(text="Earth", type="CELESTIAL_BODY", normalized_text="Earth", relevance=1.0)
        ],
        rank=1,
    )


@pytest.fixture
def earth_entity():
    """An entity extraction result."""
    return Entity(text="Earth", type="CELESTIAL_BODY", normalized_text="Earth", relevance=1.0)


@pytest.fixture
def mock_agent():
    """Create a mock OpenAI agent for testing."""
    mock = AsyncMock()
    mock.run.return_value = [
        Claim(
            text="The Earth is round.",
            original_text="The Earth is round.",
            normalized_text="The Earth has a roughly spherical shape.",
            check_worthiness=0.9,
            specificity_score=0.8,
            public_interest_score=0.7,
            impact_score=0.6,
            confidence=0.95,
            domain=ClaimDomain.SCIENCE,
            entities=[
                Entity(text="Earth", type="CELESTIAL_BODY", normalized_text="Earth", relevance=1.0)
            ],
            rank=1,
        )
    ]
    return mock


@pytest.fixture
def mock_entity_agent():
    """Create a mock entity extraction agent for testing."""
    mock = AsyncMock()
    mock.run.return_value = [
        Entity(text="Earth", type="CELESTIAL_BODY", normalized_text="Earth", relevance=1.0)
    ]
    return mock


@pytest.fixture
def detector(mock_agent, mock_entity_agent):
    """Create a ClaimDetector with mocked dependencies for testing."""
    with patch("openai.agents.Agent") as mock_agent_class:
        # Configure the first call to return the claim detection agent
        # and the second call to return the entity extraction agent
        mock_agent_class.side_effect = [mock_agent, mock_entity_agent]

        with patch("src.utils.logging.structured_logger.get_structured_logger") as mock_logger:
            mock_logger.return_value = MagicMock()

            detector = ClaimDetector(min_check_worthiness=0.5, max_claims=5)

            # Replace the agent instances with our mocks
            detector.agent = mock_agent
            detector.entity_agent = mock_entity_agent

            return detector


class TestClaimDetector:
    """Test suite for the ClaimDetector agent."""

    @pytest.mark.asyncio
    async def test_detect_simple_claim(self, detector, mock_agent):
        """Test that simple factual claims are detected correctly."""
        test_text = "The Earth is round."

        # Configure the mock to return a simple claim
        mock_agent.run.return_value = [
            Claim(
                text="The Earth is round.",
                original_text="The Earth is round.",
                normalized_text="The Earth has a roughly spherical shape.",
                check_worthiness=0.9,
                specificity_score=0.8,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.95,
                domain=ClaimDomain.SCIENCE,
                entities=[],
                rank=1,
            )
        ]

        claims = await detector.detect_claims(test_text)

        assert len(claims) == 1
        assert claims[0].text == "The Earth is round."
        assert claims[0].check_worthiness == 0.9
        assert claims[0].domain == ClaimDomain.SCIENCE

    @pytest.mark.asyncio
    async def test_detect_multiple_claims(self, detector, mock_agent):
        """Test that multiple claims in a text are detected."""
        test_text = "The Earth is round. The sky is blue. Water boils at 100 degrees Celsius."

        # Configure the mock to return multiple claims
        mock_agent.run.return_value = [
            Claim(
                text="The Earth is round.",
                original_text="The Earth is round.",
                normalized_text="The Earth has a roughly spherical shape.",
                check_worthiness=0.9,
                specificity_score=0.8,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.95,
                domain=ClaimDomain.SCIENCE,
                entities=[],
                rank=1,
            ),
            Claim(
                text="The sky is blue.",
                original_text="The sky is blue.",
                normalized_text="The sky appears blue due to atmospheric scattering.",
                check_worthiness=0.7,
                specificity_score=0.6,
                public_interest_score=0.5,
                impact_score=0.4,
                confidence=0.9,
                domain=ClaimDomain.SCIENCE,
                entities=[],
                rank=2,
            ),
            Claim(
                text="Water boils at 100 degrees Celsius.",
                original_text="Water boils at 100 degrees Celsius.",
                normalized_text="Water boils at 100 degrees Celsius at standard atmospheric pressure.",
                check_worthiness=0.85,
                specificity_score=0.9,
                public_interest_score=0.6,
                impact_score=0.5,
                confidence=0.95,
                domain=ClaimDomain.SCIENCE,
                entities=[],
                rank=3,
            ),
        ]

        claims = await detector.detect_claims(test_text)

        assert len(claims) == 3
        assert claims[0].text == "The Earth is round."
        assert claims[1].text == "The sky is blue."
        assert claims[2].text == "Water boils at 100 degrees Celsius."

    @pytest.mark.asyncio
    async def test_ignore_opinions(self, detector, mock_agent):
        """Test that opinions are not flagged as factual claims."""
        test_text = "I think chocolate ice cream is the best flavor."

        # Configure the mock to return no claims (opinions filtered out)
        mock_agent.run.return_value = []

        claims = await detector.detect_claims(test_text)

        assert len(claims) == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "text,expected_claims",
        [
            ("The Earth is flat.", 1),  # Simple factual claim (false, but still a claim)
            ("I love dogs.", 0),  # Opinion, not a factual claim
            ("According to NASA, Mars has two moons.", 1),  # Attributed factual claim
            (
                "The president said taxes will increase, but I don't believe it.",
                1,
            ),  # Contains opinion and claim
            (
                "If it rains tomorrow, the game will be canceled.",
                0,
            ),  # Hypothetical, not a factual claim
        ],
    )
    async def test_claim_detection_cases(self, detector, mock_agent, text, expected_claims):
        """Test various cases of claim detection."""
        if expected_claims > 0:
            # Configure the mock to return the expected number of claims
            mock_agent.run.return_value = [
                Claim(
                    text=text,
                    original_text=text,
                    normalized_text=text,
                    check_worthiness=0.8,
                    specificity_score=0.7,
                    public_interest_score=0.6,
                    impact_score=0.5,
                    confidence=0.9,
                    domain=ClaimDomain.SCIENCE,
                    entities=[],
                    rank=1,
                )
                for _ in range(expected_claims)
            ]
        else:
            # Configure the mock to return no claims
            mock_agent.run.return_value = []

        claims = await detector.detect_claims(text)
        assert len(claims) == expected_claims

    @pytest.mark.asyncio
    async def test_check_worthiness_filtering(self, detector, mock_agent):
        """Test filtering claims by check-worthiness."""
        test_text = "The Earth orbits the Sun. Some people prefer tea over coffee."

        # Configure the mock to return claims with different check-worthiness scores
        mock_agent.run.return_value = [
            Claim(
                text="The Earth orbits the Sun.",
                original_text="The Earth orbits the Sun.",
                normalized_text="The Earth orbits the Sun.",
                check_worthiness=0.9,
                specificity_score=0.8,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.95,
                domain=ClaimDomain.SCIENCE,
                entities=[],
                rank=1,
            ),
            Claim(
                text="Some people prefer tea over coffee.",
                original_text="Some people prefer tea over coffee.",
                normalized_text="Some people prefer tea over coffee.",
                check_worthiness=0.3,  # Below default threshold of 0.5
                specificity_score=0.4,
                public_interest_score=0.2,
                impact_score=0.1,
                confidence=0.8,
                domain=ClaimDomain.OTHER,
                entities=[],
                rank=2,
            ),
        ]

        # Default min_check_worthiness is 0.5
        claims = await detector.detect_claims(test_text)

        assert len(claims) == 1
        assert claims[0].text == "The Earth orbits the Sun."

        # Test with lower threshold to include both claims
        claims = await detector.detect_claims(test_text, min_check_worthiness=0.2)

        assert len(claims) == 2

    @pytest.mark.asyncio
    async def test_domain_classification(self, detector, mock_agent):
        """Test domain classification of claims."""
        test_text = "The president announced a new tax policy. COVID-19 cases are declining."

        # Configure the mock to return claims from different domains
        mock_agent.run.return_value = [
            Claim(
                text="The president announced a new tax policy.",
                original_text="The president announced a new tax policy.",
                normalized_text="The president announced a new tax policy.",
                check_worthiness=0.9,
                specificity_score=0.8,
                public_interest_score=0.9,
                impact_score=0.8,
                confidence=0.95,
                domain=ClaimDomain.POLITICS,
                entities=[],
                rank=1,
            ),
            Claim(
                text="COVID-19 cases are declining.",
                original_text="COVID-19 cases are declining.",
                normalized_text="COVID-19 cases are declining.",
                check_worthiness=0.85,
                specificity_score=0.7,
                public_interest_score=0.9,
                impact_score=0.9,
                confidence=0.9,
                domain=ClaimDomain.HEALTH,
                entities=[],
                rank=2,
            ),
        ]

        claims = await detector.detect_claims(test_text)

        assert len(claims) == 2
        assert claims[0].domain == ClaimDomain.POLITICS
        assert claims[1].domain == ClaimDomain.HEALTH

    @pytest.mark.asyncio
    async def test_entity_extraction(self, detector, mock_agent, mock_entity_agent):
        """Test entity extraction from claims."""
        test_text = "NASA confirmed that Mars has two moons, Phobos and Deimos."

        # Configure the mock to return a claim with entities
        mock_agent.run.return_value = [
            Claim(
                text="NASA confirmed that Mars has two moons, Phobos and Deimos.",
                original_text="NASA confirmed that Mars has two moons, Phobos and Deimos.",
                normalized_text="Mars has two moons named Phobos and Deimos.",
                check_worthiness=0.9,
                specificity_score=0.9,
                public_interest_score=0.7,
                impact_score=0.5,
                confidence=0.95,
                domain=ClaimDomain.SCIENCE,
                entities=[],  # Empty initially, will be filled by entity_agent
                rank=1,
            )
        ]

        # Configure the entity agent to return entities
        mock_entity_agent.run.return_value = [
            Entity(
                text="NASA",
                type="ORGANIZATION",
                normalized_text="National Aeronautics and Space Administration",
                relevance=0.8,
            ),
            Entity(text="Mars", type="CELESTIAL_BODY", normalized_text="Mars", relevance=1.0),
            Entity(text="Phobos", type="CELESTIAL_BODY", normalized_text="Phobos", relevance=0.9),
            Entity(text="Deimos", type="CELESTIAL_BODY", normalized_text="Deimos", relevance=0.9),
        ]

        claims = await detector.detect_claims(test_text)

        assert len(claims) == 1
        assert len(claims[0].entities) == 4
        assert claims[0].entities[0].text == "NASA"
        assert claims[0].entities[1].text == "Mars"
        assert claims[0].entities[2].text == "Phobos"
        assert claims[0].entities[3].text == "Deimos"

    @pytest.mark.asyncio
    async def test_ranking_functionality(self, detector, mock_agent):
        """Test ranking of claims by importance."""
        test_text = "Climate change is accelerating. The stock market fell 2% yesterday. Drinking water is essential for health."

        # Configure the mock to return claims with different importance factors
        mock_agent.run.return_value = [
            Claim(
                text="The stock market fell 2% yesterday.",
                original_text="The stock market fell 2% yesterday.",
                normalized_text="The stock market declined by 2% on the previous day.",
                check_worthiness=0.7,
                specificity_score=0.9,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.95,
                domain=ClaimDomain.ECONOMICS,
                entities=[],
                rank=0,  # Will be determined by ranking algorithm
            ),
            Claim(
                text="Climate change is accelerating.",
                original_text="Climate change is accelerating.",
                normalized_text="The rate of climate change is increasing.",
                check_worthiness=0.9,
                specificity_score=0.7,
                public_interest_score=0.9,
                impact_score=0.9,
                confidence=0.9,
                domain=ClaimDomain.SCIENCE,
                entities=[],
                rank=0,  # Will be determined by ranking algorithm
            ),
            Claim(
                text="Drinking water is essential for health.",
                original_text="Drinking water is essential for health.",
                normalized_text="Drinking water is essential for human health.",
                check_worthiness=0.8,
                specificity_score=0.6,
                public_interest_score=0.8,
                impact_score=0.8,
                confidence=0.95,
                domain=ClaimDomain.HEALTH,
                entities=[],
                rank=0,  # Will be determined by ranking algorithm
            ),
        ]

        claims = await detector.detect_claims(test_text)

        assert len(claims) == 3
        # Climate change should be ranked highest due to high check_worthiness and impact
        assert claims[0].text == "Climate change is accelerating."
        assert claims[0].rank == 1
        # Health claim should be second due to domain importance
        assert claims[1].text == "Drinking water is essential for health."
        assert claims[1].rank == 2
        # Economic claim should be third
        assert claims[2].text == "The stock market fell 2% yesterday."
        assert claims[2].rank == 3

    @pytest.mark.asyncio
    async def test_max_claims_limit(self, detector, mock_agent):
        """Test limiting the number of claims returned."""
        test_text = "Claim 1. Claim 2. Claim 3. Claim 4. Claim 5. Claim 6."

        # Configure the mock to return more claims than the limit
        mock_agent.run.return_value = [
            Claim(
                text=f"Claim {i}.",
                original_text=f"Claim {i}.",
                normalized_text=f"Claim {i}.",
                check_worthiness=0.9 - (i * 0.05),  # Decreasing check-worthiness
                specificity_score=0.8,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.9,
                domain=ClaimDomain.OTHER,
                entities=[],
                rank=i,
            )
            for i in range(1, 7)
        ]

        # Default max_claims is 5
        claims = await detector.detect_claims(test_text)

        assert len(claims) == 5
        assert claims[0].text == "Claim 1."
        assert claims[4].text == "Claim 5."

        # Test with lower limit
        claims = await detector.detect_claims(test_text, max_claims=3)

        assert len(claims) == 3
        assert claims[0].text == "Claim 1."
        assert claims[2].text == "Claim 3."

    @pytest.mark.asyncio
    async def test_caching_behavior(self, detector, mock_agent):
        """Test caching of claim detection results."""
        test_text = "The Earth is round."

        # Configure the mock to return a claim
        mock_agent.run.return_value = [
            Claim(
                text="The Earth is round.",
                original_text="The Earth is round.",
                normalized_text="The Earth has a roughly spherical shape.",
                check_worthiness=0.9,
                specificity_score=0.8,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.95,
                domain=ClaimDomain.SCIENCE,
                entities=[],
                rank=1,
            )
        ]

        # First call should use the agent
        claims1 = await detector.detect_claims(test_text)

        assert len(claims1) == 1
        assert mock_agent.run.call_count == 1

        # Reset the mock to track second call
        mock_agent.reset_mock()

        # Second call with same text should use the cache
        claims2 = await detector.detect_claims(test_text)

        assert len(claims2) == 1
        # Agent should not be called again
        assert mock_agent.run.call_count == 0

    @pytest.mark.asyncio
    async def test_empty_text_input(self, detector, mock_agent):
        """Test behavior with empty text input."""
        test_text = ""

        # Configure the mock to return no claims for empty input
        mock_agent.run.return_value = []

        claims = await detector.detect_claims(test_text)

        assert len(claims) == 0

    @pytest.mark.asyncio
    async def test_very_long_text(self, detector, mock_agent):
        """Test behavior with very long text input."""
        # Generate a long text
        test_text = "This is a long text. " * 500  # Approximately 10,000 characters

        # Configure the mock to return some claims
        mock_agent.run.return_value = [
            Claim(
                text="This is a long text.",
                original_text="This is a long text.",
                normalized_text="This text is lengthy.",
                check_worthiness=0.6,
                specificity_score=0.5,
                public_interest_score=0.3,
                impact_score=0.2,
                confidence=0.8,
                domain=ClaimDomain.OTHER,
                entities=[],
                rank=1,
            )
        ]

        claims = await detector.detect_claims(test_text)

        assert len(claims) == 1
        # Verify the agent was called with the long text
        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self, detector, mock_agent):
        """Test error handling during claim detection."""
        test_text = "Error-triggering text."

        # Configure the mock to raise an exception
        mock_agent.run.side_effect = Exception("Simulated error")

        # The method should propagate the exception
        with pytest.raises(Exception) as exc_info:
            await detector.detect_claims(test_text)

        assert "Simulated error" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "text,expected_claims,domain",
        [
            ("The Earth is round.", 1, ClaimDomain.SCIENCE),
            ("The president lives in the White House.", 1, ClaimDomain.POLITICS),
            ("Exercise reduces the risk of heart disease.", 1, ClaimDomain.HEALTH),
            ("The new iPhone was released last month.", 1, ClaimDomain.TECHNOLOGY),
            (
                "Global temperatures have risen by 1°C since pre-industrial times.",
                1,
                ClaimDomain.ENVIRONMENT,
            ),
            ("The film won three Academy Awards.", 1, ClaimDomain.ENTERTAINMENT),
        ],
    )
    async def test_claim_detection_by_domain(
        self, detector, mock_agent, text, expected_claims, domain
    ):
        """Test claim detection with different domain classifications."""
        # Configure the mock to return a claim with the expected domain
        mock_agent.run.return_value = [
            Claim(
                text=text,
                original_text=text,
                normalized_text=text,
                check_worthiness=0.9,
                specificity_score=0.8,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.95,
                domain=domain,
                entities=[],
                rank=1,
            )
        ]

        claims = await detector.detect_claims(text)

        assert len(claims) == expected_claims
        if expected_claims > 0:
            assert claims[0].domain == domain

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "check_worthiness,min_threshold,should_be_included",
        [
            (0.9, 0.5, True),  # High check-worthiness, low threshold
            (0.6, 0.7, False),  # Medium check-worthiness, medium threshold
            (0.3, 0.2, True),  # Low check-worthiness, very low threshold
            (0.75, 0.75, True),  # Equal to threshold
            (0.99, 1.0, False),  # Just below threshold
        ],
    )
    async def test_check_worthiness_thresholds(
        self, detector, mock_agent, check_worthiness, min_threshold, should_be_included
    ):
        """Test filtering claims with different check-worthiness thresholds."""
        test_text = "The Earth is round."

        # Configure the mock to return a claim with the specified check-worthiness
        mock_agent.run.return_value = [
            Claim(
                text="The Earth is round.",
                original_text="The Earth is round.",
                normalized_text="The Earth has a roughly spherical shape.",
                check_worthiness=check_worthiness,
                specificity_score=0.8,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.95,
                domain=ClaimDomain.SCIENCE,
                entities=[],
                rank=1,
            )
        ]

        claims = await detector.detect_claims(test_text, min_check_worthiness=min_threshold)

        if should_be_included:
            assert len(claims) == 1
            assert claims[0].check_worthiness == check_worthiness
        else:
            assert len(claims) == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "text,entity_types",
        [
            ("Tim Cook is the CEO of Apple.", ["PERSON", "ORGANIZATION"]),
            ("Paris is the capital of France.", ["LOCATION", "LOCATION"]),
            ("The movie was released on July 4, 2022.", ["WORK_OF_ART", "DATE"]),
            ("The vaccine reduced infections by 95%.", ["MEDICAL_TERM", "PERCENT"]),
            ("The company's revenue was $2 billion last quarter.", ["MONEY", "DATE"]),
        ],
    )
    async def test_entity_extraction_by_type(
        self, detector, mock_agent, mock_entity_agent, text, entity_types
    ):
        """Test entity extraction for different entity types."""
        # Configure the claim detector mock
        mock_agent.run.return_value = [
            Claim(
                text=text,
                original_text=text,
                normalized_text=text,
                check_worthiness=0.9,
                specificity_score=0.8,
                public_interest_score=0.7,
                impact_score=0.6,
                confidence=0.95,
                domain=ClaimDomain.OTHER,
                entities=[],
                rank=1,
            )
        ]

        # Configure the entity extraction mock
        mock_entities = []
        for i, entity_type in enumerate(entity_types):
            mock_entities.append(
                Entity(
                    text=f"Entity{i + 1}",
                    type=entity_type,
                    normalized_text=f"Entity{i + 1}",
                    relevance=0.9,
                )
            )

        mock_entity_agent.run.return_value = mock_entities

        # Call with entity extraction
        claims = await detector.detect_claims(text)

        # Verify entity types
        assert len(claims) == 1
        assert len(claims[0].entities) == len(entity_types)
        extracted_types = [entity.type for entity in claims[0].entities]
        for expected_type in entity_types:
            assert expected_type in extracted_types

    @pytest.mark.asyncio
    async def test_structured_logging(self, detector, mock_agent, simple_claim_text, simple_claim):
        """Test that the claim detector uses structured logging appropriately."""
        # Replace the logger with a mock to capture log calls
        mock_logger = MagicMock()
        detector.logger = mock_logger

        # Configure the claim detector mock
        mock_agent.run.return_value = [simple_claim]

        # Call detect_claims
        await detector.detect_claims(simple_claim_text)

        # Verify logging calls
        assert mock_logger.info.call_count >= 2  # At least start and complete logs

        # Check that the start log includes the expected keys
        start_log_call = mock_logger.info.call_args_list[0]
        start_log_extra = start_log_call[1].get("extra", {})

        # End log
        end_log_call = mock_logger.info.call_args_list[-1]
        end_log_extra = end_log_call[1].get("extra", {})

        # Verify key metrics are logged
        assert "text_length" in start_log_extra
        assert "operation_id" in start_log_extra
        assert "duration_ms" in end_log_extra
        assert "claims_found" in end_log_extra

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "max_claims_param,expected_claims",
        [
            (1, 1),  # Only top claim
            (2, 2),  # Top two claims
            (5, 3),  # More than available claims
            (None, 3),  # Default to detector's max_claims
        ],
    )
    async def test_max_claims_parameter(
        self, detector, mock_agent, max_claims_param, expected_claims
    ):
        """Test that the max_claims parameter limits the number of claims returned."""
        test_text = "Claim 1. Claim 2. Claim 3."

        # Configure the mock to return multiple claims with different ranks
        mock_claims = []
        for i in range(3):
            mock_claims.append(
                Claim(
                    text=f"Claim {i + 1}",
                    original_text=f"Claim {i + 1}",
                    normalized_text=f"Claim {i + 1}",
                    check_worthiness=0.9 - (i * 0.1),  # Decreasing check-worthiness
                    specificity_score=0.8,
                    public_interest_score=0.7,
                    impact_score=0.6,
                    confidence=0.95,
                    domain=ClaimDomain.OTHER,
                    entities=[],
                    rank=i + 1,
                )
            )

        mock_agent.run.return_value = mock_claims

        # Call with max_claims parameter
        claims = await detector.detect_claims(test_text, max_claims=max_claims_param)

        # Verify correct number of claims
        assert len(claims) == expected_claims

        # Verify claims are in correct order (ranked by check-worthiness)
        for i in range(len(claims)):
            assert claims[i].text == f"Claim {i + 1}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "text,expected_error",
        [
            ("", None),  # Empty text should return empty list, not error
            (None, TypeError),  # None should raise TypeError
            ("A" * 100000, None),  # Very long text should be handled
        ],
    )
    async def test_edge_case_inputs(self, detector, mock_agent, text, expected_error):
        """Test behavior with edge case inputs."""
        if expected_error:
            with pytest.raises(expected_error):
                await detector.detect_claims(text)
        else:
            if text == "":
                # Empty text scenario
                mock_agent.run.return_value = []
                claims = await detector.detect_claims(text)
                assert len(claims) == 0
            elif len(text) > 10000:
                # Very long text scenario
                mock_agent.run.return_value = [
                    Claim(
                        text="Claim from very long text",
                        original_text="Claim from very long text",
                        normalized_text="Claim from very long text",
                        check_worthiness=0.9,
                        specificity_score=0.8,
                        public_interest_score=0.7,
                        impact_score=0.6,
                        confidence=0.95,
                        domain=ClaimDomain.OTHER,
                        entities=[],
                        rank=1,
                    )
                ]
                claims = await detector.detect_claims(text)
                assert len(claims) == 1
                assert claims[0].text == "Claim from very long text"

    @pytest.mark.asyncio
    async def test_performance_metrics(self, detector, mock_agent, simple_claim_text):
        """Test that performance metrics are correctly tracked."""
        # Configure the mock
        mock_agent.run.return_value = [simple_claim()]

        # Replace metrics with a mock
        mock_metrics = MagicMock()
        detector.metrics = mock_metrics

        # Call detect_claims
        await detector.detect_claims(simple_claim_text)

        # Verify metrics calls
        assert mock_metrics.increment.call_count > 0
        assert mock_metrics.timing.call_count > 0

        # Verify specific metrics
        mock_metrics.increment.assert_any_call("claims_detected", 1)

        # Check for timing metrics
        timing_calls = [call[0][0] for call in mock_metrics.timing.call_args_list]
        assert "detection_time" in timing_calls

    @pytest.mark.asyncio
    async def test_model_fallback(self, detector, mock_agent, simple_claim):
        """Test model fallback behavior when primary model fails."""
        # Configure the primary model to fail
        primary_exception = Exception("Primary model failed")
        detector.agent.run.side_effect = primary_exception

        # Create a fallback mock agent
        fallback_mock = AsyncMock()
        fallback_mock.run.return_value = [simple_claim]

        # Patch the model_manager's fallback mechanism
        with patch.object(detector.model_manager, "get_fallback_model", return_value=fallback_mock):
            with patch.object(detector.model_manager, "has_fallback", return_value=True):
                # Call detect_claims - should use fallback
                claims = await detector.detect_claims("The Earth is round.")

                # Verify fallback was used
                assert fallback_mock.run.call_count == 1
                assert len(claims) == 1

                # Verify logger recorded the fallback
                assert detector.logger.warning.call_count > 0

    @pytest.mark.asyncio
    async def test_cache_hit_metrics(self, detector, mock_agent, simple_claim):
        """Test cache hit/miss metrics."""
        # Configure the mock
        mock_agent.run.return_value = [simple_claim]

        # Create mock cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # First call: cache miss
        detector.claim_cache = mock_cache

        # Replace metrics with a mock
        mock_metrics = MagicMock()
        detector.metrics = mock_metrics

        # First call - should be a cache miss
        await detector.detect_claims("The Earth is round.")

        # Now set up cache hit
        mock_cache.get.return_value = [simple_claim]  # Second call: cache hit

        # Second call - should be a cache hit
        await detector.detect_claims("The Earth is round.")

        # Verify metrics for cache hit and miss
        mock_metrics.increment.assert_any_call("cache_misses", 1)
        mock_metrics.increment.assert_any_call("cache_hits", 1)


# Standalone test function for manual testing
@pytest.mark.skip("Manual standalone test script - run directly if needed")
async def test_claim_detector_standalone():
    """Test the ClaimDetector component (standalone version)."""
    print("\n=== Testing ClaimDetector ===\n")

    detector = ClaimDetector()

    # Test cases with different types of content
    test_cases = [
        {
            "name": "Simple factual claims",
            "text": "The Earth is approximately 4.54 billion years old. Water covers about 71% of the Earth's surface.",
        },
        {
            "name": "Mixed facts and opinions",
            "text": "The average distance from Earth to the Sun is about 93 million miles. I think space exploration is humanity's most exciting frontier.",
        },
        {
            "name": "Scientific claims",
            "text": "Climate change has caused global temperatures to rise by approximately 1°C since pre-industrial times. The concentration of CO2 in the atmosphere has exceeded 410 parts per million.",
        },
        {
            "name": "Historical claims",
            "text": "World War II ended in 1945. The United States dropped atomic bombs on Hiroshima and Nagasaki in August of that year.",
        },
        {
            "name": "Primarily opinions",
            "text": "I believe that dogs make better pets than cats. Everyone should visit Paris at least once in their lifetime. The best time to exercise is in the morning.",
        },
    ]

    # Test each case
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        print(f'Text: "{case["text"]}"')

        try:
            # Time the detection process
            import time

            start = time.time()

            # Detect claims
            claims = await detector.detect_claims(case["text"])

            duration = time.time() - start
            print(f"Detection took {duration:.2f} seconds")

            # Display results
            if claims:
                print(f"Detected {len(claims)} claims:")
                for i, claim in enumerate(claims):
                    check_status = (
                        "Checkworthy" if claim.check_worthiness >= 0.5 else "Not checkworthy"
                    )
                    print(f'  {i + 1}. "{claim.text}" ({check_status})')
                    if hasattr(claim, "context") and claim.context:
                        print(f"     Context: {claim.context}")
                    if hasattr(claim, "domain") and claim.domain:
                        print(f"     Domain: {claim.domain}")
                    if hasattr(claim, "check_worthiness") and claim.check_worthiness:
                        print(f"     Check-worthiness score: {claim.check_worthiness:.2f}")
            else:
                print("No claims detected.")

        except Exception as e:
            print(f"Error during claim detection: {e}")

    print("\n=== ClaimDetector Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_claim_detector_standalone())
