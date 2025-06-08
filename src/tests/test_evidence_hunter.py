import asyncio
import json

from agents import Runner

from verifact_agents.claim_detector import Claim
from verifact_agents.evidence_hunter import Evidence, EvidenceHunter, deduplicate_evidence

SAMPLED_CLAIMS_PATH = 'data/testing_data/sampled_claims_with_wiki.json'
EVIDENCE_RESULTS_PATH = 'data/testing_data/evidence_hunter_results.json'

def load_sampled_claims(path):
    """ Load sampled claims from a JSON file.

    Args:
        path (str): The path to the JSON file containing the sampled claims.

    Returns:
        list[dict]: A list of dictionaries, each containing a sampled claim.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_claim_objects(sampled_claims):
    return [Claim(text=entry['claim']) for entry in sampled_claims]

async def gather_evidence_for_claim(evidence_hunter, claim):
    query = evidence_hunter.query_formulation(claim)
    result = await Runner.run(evidence_hunter.evidence_hunter_agent, query)
    evidences = result.final_output_as(list[Evidence])
    unique_evidences = deduplicate_evidence(evidences)
    return unique_evidences

async def run_evidence_hunter_on_claims(claims):
    evidence_hunter = EvidenceHunter()
    results = []
    for claim in claims:
        evidence = await gather_evidence_for_claim(evidence_hunter, claim)
        results.append({
            "claim": claim.text,
            "evidence": [ev.dict() for ev in evidence] if evidence else []
        })
    return results



if __name__ == "__main__":
    sampled_claims = load_sampled_claims(SAMPLED_CLAIMS_PATH)
    claims = build_claim_objects(sampled_claims)
    evidence_results = asyncio.run(run_evidence_hunter_on_claims(claims))
    with open(EVIDENCE_RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(evidence_results, f, ensure_ascii=False, indent=2)
    print(f"Saved evidence hunter results to {EVIDENCE_RESULTS_PATH}")
