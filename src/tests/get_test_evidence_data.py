import json
import os
import random
from typing import Any

SHARED_TASK_PATH = 'data/testing_data/shared_task_dev.jsonl'
WIKI_PAGES_DIR = 'data/testing_data/wiki-pages/wiki-pages/'
OUTPUT_PATH = 'data/testing_data/sampled_claims_with_wiki.json'

SAMPLE_SIZE = 50

def load_claims(file_path: str) -> list[dict[str, Any]]:
    """Load claims from a jsonl file.
    
    Args:
        file_path (str): The path to the jsonl file.

    Returns:
        List[Dict]: A list of dictionaries containing the claims.
    """
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data.append(json.loads(line))
    except FileNotFoundError as e:
        print(f"Error loading claims from {file_path}: {e}")
        raise
    return data


def sample_claims(data: list[dict], sample_size: int, seed: int | None = 42) -> list[dict]:
    '''Sample claims from the data.
    
    Args:
        data (list[dict]): A list of dictionaries containing the claims.
        sample_size (int): The number of claims to sample.
        seed (int | None): The seed for the random number generator.

    Returns:
        list[dict]: A list of dictionaries containing the sampled claims.
    '''
    rng = random.Random(seed) if seed is not None else random
    return rng.sample(data, sample_size)

def build_wiki_index(wiki_dir: str) -> dict:
    """Traverse all jsonl files in the wiki-pages directory and build a {page_id: text} index.
    
    Args:
        wiki_dir (str): The path to the wiki-pages directory.

    Returns:
        dict: A dictionary containing the {page_id: text} index.
    """
    wiki_index = {}
    for fname in os.listdir(wiki_dir):
        if fname.endswith('.json') or fname.endswith('.jsonl'):
            with open(os.path.join(wiki_dir, fname), 'r', encoding='utf-8') as f:
                for line in f:
                    obj = json.loads(line)
                    if isinstance(obj.get('lines'), str):
                        if '\n' in obj['lines']:
                            obj['lines'] = obj['lines'].split('\\n') if '\\n' in obj['lines'] else obj['lines'].split('\n')
                        else:
                            obj['lines'] = obj['lines'].split('\r\n') if '\r\n' in obj['lines'] else obj['lines'].split('\n')
                    wiki_index[obj['id']] = obj
    return wiki_index

def extract_evidence_page_ids(claim: Any) -> list[str]:
    """Extract the page_id of the evidence from the claim.
    
    Args:
        claim (Dict): A dictionary containing the claim.

    Returns:
        List[str]: A list of page_ids.
    """
    page_ids = set()
    for group in claim.get('evidence', []):
        for item in group:
            if isinstance(item, list) and len(item) > 0:
                page_ids.add(str(item[0]))
    return list(page_ids)

def process_evidence_item(item: Any, wiki_index: dict[str, Any]) -> dict[str, Any]:
    """Process a single evidence item and extract wiki content.
    
    Args:
        item: Evidence item from the claim data.
        wiki_index: Dictionary mapping page IDs to wiki content.
        
    Returns:
        dict: Processed evidence with page title, line index, and text.
    """
    page_title = item[2] if len(item) > 2 else None
    line_idx_in_page = item[3] if len(item) > 3 else None
    line_text = ""
    
    if page_title and line_idx_in_page is not None:
        wiki_obj = wiki_index.get(page_title, {})
        if wiki_obj and "lines" in wiki_obj and isinstance(line_idx_in_page, int):
            lines = wiki_obj["lines"]
            if 0 <= line_idx_in_page < len(lines):
                line_text = lines[line_idx_in_page]
    
    return {
        "page_title": page_title,
        "line_idx_in_page": line_idx_in_page,
        "line_text": line_text
    }

def attach_wiki_content_to_claims(claims: list[dict[str, Any]], wiki_index: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach the wiki content of the evidence of each claim.
    
    Args:
        claims (List[Dict]): A list of dictionaries containing the claims.
        wiki_index (dict): A dictionary containing the {page_id: text} index.

    Returns:
        List[Dict]: A list of dictionaries containing the enriched claims.
    """
    enriched = []
    for claim in claims:
        evidences = claim.get('evidence', [])
        wiki_evidences = []
        for group in evidences:
            for item in group:
                wiki_evidences.append(process_evidence_item(item, wiki_index))
        enriched.append({
            "claim": claim.get("claim", ""),
            "label": claim.get("label", ""),
            "evidence": wiki_evidences
        })
    return enriched

def main():
    claims = load_claims(SHARED_TASK_PATH)
    print(f"Loaded {len(claims)} claims from {SHARED_TASK_PATH}")
    sampled = sample_claims(claims, SAMPLE_SIZE)
    print(f"Sampled {len(sampled)} claims")
    wiki_index = build_wiki_index(WIKI_PAGES_DIR)
    print(f"Built wiki index with {len(wiki_index)} pages")
    enriched = attach_wiki_content_to_claims(sampled, wiki_index)
    print(f"Attached wiki content to {len(enriched)} claims")
    try:
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(enriched, f, ensure_ascii=False, indent=2)
        print(f"Saved to {OUTPUT_PATH}")
    except IOError as e:
        print(f"Error writing to {OUTPUT_PATH}: {e}")
        raise

if __name__ == '__main__':
    main()
