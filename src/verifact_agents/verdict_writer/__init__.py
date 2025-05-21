"""VerdictWriter agent for generating verdicts.

This module is responsible for analyzing evidence and generating verdicts
about factual claims with explanations and source citations.
"""

from src.verifact_agents.verdict_writer.writer import Verdict, VerdictWriter

__all__ = ["VerdictWriter", "Verdict"]
