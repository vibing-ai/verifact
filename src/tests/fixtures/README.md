# VeriFact Test Fixtures

This directory contains test fixtures for the VeriFact project, providing sample data for claims, evidence, and verdicts to use in tests.

## Available Fixtures

### Claims (`claims.py`)

Contains sample factual claims organized by domain:

- `POLITICAL_CLAIMS`: Claims related to politics and international relations
- `HEALTH_CLAIMS`: Claims related to health and medicine
- `SCIENCE_CLAIMS`: Claims related to science and technology
- `ECONOMIC_CLAIMS`: Claims related to economics and finance
- `ALL_CLAIMS`: Combined list of all claims
- `SAMPLE_TEXTS`: Sample text passages containing multiple claims for testing claim detection

### Evidence (`evidence.py`)

Contains sample evidence for claims, organized by topic:

- `POLITICAL_EVIDENCE`: Evidence for political claims
- `HEALTH_EVIDENCE`: Evidence for health claims
- `SCIENCE_EVIDENCE`: Evidence for science claims
- `ECONOMIC_EVIDENCE`: Evidence for economic claims
- `ALL_EVIDENCE`: Combined dictionary of all evidence

Each evidence collection is a dictionary where keys are topics and values are lists of `Evidence` objects.

### Verdicts (`verdicts.py`)

Contains sample verdicts for claims, organized by domain:

- `POLITICAL_VERDICTS`: Verdicts for political claims
- `HEALTH_VERDICTS`: Verdicts for health claims
- `SCIENCE_VERDICTS`: Verdicts for science claims
- `ECONOMIC_VERDICTS`: Verdicts for economic claims
- `ALL_VERDICTS`: Combined list of all verdicts

## Usage Examples

### Using in Unit Tests

```python
from src.tests.fixtures.claims import POLITICAL_CLAIMS
from src.tests.fixtures.evidence import POLITICAL_EVIDENCE
from src.tests.fixtures.verdicts import POLITICAL_VERDICTS

def test_claim_processing():
    # Use a sample claim from fixtures
    sample_claim = POLITICAL_CLAIMS[0]
    assert sample_claim.text == "The United States has the largest military budget in the world."
```

### Using with Mock Agents

```python
from unittest.mock import AsyncMock
from src.tests.fixtures.claims import POLITICAL_CLAIMS
from src.tests.fixtures.evidence import POLITICAL_EVIDENCE

class MockClaimDetector:
    def __init__(self, claims_to_return):
        self.claims_to_return = claims_to_return
        self.detect_claims = AsyncMock(return_value=claims_to_return)

# Create a mock claim detector that returns sample claims
mock_detector = MockClaimDetector(claims_to_return=POLITICAL_CLAIMS)
```

### Using in Integration Tests

```python
import pytest
from src.tests.fixtures.claims import SAMPLE_TEXTS
from src.verifact_manager import VerifactManager

@pytest.mark.asyncio
async def test_end_to_end_factchecking():
    # Create a manager instance
    manager = VerifactManager()
    
    # Process a sample text
    sample_text = SAMPLE_TEXTS[0]
    results = await manager.process_text(sample_text)
    
    # Verify results
    assert len(results) > 0
```

## Extending the Fixtures

To add new fixtures:

1. Add new claims to the appropriate list in `claims.py`
2. Add corresponding evidence in `evidence.py`
3. Add corresponding verdicts in `verdicts.py`
4. Run the fixture tests to ensure everything is working correctly:

```bash
pytest src/tests/test_fixtures.py -v
```
