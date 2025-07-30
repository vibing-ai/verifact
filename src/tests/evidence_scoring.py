import json
from difflib import SequenceMatcher
from pathlib import Path

GOLD_DATA_PATH = "data/testing_data/sampled_claims_with_wiki.json"
HUNTER_DATA_PATH = "data/testing_data/evidence_hunter_results.json"
SCORE_REPORT_PATH = "data/testing_data/scoring_report.json"


def load_data():
    """Load gold and hunter data from JSON files.

    Returns:
        tuple: A tuple containing the gold and hunter data.
    """
    try:
        with Path(GOLD_DATA_PATH).open(encoding="utf-8") as f:
            gold_data = json.load(f)
        with Path(HUNTER_DATA_PATH).open(encoding="utf-8") as f:
            hunter_data = json.load(f)
    except FileNotFoundError as e:
        error_msg = f"Error loading data files: {e}"
        raise FileNotFoundError(error_msg) from e
    return gold_data, hunter_data


def normalize_stance(stance):
    """Normalize the stance to a standard format.

    Args:
        stance (str): The stance to normalize.

    Returns:
        str: The normalized stance.
    """
    mapping = {
        "SUPPORTS": "supporting",
        "REFUTES": "contradicting",
        "NOT ENOUGH INFO": "neutral",
        "supporting": "supporting",
        "contradicting": "contradicting",
        "neutral": "neutral",
    }
    return mapping.get(stance.strip(), "neutral")


def simple_similarity(a, b):
    """Calculate the similarity between two strings.

    Args:
        a (str): The first string.
        b (str): The second string.

    Returns:
        float: The similarity between the two strings.
    """
    return SequenceMatcher(None, a, b).ratio()


def stance_match(gold_label, hunter_stances):
    """Check if the stance of the hunter is consistent with the gold label.

    Args:
        gold_label (str): The gold label.
        hunter_stances (list): The list of hunter stances.

    Returns:
        bool: True if the stance is consistent, False otherwise.
    """
    gold_label = gold_label.strip().upper()
    hunter_stances = {s.lower() for s in hunter_stances}
    if gold_label == "SUPPORTS":
        return "supporting" in hunter_stances
    if gold_label == "REFUTES":
        return "contradicting" in hunter_stances
    if gold_label == "NOT ENOUGH INFO":
        return "neutral" in hunter_stances
    return False


def get_max_similarity(gold_texts, hunter_texts):
    max_sim = 0.0
    for gt in gold_texts:
        for ht in hunter_texts:
            sim = simple_similarity(gt, ht)
            max_sim = max(max_sim, sim)
    return max_sim


def score_claim(gold, hunter, sim_threshold=0.7):
    """Score the claim.

    Args:
        gold (dict): The gold data.
        hunter (dict): The hunter data.
        sim_threshold (float): The similarity threshold.

    Returns:
        dict: The score of the claim.
    """
    gold_evidences = gold["evidence"]
    hunter_evidences = hunter["evidence"]
    gold_label = gold.get("label", "NOT ENOUGH INFO")
    hunter_stances = [normalize_stance(ev.get("stance", "neutral")) for ev in hunter_evidences]
    stance_is_match = stance_match(gold_label, hunter_stances)

    gold_texts = [ev.get("line_text", "") for ev in gold_evidences if ev.get("line_text")]
    hunter_texts = [
        ev.get("content", "")
        for ev in hunter_evidences
        if "wiki" in (ev.get("source", "")).lower() or "wikipedia" in (ev.get("source", "")).lower()
    ]
    max_sim = get_max_similarity(gold_texts, hunter_texts)

    return {"stance_match": stance_is_match, "max_content_similarity": max_sim}


def main():
    stance_correct = 0
    content_sim_total = 0
    detailed_results = []
    gold_data, hunter_data = load_data()
    len(gold_data)
    for gold, hunter in zip(gold_data, hunter_data, strict=True):
        score = score_claim(gold, hunter)
        if score["stance_match"]:
            stance_correct += 1
        content_sim_total += score["max_content_similarity"]
        detailed_results.append(
            {
                "claim": gold.get("claim", ""),
                "label": gold.get("label", ""),
                "stance_match": score["stance_match"],
                "max_content_similarity": score["max_content_similarity"],
                "gold_evidence": gold.get("evidence", []),
                "hunter_evidence": hunter.get("evidence", []),
            }
        )
    with Path(SCORE_REPORT_PATH).open("w", encoding="utf-8") as f:
        json.dump(detailed_results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
