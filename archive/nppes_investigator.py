"""
NPPES NPI Network Investigator

Performs iterative graph expansion against the public NPPES API to find all
NPI profiles associated with a person or organization. Designed to be called
by an agent that handles fuzzy name matching and result interpretation.

Usage:
    from nppes_investigator import NPPESInvestigator

    inv = NPPESInvestigator()
    inv.add_seed_npi("1093879322")
    inv.add_seed_name("steven", "ripple")
    results = inv.run()
    inv.export("output.xlsx")
"""

import requests
import pandas as pd
import json
from typing import Optional

NPPES_API = "https://npiregistry.cms.hhs.gov/api/?version=2.1"


class NPPESInvestigator:

    def __init__(self):
        self.found_npis: dict[str, dict] = {}       # npi -> full profile dict
        self.search_queue: list[dict] = []           # pending searches
        self.completed_searches: list[dict] = []     # search log
        self.searched_keys: set[str] = set()         # dedup search attempts

    # ------------------------------------------------------------------
    # Seed inputs
    # ------------------------------------------------------------------

    def add_seed_npi(self, npi: str):
        """Add a known NPI as a starting point."""
        self._enqueue_search("npi", {"number": npi.strip()}, source="seed")

    def add_seed_name(self, first_name: str, last_name: str, state: Optional[str] = None):
        """Add a person's name as a starting point."""
        params = {"first_name": first_name.strip(), "last_name": last_name.strip(), "limit": 200}
        if state:
            params["state"] = state
        self._enqueue_search("name", params, source="seed")

    def add_seed_org(self, org_name: str, state: Optional[str] = None):
        """Add an organization name as a starting point."""
        params = {"organization_name": org_name.strip(), "limit": 200}
        if state:
            params["state"] = state
        self._enqueue_search("org", params, source="seed")

    # ------------------------------------------------------------------
    # Agent-callable search methods (for dynamic expansion)
    # ------------------------------------------------------------------

    def search_by_npi(self, npi: str):
        """Fetch a specific NPI profile."""
        self._enqueue_search("npi", {"number": npi.strip()}, source="agent")

    def search_by_name(self, first_name: str, last_name: str, state: Optional[str] = None):
        """Search by individual name. Agent should call this with normalized names."""
        params = {"first_name": first_name.strip(), "last_name": last_name.strip(), "limit": 200}
        if state:
            params["state"] = state
        self._enqueue_search("name", params, source="agent")

    def search_by_org(self, org_name: str, state: Optional[str] = None):
        """Search by organization name."""
        params = {"organization_name": org_name.strip(), "limit": 200}
        if state:
            params["state"] = state
        self._enqueue_search("org", params, source="agent")

    def search_by_zip(self, zip_code: str, state: Optional[str] = None):
        """Search all NPIs at a zip code (most productive address search method)."""
        params = {"address_purpose": "LOCATION", "postal_code": zip_code.strip(), "limit": 200}
        if state:
            params["state"] = state
        self._enqueue_search("zip", params, source="agent")

    def search_by_address(self, city: str, state: str, zip_code: Optional[str] = None):
        """Search by city/state, optionally with zip."""
        params = {"address_purpose": "LOCATION", "city": city.strip(), "state": state.strip(), "limit": 200}
        if zip_code:
            params["postal_code"] = zip_code.strip()
        self._enqueue_search("address", params, source="agent")

    # ------------------------------------------------------------------
    # Core run loop
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """
        Process the search queue until empty.
        Returns a summary dict with found NPIs and search log.
        Note: Agent should call search_by_* methods to add new searches
        based on what it finds in intermediate results, then call run() again.
        For fully automated expansion, use run_auto().
        """
        self._process_queue()
        return self._build_summary()

    def run_auto(self) -> dict:
        """
        Fully automated expansion. Extracts searchable fields from each
        discovered profile and queues them automatically. Stops when no
        new NPIs are found. Agent handles fuzzy name resolution on top.
        """
        prev_count = -1
        while len(self.found_npis) != prev_count:
            prev_count = len(self.found_npis)
            self._process_queue()
            self._auto_expand()

        return self._build_summary()

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _enqueue_search(self, search_type: str, params: dict, source: str, matched_on: str = ""):
        key = json.dumps({"type": search_type, "params": params}, sort_keys=True)
        if key in self.searched_keys:
            return
        self.searched_keys.add(key)
        self.search_queue.append({
            "type": search_type,
            "params": params,
            "source": source,
            "matched_on": matched_on
        })

    def _process_queue(self):
        while self.search_queue:
            search = self.search_queue.pop(0)
            self._execute_search(search)

    def _execute_search(self, search: dict):
        params = search["params"].copy()
        try:
            response = requests.get(NPPES_API, params=params, timeout=15)
            data = response.json()
        except Exception as e:
            self.completed_searches.append({**search, "results": 0, "error": str(e)})
            return

        results = data.get("results", [])
        result_count = data.get("result_count", 0)

        self.completed_searches.append({
            **search,
            "results": result_count,
            "truncated": result_count == 200
        })

        for profile in results:
            npi = profile.get("number")
            if not npi:
                continue
            if npi not in self.found_npis:
                self.found_npis[npi] = {
                    "profile": profile,
                    "matched_on": search.get("matched_on") or search["type"],
                    "source_search": search["type"]
                }

    def _auto_expand(self):
        """Extract fields from all found profiles and queue new searches."""
        for npi, entry in self.found_npis.items():
            profile = entry["profile"]
            basic = profile.get("basic", {})
            addresses = profile.get("addresses", [])
            other_names = profile.get("other_names", [])

            # Name searches
            first = basic.get("first_name", "")
            last = basic.get("last_name", "")
            if first and last:
                self._enqueue_search("name",
                    {"first_name": first, "last_name": last, "limit": 200},
                    source="auto", matched_on=f"name: {first} {last}")

            # Authorized official name
            auth_first = basic.get("authorized_official_first_name", "")
            auth_last = basic.get("authorized_official_last_name", "")
            if auth_first and auth_last:
                self._enqueue_search("name",
                    {"first_name": auth_first, "last_name": auth_last, "limit": 200},
                    source="auto", matched_on=f"auth official: {auth_first} {auth_last}")

            # Organization name
            org_name = basic.get("organization_name", "")
            if org_name:
                self._enqueue_search("org",
                    {"organization_name": org_name, "limit": 200},
                    source="auto", matched_on=f"org name: {org_name}")

            # Other names (DBAs, former names, etc.)
            for other in other_names:
                other_org = other.get("organization_name", "")
                if other_org:
                    self._enqueue_search("org",
                        {"organization_name": other_org, "limit": 200},
                        source="auto", matched_on=f"other name: {other_org}")

            # Zip code searches from all addresses
            for addr in addresses:
                zip_code = addr.get("postal_code", "").replace("-", "")
                if zip_code and len(zip_code) >= 5:
                    self._enqueue_search("zip",
                        {"address_purpose": "LOCATION", "postal_code": zip_code, "limit": 200},
                        source="auto", matched_on=f"zip: {zip_code}")

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _build_summary(self) -> dict:
        return {
            "total_npis_found": len(self.found_npis),
            "npi_numbers": list(self.found_npis.keys()),
            "profiles": self._flatten_profiles(),
            "search_log": self.completed_searches
        }

    def _flatten_profiles(self) -> list[dict]:
        rows = []
        for npi, entry in self.found_npis.items():
            profile = entry["profile"]
            basic = profile.get("basic", {})
            addresses = profile.get("addresses", [])
            taxonomies = profile.get("taxonomies", [])
            identifiers = profile.get("identifiers", [])

            # Primary address (LOCATION type preferred)
            location_addr = next((a for a in addresses if a.get("address_purpose") == "LOCATION"), {})
            mailing_addr = next((a for a in addresses if a.get("address_purpose") == "MAILING"), {})
            primary_addr = location_addr or mailing_addr

            # Primary taxonomy
            primary_tax = next((t for t in taxonomies if t.get("primary")), taxonomies[0] if taxonomies else {})

            # Medicaid identifier
            medicaid = next((i.get("identifier") for i in identifiers if "medicaid" in i.get("desc", "").lower()), "")

            rows.append({
                "npi": npi,
                "entity_type": "Individual" if profile.get("enumeration_type") == "NPI-1" else "Organization",
                "name": _full_name(basic),
                "organization_name": basic.get("organization_name", ""),
                "authorized_official": _auth_official(basic),
                "address": _format_address(primary_addr),
                "city": primary_addr.get("city", ""),
                "state": primary_addr.get("state", ""),
                "zip": primary_addr.get("postal_code", ""),
                "phone": primary_addr.get("telephone_number", ""),
                "fax": primary_addr.get("fax_number", ""),
                "taxonomy_code": primary_tax.get("code", ""),
                "taxonomy_desc": primary_tax.get("desc", ""),
                "medicaid_id": medicaid,
                "enumeration_date": basic.get("enumeration_date", ""),
                "last_updated": basic.get("last_updated", ""),
                "matched_on": entry["matched_on"]
            })
        return rows

    def export(self, filepath: str):
        """Export results to Excel with profiles and search log on separate sheets."""
        summary = self._build_summary()

        profiles_df = pd.DataFrame(summary["profiles"])

        log_df = pd.DataFrame([{
            "search_type": s["type"],
            "params": json.dumps(s["params"]),
            "results": s.get("results", 0),
            "matched_on": s.get("matched_on", ""),
            "source": s.get("source", ""),
            "truncated": s.get("truncated", False),
            "error": s.get("error", "")
        } for s in summary["search_log"]])

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            profiles_df.to_excel(writer, sheet_name="NPI Profiles", index=False)
            log_df.to_excel(writer, sheet_name="Search Log", index=False)

        print(f"Exported {len(profiles_df)} NPI profiles to {filepath}")

    def get_profiles_json(self) -> str:
        """Return profiles as JSON string — for agent consumption."""
        return json.dumps(self._flatten_profiles(), indent=2)

    def get_search_log_json(self) -> str:
        """Return search log as JSON string — for agent consumption."""
        return json.dumps(self.completed_searches, indent=2)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _full_name(basic: dict) -> str:
    parts = [
        basic.get("first_name", ""),
        basic.get("middle_name", ""),
        basic.get("last_name", ""),
        basic.get("credential", "")
    ]
    return " ".join(p for p in parts if p).strip()


