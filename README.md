# VeriFact: Open-Source AI Factchecking Platform – Product Requirements Document (PRD)

**Repository:** [vibing-ai/verifact](https://github.com/vibing-ai/verifact)

---

## Executive Summary

VeriFact is an open-source AI factchecking platform that leverages a multi-agent architecture to detect factual claims, gather evidence, and generate verdicts with transparent explanations and source citations. The project is designed for extensibility, open source collaboration, and rapid iteration, with the initial implementation built using the **OpenAI Agent SDK** with **OpenRouter** for multi-model access.

---

## 1. Project Goals

- **Automate Factchecking:** Identify, research, and verify factual claims from user-submitted text.
- **Multi-Agent Architecture:** Modular agents for claim detection, evidence gathering, and verdict writing.
- **Open Source Collaboration:** Clear contribution pathways, documentation, and GitHub workflows.
- **Transparency & Accuracy:** Explanations and source citations for every verdict.

---

## 2. Core Features

- **Claim Detection:** Extract check-worthy factual claims from text.
- **Evidence Gathering:** Retrieve and rank evidence from trusted sources using web search.
- **Verdict Generation:** Synthesize evidence to produce verdicts (True/False/Partly True/Inconclusive) with confidence scores and explanations.
- **Chainlit Interface:** Interactive web UI for testing and exploring the fact-checking process.
- **Extensible Design:** Modular codebase for easy addition of new features and agents.
- **Multi-Model Support:** Use OpenRouter to access a variety of LLMs including OpenAI, Anthropic, Mistral and more.

---

## 3. Technical Architecture

### 3.1 Agent Pipeline

```
User Input → ClaimDetector → EvidenceHunter → VerdictWriter → User Output
```

- **ClaimDetector:** Identifies and extracts factual claims.
- **EvidenceHunter:** Searches for and evaluates supporting/contradicting evidence.
- **VerdictWriter:** Synthesizes evidence and generates verdicts with explanations.

### 3.2 OpenAI Agent SDK with OpenRouter

- **Lightweight orchestration** with structured outputs (Pydantic models).
- **Provider-agnostic**: Uses OpenRouter to access models from multiple providers.
- **Native tracing** for debugging and monitoring.
- **Manual handoff** between agents for flexible workflows.

### 3.3 Chainlit Frontend

- **Interactive Chat Interface:** Visualize the fact-checking process step by step.
- **Streaming Results:** Real-time updates as agents process claims.
- **Multi-Step Reasoning:** Clear visualization of the entire verification pipeline.
- **Chainlit Playground:** Built-in LLM playground for testing and debugging.

### 3.4 Supabase with PGVector Database

- **Vector Storage:** Store and retrieve embeddings for efficient semantic search.
- **PGVector Extension:** PostgreSQL-native vector similarity operations.
- **Supabase Integration:** Easy management of vector database operations.
- **Persistence:** Save fact-check results and evidence for future reference.

### 3.5 OpenRouter Integration

- **Multi-Model Access:** Use models from OpenAI, Anthropic, Mistral, and others through a single API.
- **Model Fallbacks:** Automatic failover to alternative models when necessary.
- **Cost Optimization:** Select the most cost-effective models for different tasks.
- **Simplified Integration:** Single configuration point for all language models.

**Example Implementation:**

```python
from agents import Agent, Runner, WebSearchTool
from pydantic import BaseModel, Literal

class Claim(BaseModel):
    text: str
    context: str
    checkworthy: bool

class Verdict(BaseModel):
    claim: str
    verdict: Literal["true", "false", "partially true", "unverifiable"]
    confidence: float
    explanation: str
    sources: list[str]

claim_detector = Agent(
    name="ClaimDetector",
    instructions="Identify check-worthy factual claims from input text.",
    output_type=Claim,
    tools=[WebSearchTool()],
    model="openai/gpt-4o"  # Uses OpenRouter to access GPT-4o
)

evidence_hunter = Agent(
    name="EvidenceHunter",
    instructions="Find evidence for or against the provided claim.",
    tools=[WebSearchTool()],
    model="anthropic/claude-3-opus"  # Uses OpenRouter to access Claude
)

verdict_writer = Agent(
    name="VerdictWriter",
    instructions="Analyze evidence and determine claim accuracy.",
    output_type=Verdict,
    model="mistral/mistral-large"  # Uses OpenRouter to access Mistral
)

factcheck_coordinator = Agent(
    name="FactcheckCoordinator",
    instructions="Coordinate the factchecking process.",
    handoffs=[claim_detector, evidence_hunter, verdict_writer]
)
```

---

## 4. API Design

**Endpoint:** `POST /api/v1/factcheck`

**Request:**

```json
{
  "text": "Input text containing claims",
  "options": {
    "min_check_worthiness": 0.7,
    "domains": ["politics", "health"],
    "max_claims": 5,
    "explanation_detail": "detailed"
  }
}
```

**Response:**

```json
{
  "claims": [
    {
      "text": "Normalized claim text",
      "verdict": "Mostly True",
      "confidence": 0.89,
      "explanation": "Detailed explanation with evidence",
      "sources": [{ "url": "source1.com", "credibility": 0.95, "quote": "..." }]
    }
  ],
  "metadata": {
    "processing_time": "1.2s",
    "model_version": "1.0.4"
  }
}
```

---

## 5. Development Roadmap

### V1 (MVP) – 14 Days

- Claim detection from text
- Evidence retrieval via web search
- Verdict classification and explanation
- Chainlit web interface
- Supabase with PGVector integration
- API documentation

### V2 (Post-MVP)

- Multi-claim and multilingual support
- Basic image analysis
- User feedback and metrics dashboard

### V3+

- Advanced media forensics (image/video)
- Expanded language support
- Developer API
- Debate panel for contested claims

---

## 6. Repository Structure

```
verifact/
├── .github/                    # GitHub workflows & templates
├── docs/                       # Documentation
│   ├── api/                    # API reference documentation
│   ├── agents/                 # Agent documentation
│   ├── examples/               # Usage examples and tutorials
│   └── tutorials/              # Step-by-step tutorials
├── examples/                   # Example scripts for practical usage
├── src/                        # Source code
│   ├── agents/                 # Agent implementations
│   ├── api/                    # API endpoints
│   ├── models/                 # ML models
│   └── utils/                  # Utilities
├── tests/                      # Tests directory
├── configs/                    # Configuration files
├── scripts/                    # Utility scripts
├── notebooks/                  # Jupyter notebooks
├── reports/                    # Generated reports and analytics
├── app.py                      # Chainlit application
├── cli.py                      # Command-line interface
├── chainlit.md                 # Chainlit documentation
├── requirements.txt            # Dependencies
├── pyproject.toml              # Python project metadata
├── README.md                   # Project overview
├── CONTRIBUTING.md             # Contribution guidelines
└── LICENSE                     # Apache 2.0
```

> **Note on Documentation Organization**:
> - `docs/examples/` contains documentation with explanations, screenshots, and code snippets
> - `examples/` contains runnable example scripts that demonstrate practical usage
> - `notebooks/` contains Jupyter notebooks for interactive examples and tutorials

---

## 7. Getting Started

### Installation

1. Clone the repository:

   ```
   git clone https://github.com/vibing-ai/verifact.git
   cd verifact
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:

   - Copy `configs/env.template` to `.env`
   - Add your OpenRouter API key (required)
   - Configure other settings as needed

4. Run the Chainlit interface:
   ```
   chainlit run app.py
   ```

### Using OpenRouter

VeriFact uses OpenRouter exclusively to access AI models:

1. Sign up for an account at [OpenRouter](https://openrouter.ai/)
2. Get your API key from the OpenRouter dashboard
3. In your `.env` file, set:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```
4. Optionally configure your site information:
   ```
   OPENROUTER_SITE_URL=your_site_url
   OPENROUTER_SITE_NAME=your_site_name
   ```

VeriFact supports models from multiple providers through OpenRouter:

- OpenAI models (e.g., `openai/gpt-4o`)
- Anthropic models (e.g., `anthropic/claude-3-opus`)
- Mistral models (e.g., `mistral/mistral-large`)
- Meta models (e.g., `meta/llama-3-70b-instruct`)
- Google models (e.g., `google/gemini-pro`)

### Setting up Supabase

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Enable the pgvector extension in your Supabase project
3. Add your Supabase URL and key to the `.env` file

---

## 8. Contribution Guidelines

- **Issue Assignment:** Claim issues via comments; mentors approve assignments.
- **Development:** Fork, branch, implement, test, and document.
- **Pull Requests:** Reference issues, pass CI checks, and follow PR template.
- **Review:** Mentor review and feedback before merge.

---

## 9. Testing & Quality Assurance

- **Unit Tests:** >80% code coverage.
- **Integration Tests:** Agent pipeline and API endpoints.
- **End-to-End Tests:** Known claims with expected outcomes.
- **CI/CD:** Automated linting, formatting, and tests on PRs.

---

## 10. Licensing

- **Code:** Apache 2.0 License.
- **Models:** Separate model license for usage and attribution.

---

## 11. References

- [vibing-ai/verifact GitHub Repository](https://github.com/vibing-ai/verifact)
- [OpenAI Agent SDK Documentation](https://github.com/openai/openai-python)
- [OpenRouter Documentation](https://openrouter.ai/docs)

---

**For more details, see the full PRD in `docs/Verifact PRD.md` or the [repository README](https://github.com/vibing-ai/verifact).**
