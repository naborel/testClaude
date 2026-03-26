# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

NPI network investigation tool for FWA (Fraud, Waste, Abuse) research. Searches the NPPES NPI registry via BigQuery to find all NPIs connected to a person or organization through shared phones, addresses, authorized officials, and org names.

## Repository Structure

```
testClaude/
├── src/
│   └── nppes_bigquery.py        # BigQuery query module (active tool)
├── archive/                     # Superseded scripts (API-based, CSV-based approaches)
├── .claude/
│   ├── agents/
│   │   ├── npi-investigator.md  # NPI graph expansion agent
│   │   └── referral-investigator.md  # FWA referral justification agent
│   └── settings.local.json
└── gcp_key.json                 # GCP service account key — gitignored, never commit
```

## BigQuery Access

- Project: `nppes-investigator`, Dataset: `nppes`, Table: `nppes_npis`
- Credentials loaded from `gcp_key.json` in the project root (gitignored)
- Copy `gcp_key.json` to project root when setting up on a new machine
- Service account: `nppes-reader@nppes-investigator.iam.gserviceaccount.com`

## Running Investigations

```python
import sys
sys.path.insert(0, r'c:\Users\nabor\VSCodeProjects\testClaude\src')
from nppes_bigquery import NPPESBigQuery, summarize

db = NPPESBigQuery()
df = db.search_by_npi("1093879322")
print(summarize(df, "npi", "1093879322"))
```

The `npi-investigator` agent drives this module for full graph expansion investigations.

## Claude Code Permissions

The `.claude/settings.local.json` restricts allowed Bash commands to `git config:*`. If you need to run other commands, the user will be prompted to approve them.

## Git

- Main branch: `main`
- Feature work happens on: `feat`
- Remote: https://github.com/naborel/testClaude
