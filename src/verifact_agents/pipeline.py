from typing import Any, Dict, Optional

from src.verifact_agents.claim_detector import claim_detector_agent
from src.verifact_agents.evidence_hunter import evidence_hunter_agent
from src.verifact_agents.verdict_writer import verdict_writer_agent


class FactcheckPipeline:
    def __init__(self, 
                 claim_detector=claim_detector_agent, 
                 evidence_hunter=evidence_hunter_agent, 
                 verdict_writer=verdict_writer_agent):
        self.claim_detector = claim_detector
        self.evidence_hunter = evidence_hunter
        self.verdict_writer = verdict_writer

    async def process(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            # Step 1: Detect claims
            claims = await self.claim_detector.process(text)
            if not claims:
                return None
            claim = claims[0]

            # Step 2: Gather evidence
            evidence = await self.evidence_hunter.process(claim)

            # Step 3: Get verdict
            verdict = await self.verdict_writer.process({
                "claim": claim,
                "evidence": evidence
            })

            return {
                "claim": claim,
                "evidence": evidence,
                "verdict": verdict
            }
        except Exception as e:
            # Log or handle error as needed
            return {"error": str(e)} 