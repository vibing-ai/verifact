# FEVER Dataset Testing Guide

This project includes test scripts that use the [FEVER (Fact Extraction and VERification) dataset](https://fever.ai/dataset/fever.html) to evaluate our fact-checking system performance.

## Quick Setup

1. **Download the dataset** from [https://fever.ai/dataset/fever.html](https://fever.ai/dataset/fever.html):
   - Shared Task Development Dataset (Labelled)
   - Pre-processed Wikipedia Pages (June 2017 dump)

2. **Set up the directory structure**:
   ```
   verifact/
   ├── data/
   │   └── testing_data/
   │       ├── shared_task_dev.jsonl
   │       └── wiki-pages/
   │           └── wiki-pages/
   │               ├── A/
   │               ├── B/
   │               └── ... (other directories)
   ```

3. **Run the tests**:
   ```bash
   cd src/tests
   python get_test_evidence_data.py    # Prepare test data
   python test_evidence_hunter.py      # Test evidence hunting
   python evidence_scoring.py          # Evaluate performance
   ```

## What the Tests Do

- **Data Preparation**: Extracts Wikipedia content for evidence from the FEVER dataset
- **Evidence Hunting**: Tests our system's ability to find relevant evidence
- **Performance Evaluation**: Compares our results against the gold standard

## Expected Results

The tests will generate:
- `sampled_claims_with_wiki.json`: Enriched claims with Wikipedia evidence
- `evidence_hunter_results.json`: Evidence found by our system
- `scoring_report.json`: Detailed performance metrics

## Detailed Documentation

For complete instructions, see [src/tests/README.md](src/tests/README.md).

## Citation

If using FEVER dataset, cite:
```bibtex
@inproceedings{Thorne18Fever,
    author = {Thorne, James and Vlachos, Andreas and Christodoulopoulos, Christos and Mittal, Arpit},
    title = {{FEVER}: a Large-scale Dataset for Fact Extraction and {VERification}},
    booktitle = {NAACL-HLT},
    year = {2018}
}
``` 