# VeriFact Agent Architecture

This module implements a clean, decoupled architecture for the VeriFact factchecking system agents. The architecture is designed to support proper separation of concerns, dependency injection, and testability.

## Architectural Principles

The architecture is based on the following principles:

1. **Single Responsibility Principle**: Each agent has one clearly defined responsibility
2. **Interface Segregation**: Define minimal, focused interfaces for each agent
3. **Dependency Inversion**: High-level modules don't depend on low-level modules
4. **Message-based Communication**: Agents communicate through well-defined DTOs
5. **Explicit Dependencies**: Dependencies between agents are explicit, through constructor injection

## Core Components

### Base Agent Interface

The architecture is built around a base `Agent` protocol with a generic `process()` method. This protocol is defined in `base.py` and serves as the foundation for specific agent interfaces.

```python
class Agent(Protocol, Generic[T_Input, T_Output]):
    """Base protocol for all agents."""

    async def process(self, input_data: T_Input) -> T_Output:
        """Process the input data and return a result."""
        ...
```

### Data Transfer Objects (DTOs)

The agents communicate through immutable Data Transfer Objects (DTOs) defined in `dto.py`:

1. **Claim**: Represents a factual claim detected in text
2. **Evidence**: Represents evidence related to a claim
3. **Verdict**: Represents a factchecking verdict with explanation and sources

### Specific Agent Interfaces

The system defines three key agent interfaces:

1. **ClaimDetector**: Extracts factual claims from text
2. **EvidenceHunter**: Gathers evidence related to claims
3. **VerdictWriter**: Generates verdicts based on claims and evidence

Each interface extends the base `Agent` protocol with specific methods for its responsibility.

### Factory

The `AgentFactory` in `factory.py` provides a centralized place for creating agent instances with proper configuration and dependency injection:

```python
# Create agents with the factory
claim_detector = AgentFactory.create_claim_detector(config)
evidence_hunter = AgentFactory.create_evidence_hunter(config)
verdict_writer = AgentFactory.create_verdict_writer(config)
```

### Orchestrator

The `FactcheckPipeline` in `orchestrator.py` coordinates the workflow between agents, handling the flow of data and error boundaries:

```python
# Create a pipeline with explicit dependencies
pipeline = FactcheckPipeline(
    claim_detector=claim_detector,
    evidence_hunter=evidence_hunter,
    verdict_writer=verdict_writer
)

# Process text through the pipeline
verdicts = await pipeline.process_text(text)
```

## Legacy Compatibility

The system provides backward compatibility with the legacy agent interfaces:

1. Legacy interfaces (`IClaimDetector`, `IEvidenceHunter`, `IVerdictWriter`) extend the new interfaces
2. The `DTOFactory` in `dto.py` converts between legacy models and new DTOs
3. The `transition.py` module provides adapter functions for integration with legacy code

## Usage Examples

### Using the Complete Pipeline

```python
from src.agents.orchestrator import FactcheckPipelineFactory

# Define pipeline configuration
config = {
    "parallelism": 3,
    "min_check_worthiness": 0.6,
    "max_claims": 5,
    "claim_detector": {"model_name": "google/gemma-2-27b-it"},
    "evidence_hunter": {"model_name": "google/gemma-3-27b-it:free"},
    "verdict_writer": {"model_name": "deepseek/deepseek-chat:free"}
}

# Create the pipeline using the factory
pipeline = FactcheckPipelineFactory.create_pipeline(config)

# Process text through the pipeline
verdicts = await pipeline.process_text(text)
```

### Using Individual Agents

```python
from src.agents.factory import AgentFactory

# Create individual agents
claim_detector = AgentFactory.create_claim_detector()
evidence_hunter = AgentFactory.create_evidence_hunter()
verdict_writer = AgentFactory.create_verdict_writer()

# Use agents individually
claims = await claim_detector.detect_claims(text)
evidence = await evidence_hunter.gather_evidence(claims[0])
verdict = await verdict_writer.generate_verdict(claims[0], evidence)
```

## Testing

The architecture supports easy testing with mocks:

```python
# Create mock agents
mock_claim_detector = MockClaimDetector(claims_to_return=[sample_claim])
mock_evidence_hunter = MockEvidenceHunter(evidence_to_return=[sample_evidence])
mock_verdict_writer = MockVerdictWriter(verdict_to_return=sample_verdict)

# Create pipeline with mock agents
pipeline = FactcheckPipeline(
    claim_detector=mock_claim_detector,
    evidence_hunter=mock_evidence_hunter,
    verdict_writer=mock_verdict_writer
)

# Test the pipeline
verdicts = await pipeline.process_text("Test text")
```

See `examples/pipeline_testing.py` for complete testing examples.

## Extension Points

To extend the system:

1. **New Agent Types**: Create a new interface extending the base `Agent` protocol
2. **New DTOs**: Define new immutable data classes for communication
3. **New Agent Implementations**: Implement existing interfaces with new behavior
4. **New Orchestrators**: Create specialized pipelines for specific workflows

## Directory Structure

```
src/agents/
├── base.py                # Base Agent protocol
├── dto.py                 # Data Transfer Objects
├── factory.py             # Agent factory
├── interfaces.py          # Specific agent interfaces
├── orchestrator.py        # Pipeline orchestrator
├── transition.py          # Legacy compatibility utilities
├── examples/              # Usage examples
│   ├── pipeline_usage.py  # Example pipeline usage
│   └── pipeline_testing.py# Example tests
└── README.md              # This file
```
