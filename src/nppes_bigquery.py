"""
NPPES BigQuery Search Module

Provides targeted search functions against the NPPES NPI table in BigQuery.
Designed to be called by the npi-investigator agent during graph expansion.

Table: nppes-investigator.nppes.nppes_npis
Column names have spaces (BigQuery auto-detected from CSV headers).

Usage:
    from nppes_bigquery import NPPESBigQuery

    db = NPPESBigQuery()
    result = db.search_by_npi("1093879322")
    result = db.search_by_phone("2257695377")
    result = db.search_by_zip("70810")
    result = db.search_by_address("10522 S Glenstone")
    result = db.search_by_authorized_official("ripple", "steven")
    result = db.search_by_org_name("smilestars")
"""

from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import json

# -------------------------------------------------------------------
# Credentials — loaded from gcp_key.json (gitignored, never committed)
# Copy gcp_key.json to this directory when setting up on a new machine.
# -------------------------------------------------------------------

import os as _os
_KEY_PATH = _os.path.join(_os.path.dirname(__file__), "gcp_key.json")
with open(_KEY_PATH) as _f:
    SERVICE_ACCOUNT_KEY = json.load(_f)

TABLE = "`nppes-investigator.nppes.nppes_npis`"

# Core columns to return on every query — keeps results readable
SELECT_COLS = """
    NPI,
    `Entity Type Code`                                          AS entity_type,
    `Provider Organization Name _Legal Business Name_`         AS org_name,
    `Provider Last Name _Legal Name_`                          AS last_name,
    `Provider First Name`                                      AS first_name,
    `Provider Middle Name`                                     AS middle_name,
    `Provider Credential Text`                                 AS credential,
    `Provider First Line Business Practice Location Address`   AS address,
    `Provider Business Practice Location Address City Name`    AS city,
    `Provider Business Practice Location Address State Name`   AS state,
    `Provider Business Practice Location Address Postal Code`  AS zip,
    `Provider Business Practice Location Address Telephone Number` AS phone,
    `Provider Business Practice Location Address Fax Number`   AS fax,
    `Authorized Official Last Name`                            AS ao_last,
    `Authorized Official First Name`                           AS ao_first,
    `Authorized Official Middle Name`                          AS ao_middle,
    `Authorized Official Title or Position`                    AS ao_title,
    `Authorized Official Telephone Number`                     AS ao_phone,
    `Provider First Line Business Mailing Address`             AS mailing_address,
    `Provider Business Mailing Address City Name`              AS mailing_city,
    `Provider Business Mailing Address State Name`             AS mailing_state,
    `Provider Business Mailing Address Postal Code`            AS mailing_zip,
    `Provider Enumeration Date`                                AS enumeration_date,
    `Last Update Date`                                         AS last_updated,
    `NPI Deactivation Date`                                    AS deactivation_date,
    `Healthcare Provider Taxonomy Code_1`                      AS taxonomy_code,
    `Provider Sex Code`                                        AS gender
"""


