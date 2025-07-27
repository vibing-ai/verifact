import json
import secrets
from pathlib import Path
from typing import Any

# Download the dataset from https://fever.ai/dataset/fever.html
# The dataset is available for download from the FEVER website.
# Extract the wiki-pages.tar.gz file to the wiki-pages directory.
# Put the dataset in the following directory structure within the `verifact` project:
# |-- verifact
# |-- data
# |-- testing_data
# |-- shared_task_dev.jsonl
# |-- wiki_pages

SHARED_TASK_PATH = "data/testing_data/shared_task_dev.jsonl"
WIKI_PAGES_DIR = "data/testing_data/wiki-pages/wiki-pages/"
OUTPUT_PATH = "data/testing_data/sampled_claims_with_wiki.json"

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
        with Path(file_path).open(encoding="utf-8") as f:
            data.extend(json.loads(line) for line in f)
    except FileNotFoundError as e:
        error_msg = f"Error loading claims from {file_path}: {e}"
        raise FileNotFoundError(error_msg) from e
    return data


def sample_claims(data: list[dict], sample_size: int, seed: int | None = 42) -> list[dict]:
    """Sample claims from the data.

    Args:
        data (list[dict]): A list of dictionaries containing the claims.
        sample_size (int): The number of claims to sample.
        seed (int | None): The seed for the random number generator (ignored for secrets.SystemRandom).

    Returns:
        list[dict]: A list of dictionaries containing the sampled claims.
    """
    indices = secrets.SystemRandom().sample(range(len(data)), sample_size)
    return [data[i] for i in indices]


def split_lines(lines_str):
    if "\\n" in lines_str:
        return lines_str.split("\\n")
    if "\n" in lines_str:
        return lines_str.split("\n")
    if "\r\n" in lines_str:
        return lines_str.split("\r\n")
    return [lines_str]


def build_wiki_index(wiki_dir: str) -> dict:
    wiki_index = {}
    wiki_path = Path(wiki_dir)
    for fname in wiki_path.iterdir():
        if fname.suffix in (".json", ".jsonl"):
            with fname.open(encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    if isinstance(obj.get("lines"), str):
                        obj["lines"] = split_lines(obj["lines"])
                    wiki_index[obj["id"]] = obj
    return wiki_index


def extract_evidence_page_ids(claim: Any) -> list[str]:
    """Extract the page_id of the evidence from the claim.

    Args:
        claim (Dict): A dictionary containing the claim.

    Returns:
        List[str]: A list of page_ids.
    """
    page_ids = set()
    for group in claim.get("evidence", []):
        for item in group:
            if isinstance(item, list) and len(item) > 0:
                page_ids.add(str(item[0]))
    return list(page_ids)


def get_line_text(wiki_obj, line_idx_in_page):
    if wiki_obj and "lines" in wiki_obj and isinstance(line_idx_in_page, int):
        lines = wiki_obj["lines"]
        if 0 <= line_idx_in_page < len(lines):
            return lines[line_idx_in_page]
    return ""


def process_evidence_item(item: Any, wiki_index: dict[str, Any]) -> dict[str, Any]:
    """Process a single evidence item and extract wiki content.

    Args:
        item: Evidence item from the claim data.
        wiki_index: Dictionary mapping page IDs to wiki content.

    Returns:
        dict: Processed evidence with page title, line index, and text.
    """
    page_title_index = 2
    line_index = 3
    page_title = item[page_title_index] if len(item) > page_title_index else None
    line_idx_in_page = item[line_index] if len(item) > line_index else None
    line_text = ""
    if page_title and line_idx_in_page is not None:
        wiki_obj = wiki_index.get(page_title, {})
        line_text = get_line_text(wiki_obj, line_idx_in_page)
    return {"page_title": page_title, "line_idx_in_page": line_idx_in_page, "line_text": line_text}


def attach_wiki_content_to_claims(
    claims: list[dict[str, Any]], wiki_index: dict[str, Any]
) -> list[dict[str, Any]]:
    """Attach the wiki content of the evidence of each claim.

    Args:
        claims (List[Dict]): A list of dictionaries containing the claims.
        wiki_index (dict): A dictionary containing the {page_id: text} index.

    Returns:
        List[Dict]: A list of dictionaries containing the enriched claims.
    """
    enriched = []
    for claim in claims:
        evidences = claim.get("evidence", [])
        wiki_evidences = []
        wiki_evidences.extend(
            process_evidence_item(item, wiki_index)
            for group in evidences
            for item in group
        )
        enriched.append(
            {
                "claim": claim.get("claim", ""),
                "label": claim.get("label", ""),
                "evidence": wiki_evidences,
            }
        )
    return enriched


def main():
    claims = load_claims(SHARED_TASK_PATH)
    sampled = sample_claims(claims, SAMPLE_SIZE)
    wiki_index = build_wiki_index(WIKI_PAGES_DIR)
    enriched = attach_wiki_content_to_claims(sampled, wiki_index)
    with Path(OUTPUT_PATH).open("w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
