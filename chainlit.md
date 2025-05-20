# VeriFact: AI-Powered Fact-Checking

VeriFact is a smart fact-checking assistant that helps you verify the accuracy of claims by searching for evidence on the web and analyzing the results.

## How to Use

1. **Enter text with claims**: Type or paste any text containing factual claims you'd like to verify.
2. **Review detected claims**: VeriFact will identify claims that can be fact-checked and show them to you.
3. **Explore evidence**: For each claim, you'll see evidence gathered from various sources. Click on source links to view detailed information.
4. **Examine verdicts**: Review the verdict for each claim along with an explanation of how it was determined.
5. **Export results**: Download your fact-check results for sharing or future reference.

## Features

- **Claim Detection**: Automatically identifies check-worthy factual claims from text
- **Evidence Gathering**: Searches reliable sources to find relevant information about claims
- **Verdict Generation**: Analyzes evidence to determine whether claims are true, false, or need more context
- **Interactive UI**: Explore evidence and see the fact-checking process step-by-step
- **Results Export**: Save fact-check results for later use or sharing
- **History Tracking**: Access your past fact-checks in the history panel

## Settings

You can customize your fact-checking experience using the settings menu:

- **Maximum Claims**: Set how many claims to check from your input (1-10)
- **Show Detailed Evidence**: Toggle to show or hide detailed evidence information
- **Show Confidence Scores**: Toggle to show or hide confidence ratings for verdicts

## About

VeriFact is built with a state-of-the-art language model pipeline featuring three specialized agents:

1. **ClaimDetector**: Identifies factual claims from user input
2. **EvidenceHunter**: Gathers evidence for those claims
3. **VerdictWriter**: Generates verdicts based on the evidence

For API access, use `src/main.py`. For CLI access, use `cli.py`.