class NPPESBigQuery:

    def __init__(self):
        credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_KEY)
        self.client = bigquery.Client(project="nppes-investigator", credentials=credentials)

    def _run(self, query: str) -> pd.DataFrame:
        return self.client.query(query).result().to_dataframe()

    # ------------------------------------------------------------------
    # Search functions
    # ------------------------------------------------------------------

    def search_by_npi(self, npi: str) -> pd.DataFrame:
        """Direct NPI lookup."""
        q = f"SELECT {SELECT_COLS} FROM {TABLE} WHERE NPI = {int(npi.strip())}"
        return self._run(q)

    def search_by_phone(self, phone: str) -> pd.DataFrame:
        """
        Search by phone number. Strips non-digits before matching.
        Checks both practice location phone and authorized official phone.
        """
        digits = ''.join(c for c in phone if c.isdigit())
        q = f"""
        SELECT {SELECT_COLS} FROM {TABLE}
        WHERE REGEXP_REPLACE(CAST(`Provider Business Practice Location Address Telephone Number` AS STRING), r'[^0-9]', '') = '{digits}'
           OR REGEXP_REPLACE(CAST(`Authorized Official Telephone Number` AS STRING), r'[^0-9]', '') = '{digits}'
           OR REGEXP_REPLACE(CAST(`Provider Business Mailing Address Telephone Number` AS STRING), r'[^0-9]', '') = '{digits}'
        """
        return self._run(q)

    def search_by_zip(self, zip_code: str) -> pd.DataFrame:
        """
        Search all NPIs at a zip code (practice location or mailing).
        Matches on first 5 digits to handle zip+4 variations.
        """
        zip5 = zip_code.strip()[:5]
        q = f"""
        SELECT {SELECT_COLS} FROM {TABLE}
        WHERE SUBSTR(`Provider Business Practice Location Address Postal Code`, 1, 5) = '{zip5}'
           OR SUBSTR(`Provider Business Mailing Address Postal Code`, 1, 5) = '{zip5}'
        """
        return self._run(q)

    def search_by_address(self, street: str) -> pd.DataFrame:
        """
        Substring search on street address (practice location and mailing).
        Pass partial address e.g. '10522 S Glenstone' or '1255 E 31st'.
        Case insensitive.
        """
        street_clean = street.strip().upper()
        q = f"""
        SELECT {SELECT_COLS} FROM {TABLE}
        WHERE UPPER(`Provider First Line Business Practice Location Address`) LIKE '%{street_clean}%'
           OR UPPER(`Provider First Line Business Mailing Address`) LIKE '%{street_clean}%'
        """
        return self._run(q)

    def search_by_authorized_official(self, last_name: str, first_name: str = "") -> pd.DataFrame:
        """
        Search by authorized official name. Last name required, first name optional.
        Case insensitive exact match on last name, substring on first name if provided.
        Agent should handle variations by calling multiple times with different name forms.
        """
        last_clean = last_name.strip().upper()
        q = f"""
        SELECT {SELECT_COLS} FROM {TABLE}
        WHERE UPPER(`Authorized Official Last Name`) = '{last_clean}'
        """
        if first_name.strip():
            first_clean = first_name.strip().upper()
            q += f" AND UPPER(`Authorized Official First Name`) LIKE '{first_clean}%'"
        return self._run(q)

    def search_by_org_name(self, org_name: str) -> pd.DataFrame:
        """
        Substring search on organization legal name and other organization name.
        Case insensitive.
        """
        name_clean = org_name.strip().upper()
        q = f"""
        SELECT {SELECT_COLS} FROM {TABLE}
        WHERE UPPER(`Provider Organization Name _Legal Business Name_`) LIKE '%{name_clean}%'
           OR UPPER(`Provider Other Organization Name`) LIKE '%{name_clean}%'
        """
        return self._run(q)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_results(self, results: list[dict], filepath: str):
        """
        Export final investigation results to Excel.
        results: list of dicts, each with 'npi_data' (DataFrame row) and 'matched_on' string.
        """
        if not results:
            print("No results to export.")
            return

        rows = []
        for entry in results:
            row = dict(entry['npi_data'])
            row['matched_on'] = entry['matched_on']
            row['discovery_order'] = entry.get('discovery_order', '')
            rows.append(row)

        df = pd.DataFrame(rows)

        # Reorder so key fields come first
        front_cols = ['discovery_order', 'matched_on', 'NPI', 'entity_type', 'org_name',
                      'last_name', 'first_name', 'credential', 'address', 'city', 'state',
                      'zip', 'phone', 'fax', 'ao_last', 'ao_first', 'ao_title', 'ao_phone']
        remaining = [c for c in df.columns if c not in front_cols]
        df = df[[c for c in front_cols if c in df.columns] + remaining]

        df.to_excel(filepath, index=False)
        print(f"Exported {len(df)} NPIs to {filepath}")


# ------------------------------------------------------------------
# Helper to print results cleanly during agent sessions
# ------------------------------------------------------------------

def summarize(df: pd.DataFrame, search_type: str, search_value: str) -> str:
    """Returns a compact summary string for agent consumption."""
    if df.empty:
        return f"[{search_type}: '{search_value}'] → 0 results"

    lines = [f"[{search_type}: '{search_value}'] -> {len(df)} result(s)"]
    for _, row in df.iterrows():
        name = row.get('org_name') or f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        npi = row.get('NPI', '')
        addr = row.get('address', '')
        phone = row.get('phone', '')
        ao = f"{row.get('ao_first', '')} {row.get('ao_last', '')}".strip()
        lines.append(f"  NPI {npi} | {name} | {addr} | phone: {phone} | AO: {ao}")
    return '\n'.join(lines)
