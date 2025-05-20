"""VeriFact Chainlit UI Entry Point.

This module serves as the main entry point for the VeriFact Chainlit web interface.
It initializes a Chainlit chat application with the three main agents:
- ClaimDetector: Identifies factual claims from user input
- EvidenceHunter: Gathers evidence for those claims
- VerdictWriter: Generates verdicts based on the evidence

To run the web interface:
    chainlit run app.py

For API access, use `src/main.py`.
For CLI access, use `cli.py`.
"""

# Import all necessary UI components from the refactored modules

# Additional components are automatically imported via the @cl decorators
# The event handlers defined in src/ui/app.py and src/ui/events.py will be
# properly registered with Chainlit when this file is run.