def _auth_official(basic: dict) -> str:
    parts = [
        basic.get("authorized_official_first_name", ""),
        basic.get("authorized_official_last_name", ""),
        basic.get("authorized_official_credential", ""),
        basic.get("authorized_official_title_or_position", "")
    ]
    return " ".join(p for p in parts if p).strip()


def _format_address(addr: dict) -> str:
    parts = [
        addr.get("address_1", ""),
        addr.get("address_2", ""),
        addr.get("city", ""),
        addr.get("state", ""),
        addr.get("postal_code", "")
    ]
    return ", ".join(p for p in parts if p).strip()


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    inv = NPPESInvestigator()

    # Example: python nppes_investigator.py npi 1093879322
    # Example: python nppes_investigator.py name steven ripple
    # Example: python nppes_investigator.py org "smilestars"

    if len(sys.argv) < 3:
        print("Usage:")
        print("  python nppes_investigator.py npi <npi_number>")
        print("  python nppes_investigator.py name <first> <last> [state]")
        print("  python nppes_investigator.py org <org_name> [state]")
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == "npi":
        inv.add_seed_npi(sys.argv[2])
    elif mode == "name":
        state = sys.argv[4] if len(sys.argv) > 4 else None
        inv.add_seed_name(sys.argv[2], sys.argv[3], state)
    elif mode == "org":
        state = sys.argv[3] if len(sys.argv) > 3 else None
        inv.add_seed_org(sys.argv[2], state)

    print("Running automated expansion...")
    results = inv.run_auto()
    print(f"Found {results['total_npis_found']} NPIs: {results['npi_numbers']}")

    output_file = "nppes_results.xlsx"
    inv.export(output_file)
