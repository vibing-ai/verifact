import asyncio
import json
from pathlib import Path

from agents import Runner

from verifact_agents.claim_detector import Claim
from verifact_agents.evidence_hunter import (
    Evidence,
    EvidenceHunter,
    deduplicate_evidence,
)

SAMPLED_CLAIMS_PATH = "data/testing_data/sampled_claims_with_wiki.json"
EVIDENCE_RESULTS_PATH = "data/testing_data/evidence_hunter_results.json"


def load_sampled_claims(path):
    """Load sampled claims from a JSON file.

    Args:
        path (str): The path to the JSON file containing the sampled claims.

    Returns:
        list[dict]: A list of dictionaries, each containing a sampled claim.
    """
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def build_claim_objects(sampled_claims):
    """Build claim objects from sampled claims.

    Args:
        sampled_claims (list[dict]): A list of dictionaries, each containing a sampled claim.

    Returns:
        list[Claim]: A list of claim objects.
    """
    return [
        Claim(text=entry["claim"], verdict="", confidence=0.0, explanation="", sources=[])
        for entry in sampled_claims
    ]


async def gather_evidence_for_claim(evidence_hunter, claim):
    query = evidence_hunter.query_formulation(claim)
    try:
        result = await Runner.run(evidence_hunter.evidence_hunter_agent, query)
        evidences = result.final_output_as(list[Evidence])
        return deduplicate_evidence(evidences)
    except Exception:
        return []


async def run_evidence_hunter_on_claims(claims):
    evidence_hunter = EvidenceHunter()
    results = []

    async def process_claim(claim):
        try:
            evidence = await gather_evidence_for_claim(evidence_hunter, claim)
            return {
                "claim": claim.text,
                "evidence": [ev.dict() for ev in evidence] if evidence else [],
            }
        except Exception as e:
            return {"claim": claim.text, "evidence": [], "error": f"{e!s}"}

    for claim in claims:
        result = await process_claim(claim)
        results.append(result)
    return results


if __name__ == "__main__":
    sampled_claims = load_sampled_claims(SAMPLED_CLAIMS_PATH)
    claims = build_claim_objects(sampled_claims)

    test_claims = claims

    evidence_results = asyncio.run(run_evidence_hunter_on_claims(test_claims))

    with Path(EVIDENCE_RESULTS_PATH).open("w", encoding="utf-8") as f:
        json.dump(evidence_results, f, ensure_ascii=False, indent=2)
