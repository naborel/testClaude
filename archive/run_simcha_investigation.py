"""
Investigation script for Simcha Benedet NPI profiles.
Runs multiple name variation searches, automated expansion, and exports results.
"""

import sys
import json
sys.path.insert(0, r"c:\Users\nabor\VSCodeProjects\testClaude")
from nppes_investigator import NPPESInvestigator

inv = NPPESInvestigator()

# --- Seed searches: full name and plausible variations ---
name_variations = [
    ("simcha", "benedet"),
    ("sim",    "benedet"),
    ("s",      "benedet"),
    ("simcha", "b"),          # last name initial
    ("simch",  "benedet"),    # truncated first
    ("simcha", "benede"),     # truncated last
    ("simcha", "benedict"),   # common misspelling
    ("simcha", "bendet"),     # dropped letter
    ("simcha", "benedetti"),  # extended variant
]

for first, last in name_variations:
    inv.add_seed_name(first, last)

print(f"Seeded {len(name_variations)} name variation searches.")
print("Running automated expansion...")

results = inv.run_auto()

print(f"\n=== INITIAL AUTO-EXPANSION COMPLETE ===")
print(f"Total NPIs found: {results['total_npis_found']}")
print(f"NPI numbers: {results['npi_numbers']}")

# --- Round 2: manual fuzzy expansion based on any results ---
profiles = results["profiles"]

# Collect unique zip codes and authorized official names for further expansion
zips_seen = set()
auth_names_seen = set()

for p in profiles:
    z = p.get("zip", "").replace("-", "")
    if z and len(z) >= 5:
        zips_seen.add(z[:5])
    auth = p.get("authorized_official", "")
    if auth:
        auth_names_seen.add(auth)

print(f"\nExpanding on {len(zips_seen)} unique zip codes from found profiles...")
for z in zips_seen:
    inv.search_by_zip(z)

# Additional fuzzy first-name truncations that authorized officials sometimes use
extra_variations = [
    ("sim", "ben"),
    ("s",   "ben"),
    ("simcha", "bened"),
]
for first, last in extra_variations:
    inv.search_by_name(first, last)

# Run again to process new searches
results2 = inv.run_auto()

print(f"\n=== FINAL RESULTS ===")
print(f"Total NPIs found: {results2['total_npis_found']}")
print(f"NPI numbers: {results2['npi_numbers']}")

# --- Print profiles as JSON for agent review ---
print("\n--- PROFILES JSON ---")
print(inv.get_profiles_json())

print("\n--- SEARCH LOG JSON ---")
print(inv.get_search_log_json())

# --- Export ---
output_path = r"c:\Users\nabor\VSCodeProjects\testClaude\simcha_benedet_npis.xlsx"
inv.export(output_path)
print(f"\nExport complete: {output_path}")
