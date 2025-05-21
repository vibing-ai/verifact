# Using OpenAI Agents SDK with VeriFact

This document explains how to use the OpenAI Agents SDK alongside VeriFact's renamed `verifact_agents` module.

## Background

To avoid namespace conflicts with the OpenAI Agents SDK, we've renamed our internal module from `src.agents` to `src.verifact_agents`. This allows us to use both our internal agents and the OpenAI Agents SDK without import conflicts.

## Installation

The OpenAI Agents SDK is included in our project dependencies. If you're setting up a new environment, simply install the project dependencies:

```bash
pip install -e .
```

Or if you're using `uv`:

```bash
uv pip install -e .
```

## Usage Example

Here's a simple example showing the correct import patterns:

```python
# Import OpenAI Agents SDK
from agents import Agent as OpenAIAgent
from agents import Runner

# Import VeriFact agents
from src.verifact_agents import ClaimDetector
from src.verifact_agents.evidence_hunter import EvidenceHunter
from src.verifact_agents.verdict_writer import VerdictWriter

# Using OpenAI Agents
fact_checker_agent = OpenAIAgent(
    name="Fact Checker",
    instructions="You are a fact-checking assistant...",
)

# Run the OpenAI agent
result = await Runner.run(fact_checker_agent, "Check this claim: The Earth is flat.")

# Using VeriFact agents
claim_detector = ClaimDetector()
claims = await claim_detector.process("The Earth is flat and vaccines cause autism.")
```

## Full Example

For a complete example showing how to use both types of agents together, see the [OpenAI Agents Example](../../examples/openai_agents_example.py).

## Differences Between VeriFact Agents and OpenAI Agents

- **VeriFact Agents**: Our specialized agents (`ClaimDetector`, `EvidenceHunter`, `VerdictWriter`) provide domain-specific factchecking functionality with fine-tuned models.
- **OpenAI Agents**: The OpenAI Agents SDK provides a general framework for building, orchestrating, and deploying AI agents with features like handoffs, guardrails, and integrated tracing.

You may want to use VeriFact agents for the core factchecking pipeline and then use OpenAI agents to build interactive interfaces or extend the system with additional capabilities.

## Environment Variables

Remember to set your OpenAI API key when using the OpenAI Agents SDK:

```bash
export OPENAI_API_KEY=your_api_key_here
```
