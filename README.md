# NPI Network Investigator

A Claude Code-powered tool for NPI network investigation. Given a seed NPI or provider name, it expands a graph of connections through the NPPES database to find all associated NPIs via shared phones, addresses, authorized officials, and organization names.

Intended use: FWA (Fraud, Waste, Abuse) research — establishing whether a set of providers are part of a common network.

---

## Setup

### 1. Install dependencies

```bash
pip install google-cloud-bigquery google-auth pandas db-dtypes openpyxl
```

### 2. Add credentials

Copy `gcp_key.json` (GCP service account key) to the project root. This file is gitignored and must be obtained separately.

The service account needs BigQuery read access to the `nppes-investigator` project.

---

## Running an Investigation

Start Claude Code in this directory and describe what you want to investigate:

- An NPI number: `investigate NPI 1093879322`
- A person's name: `investigate Steven Ripple`
- An organization: `investigate SmileStars Dental`

The agent will iteratively search BigQuery, follow connections (phones, addresses, authorized officials, org names), and produce:

1. An Excel file with all found NPIs and their discovery trail
2. A written summary grouping NPIs by network cluster and flagging likely noise

---

## How It Works

The investigation uses a graph expansion approach:

1. **Seed** — look up the starting NPI or name
2. **Extract** — pull phone numbers, addresses, authorized official names, org names from each found NPI
3. **Search** — query BigQuery for other NPIs sharing those values
4. **Iterate** — repeat until no new NPIs are found

High-signal fields (phone numbers, authorized official names) are always followed. Lower-signal fields (zip codes, common addresses) are followed with judgment to avoid noise.

Each NPI in the output includes a `matched_on` trail showing exactly how it was connected to the network (e.g., `phone: 2257695377 found on NPI 1093879322`).

---

## Repository Structure

```
├── src/
│   └── nppes_bigquery.py       # BigQuery query module used by the agent
├── archive/                    # Superseded approaches (API-based, local CSV)
├── .claude/
│   └── agents/
│       ├── npi-investigator.md      # NPI graph expansion agent
│       └── referral-investigator.md # FWA referral justification agent
└── gcp_key.json                # GCP credentials — gitignored, never commit
```
