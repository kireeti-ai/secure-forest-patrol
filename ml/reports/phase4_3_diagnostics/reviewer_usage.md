# Reviewer Usage

Run locally on macOS:

```bash
python3 ml/reports/phase4_3_diagnostics/review_tool.py --reviewer reviewer1 --limit 60
```

The tool plays the original file with `afplay`, prompts for a decision, and writes only `ml/datasets/phase4_3_candidate/review_decisions.csv`. `q` exits without marking the current item reviewed. Existing decisions are loaded on resume; conflicting duplicate candidate decisions are rejected.
