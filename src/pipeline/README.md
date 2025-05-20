# VeriFact Pipeline Module

The VeriFact Pipeline module provides a unified interface for connecting the three main agents of the VeriFact system:

1. **ClaimDetector**: Identifies factual claims in text
2. **EvidenceHunter**: Gathers evidence for claims
3. **VerdictWriter**: Analyzes evidence and generates verdicts

## Key Features

- **Unified Processing**: Process text through all three agents sequentially
- **Error Handling**: Robust error recovery with configurable retries
- **Multiple Interfaces**:
  - Asynchronous API with `process_text()`
  - Synchronous API with `process_text_sync()`
  - Streaming API with `process_text_streaming()`
- **Events & Progress Tracking**: Subscribe to pipeline events
- **Configuration Options**: Customize behavior through `PipelineConfig`
- **Detailed Logging**: Comprehensive logging of pipeline operations

## Usage Examples

### Basic Usage

```python
from src.pipeline import FactcheckPipeline

# Create a pipeline with default configuration
pipeline = FactcheckPipeline()

# Process text asynchronously
import asyncio
verdicts = asyncio.run(pipeline.process_text("Earth is the third planet from the sun."))

# Or synchronously
verdicts = pipeline.process_text_sync("Earth is the third planet from the sun.")

# Process the verdicts
for verdict in verdicts:
    print(f"Claim: {verdict.claim}")
    print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.0%})")
    print(f"Explanation: {verdict.explanation}")
    print("Sources:", ", ".join(verdict.sources))
```

### Advanced Configuration

```python
from src.pipeline import FactcheckPipeline, PipelineConfig

# Create a custom configuration
config = PipelineConfig(
    claim_detector_model="qwen/qwen3-8b:free",             # Best for structured JSON output
    evidence_hunter_model="google/gemma-3-27b-it:free",    # Optimized for RAG with 128k context
    verdict_writer_model="deepseek/deepseek-chat:free",    # Best reasoning for evidence synthesis
    min_checkworthiness=0.7,
    max_claims=5,
    evidence_per_claim=3,
    timeout_seconds=300.0,
    retry_attempts=3,
    raise_exceptions=True
)

# Create pipeline with custom configuration
pipeline = FactcheckPipeline(config=config)

# Process text
verdicts = asyncio.run(pipeline.process_text("Your text here..."))
```

### Event Handling

```python
from src.pipeline import FactcheckPipeline, PipelineEvent

# Create a pipeline
pipeline = FactcheckPipeline()

# Define event handlers
def on_claim_detected(event, data):
    print(f"Detected claim: {data['claims'][-1].text}")

def on_verdict_generated(event, data):
    print(f"Generated verdict: {data['verdict'].verdict}")

def on_error(event, data):
    print(f"Error: {data.get('error', 'Unknown error')}")

# Register event handlers
pipeline.register_event_handler(PipelineEvent.CLAIM_DETECTED, on_claim_detected)
pipeline.register_event_handler(PipelineEvent.VERDICT_GENERATED, on_verdict_generated)
pipeline.register_event_handler(PipelineEvent.ERROR, on_error)

# Process text
verdicts = asyncio.run(pipeline.process_text("Your text here..."))
```

### Streaming Processing

```python
from src.pipeline import FactcheckPipeline

# Create a pipeline
pipeline = FactcheckPipeline()

# Process text with streaming results
async def process_streaming():
    text = "Your text here with multiple claims..."
    async for verdict in pipeline.process_text_streaming(text):
        print(f"New verdict: {verdict.claim} -> {verdict.verdict}")
        # Process each verdict as it's generated

# Run the streaming example
asyncio.run(process_streaming())
```

## Pipeline Configuration Options

The `PipelineConfig` class provides the following configuration options:

| Option                  | Description                                         | Default            |
| ----------------------- | --------------------------------------------------- | ------------------ |
| `claim_detector_model`  | Model for claim detection                           | None (use default) |
| `evidence_hunter_model` | Model for evidence gathering                        | None (use default) |
| `verdict_writer_model`  | Model for verdict generation                        | None (use default) |
| `min_checkworthiness`   | Minimum threshold for checkworthy claims            | 0.5                |
| `max_claims`            | Maximum number of claims to process                 | None (no limit)    |
| `evidence_per_claim`    | Number of evidence items to gather per claim        | 5                  |
| `timeout_seconds`       | Timeout for the entire pipeline                     | 120.0              |
| `enable_fallbacks`      | Whether to enable model fallbacks                   | True               |
| `retry_attempts`        | Number of retry attempts for failed operations      | 2                  |
| `raise_exceptions`      | Whether to raise exceptions or return empty results | False              |
| `include_debug_info`    | Whether to include debug info in results            | False              |

## Pipeline Events

The pipeline emits the following events that you can subscribe to:

| Event               | Description                            |
| ------------------- | -------------------------------------- |
| `STARTED`           | Pipeline has started processing text   |
| `STAGE_STARTED`     | A pipeline stage has started           |
| `STAGE_COMPLETED`   | A pipeline stage has completed         |
| `CLAIM_DETECTED`    | A claim has been detected              |
| `EVIDENCE_GATHERED` | Evidence has been gathered for a claim |
| `VERDICT_GENERATED` | A verdict has been generated           |
| `COMPLETED`         | Pipeline has completed processing      |
| `ERROR`             | An error occurred during processing    |
| `WARNING`           | A warning occurred during processing   |
