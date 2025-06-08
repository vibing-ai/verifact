import json
from difflib import SequenceMatcher

with open('data/testing_data/sampled_claims_with_wiki.json', 'r', encoding='utf-8') as f:
    gold_data = json.load(f)
with open('data/testing_data/evidence_hunter_results.json', 'r', encoding='utf-8') as f:
    hunter_data = json.load(f)

def normalize_stance(stance):
    '''Normalize the stance to a standard format.
    
    Args:
        stance (str): The stance to normalize.

    Returns:
        str: The normalized stance.
    '''
    mapping = {
        "SUPPORTS": "supporting",
        "REFUTES": "contradicting",
        "NOT ENOUGH INFO": "neutral",
        "supporting": "supporting",
        "contradicting": "contradicting",
        "neutral": "neutral"
    }
    return mapping.get(stance.strip(), "neutral")

def simple_similarity(a, b):
    '''Calculate the similarity between two strings.

    Args:
        a (str): The first string.
        b (str): The second string.

    Returns:
        float: The similarity between the two strings.
    '''
    return SequenceMatcher(None, a, b).ratio()

def stance_match(gold_label, hunter_stances):
    '''Check if the stance of the hunter is consistent with the gold label.
    
    Args:
        gold_label (str): The gold label.
        hunter_stances (list): The list of hunter stances.

    Returns:
        bool: True if the stance is consistent, False otherwise.
    '''
    gold_label = gold_label.strip().upper()
    hunter_stances = set(s.lower() for s in hunter_stances)
    if gold_label == "SUPPORTS":
        return "supporting" in hunter_stances
    elif gold_label == "REFUTES":
        return "contradicting" in hunter_stances
    elif gold_label == "NOT ENOUGH INFO":
        return "neutral" in hunter_stances
    return False

def score_claim(gold, hunter, sim_threshold=0.7):
    '''Score the claim.
    
    Args:
        gold (dict): The gold data.
        hunter (dict): The hunter data.
        sim_threshold (float): The similarity threshold.
    
    Returns:
        dict: The score of the claim.
    '''
    gold_evidences = gold['evidence']
    hunter_evidences = hunter['evidence']
    gold_label = gold.get('label', 'NOT ENOUGH INFO')
    hunter_stances = [normalize_stance(ev.get('stance', 'neutral')) for ev in hunter_evidences]
    stance_is_match = stance_match(gold_label, hunter_stances)

    gold_texts = [ev.get('line_text', '') for ev in gold_evidences if ev.get('line_text')]
    hunter_texts = [ev.get('content', '') for ev in hunter_evidences if 'wiki' in (ev.get('source', '')).lower() or 'wikipedia' in (ev.get('source', '')).lower()]
    max_sim = 0.0
    for gt in gold_texts:
        for ht in hunter_texts:
            sim = simple_similarity(gt, ht)
            if sim > max_sim:
                max_sim = sim

    return {
        'stance_match': stance_is_match,
        'max_content_similarity': max_sim
    }

def main():
    stance_correct = 0
    content_sim_total = 0
    detailed_results = []
    n = len(gold_data)
    for gold, hunter in zip(gold_data, hunter_data):
        score = score_claim(gold, hunter)
        if score['stance_match']:
            stance_correct += 1
        content_sim_total += score['max_content_similarity']
        detailed_results.append({
            'claim': gold.get('claim', ''),
            'label': gold.get('label', ''),
            'stance_match': score['stance_match'],
            'max_content_similarity': score['max_content_similarity'],
            'gold_evidence': gold.get('evidence', []),
            'hunter_evidence': hunter.get('evidence', [])
        })
    print(f'Stance accuracy: {stance_correct/n:.2%}')
    print(f'Average max content similarity (wiki source): {content_sim_total/n:.2f}')
    with open('data/testing_data/scoring_report.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, ensure_ascii=False, indent=2)
    print('Detailed scoring report saved to data/testing_data/scoring_report.json')

if __name__ == '__main__':
    main()
