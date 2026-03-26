#!/usr/bin/env python3
"""
NPPES Database Search Script
Finds all NPI entities associated with Simcha Bendet by searching:
- Authorized Official names (multiple variations)
- Known addresses
- Known phone numbers
"""

import requests
import zipfile
import csv
import os
from datetime import datetime
import re

# Search criteria
NAME_VARIATIONS = [
    "simcha b bendet",
    "simcha bendet",
    "simcha bunim bendet",
    "bunim ben",
    "bendet simcha",
    "bendet, simcha"
]

KNOWN_ADDRESSES = [
    "1255 e 31st",
    "1344 e 24th",
    "439 high rd",
    "286 south main",
    "2265 hovsons",
]

KNOWN_PHONES = [
    "3476689113",
    "9294661305",
    "3479777095",
    "9179600552",
    "7186775909",
]

def download_nppes_data():
    """Download the NPPES data dissemination file"""
    print("=" * 80)
    print("NPPES DATABASE DOWNLOADER")
    print("=" * 80)

    # NPPES Data Dissemination file URL
    url = "https://download.cms.gov/nppes/NPI_Files.html"

    print("\n[INFO] Checking NPPES download page...")
    print(f"[INFO] URL: {url}")

    # The actual download link changes, so we need to find it
    # For now, let's use the known pattern
    base_url = "https://download.cms.gov/nppes/"
    file_pattern = "NPPES_Data_Dissemination_"

    print("\n[WARNING] The NPPES file is 6-8 GB compressed.")
    print("[WARNING] This download may take 10-30 minutes depending on connection speed.")
    print("[WARNING] The uncompressed CSV will be even larger (~20-30 GB).")

    # Try to get the latest file
    try:
        # Check if file already exists
        existing_files = [f for f in os.listdir('.') if f.startswith('npidata_pfile')]
        if existing_files:
            print(f"\n[INFO] Found existing NPPES file: {existing_files[0]}")
            response = input("Use existing file? (y/n): ").lower()
            if response == 'y':
                return existing_files[0]

        # Note: The actual download requires finding the current week's file
        # This is a placeholder - we'll try a different approach
        print("\n[INFO] Direct download of NPPES requires finding the current week's file.")
        print("[INFO] Attempting alternative approach using NPPES API...")

        return None

    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        return None

def search_nppes_api(search_term, search_type="authorized_official"):
    """
    Search NPPES using their registry (not a true API, but web scraping alternative)
    """
    print(f"\n[SEARCHING] {search_type}: {search_term}")
    results = []

    # We'll need to use web scraping or manual search
    # The NPPES doesn't have a public API, so we'd need to:
    # 1. Download full database (preferred)
    # 2. Web scrape the registry site (against ToS)
    # 3. Use commercial NPI lookup services

    return results

def search_csv_file(csv_filename):
    """Search through downloaded NPPES CSV file"""
    print("\n" + "=" * 80)
    print("SEARCHING NPPES DATABASE")
    print("=" * 80)

    results = []

    # NPPES file column structure (these are the key columns we need)
    # The actual file has many more columns
    KEY_COLUMNS = {
        'NPI': 0,
        'Entity Type Code': 1,  # 1 = Individual, 2 = Organization
        'Replacement NPI': 2,
        'Employer Identification Number (EIN)': 3,
        'Provider Organization Name (Legal Business Name)': 4,
        'Provider Last Name (Legal Name)': 5,
        'Provider First Name': 6,
        'Provider Middle Name': 7,
        'Provider Name Prefix Text': 8,
        'Provider Name Suffix Text': 9,
        'Provider Credential Text': 10,
        'Provider First Line Business Mailing Address': 20,
        'Provider Second Line Business Mailing Address': 21,
        'Provider Business Mailing Address City Name': 22,
        'Provider Business Mailing Address State Name': 23,
        'Provider Business Mailing Address Postal Code': 24,
        'Provider Business Practice Location Address First Line': 28,
        'Provider Business Practice Location Address City Name': 30,
        'Provider Business Practice Location Address State Name': 31,
        'Provider Business Practice Location Address Postal Code': 32,
        'Provider Enumeration Date': 36,
        'Last Update Date': 37,
        'NPI Deactivation Date': 39,
        'Provider Gender Code': 41,
        'Authorized Official Last Name': 42,
        'Authorized Official First Name': 43,
        'Authorized Official Middle Name': 44,
        'Authorized Official Title or Position': 45,
        'Authorized Official Telephone Number': 46,
    }

    try:
        with open(csv_filename, 'r', encoding='utf-8', errors='ignore') as f:
            print(f"[INFO] Reading file: {csv_filename}")

            reader = csv.reader(f)
            header = next(reader)  # Skip header

            line_count = 0
            match_count = 0

            for row in reader:
                line_count += 1

                # Progress indicator
                if line_count % 100000 == 0:
                    print(f"[PROGRESS] Processed {line_count:,} records, found {match_count} matches...")

                if len(row) < 47:  # Make sure row has enough columns
                    continue

                # Check Authorized Official name
                ao_first = row[43].lower() if len(row) > 43 else ""
                ao_last = row[42].lower() if len(row) > 42 else ""
                ao_middle = row[44].lower() if len(row) > 44 else ""
                ao_full = f"{ao_first} {ao_middle} {ao_last}".strip()

                # Check addresses
                addr1 = row[28].lower() if len(row) > 28 else ""
                addr2 = row[20].lower() if len(row) > 20 else ""

                # Check phone
                phone = re.sub(r'\D', '', row[46]) if len(row) > 46 else ""

                # Check for matches
                name_match = any(name in ao_full for name in NAME_VARIATIONS)
                addr_match = any(addr in addr1 or addr in addr2 for addr in KNOWN_ADDRESSES)
                phone_match = phone in KNOWN_PHONES if phone else False

                if name_match or addr_match or phone_match:
                    match_count += 1

                    result = {
                        'NPI': row[0] if len(row) > 0 else "",
                        'Entity_Type': 'Organization' if row[1] == '2' else 'Individual',
                        'Organization_Name': row[4] if len(row) > 4 else "",
                        'Address': row[28] if len(row) > 28 else "",
                        'City': row[30] if len(row) > 30 else "",
                        'State': row[31] if len(row) > 31 else "",
                        'Zip': row[32] if len(row) > 32 else "",
                        'Authorized_Official': f"{ao_first} {ao_last}".strip(),
                        'AO_Title': row[45] if len(row) > 45 else "",
                        'Phone': row[46] if len(row) > 46 else "",
                        'Enumeration_Date': row[36] if len(row) > 36 else "",
                        'Last_Update': row[37] if len(row) > 37 else "",
                        'Match_Type': 'Name' if name_match else ('Address' if addr_match else 'Phone'),
                    }

                    results.append(result)
                    print(f"\n[MATCH FOUND] {result['Organization_Name']} (NPI: {result['NPI']})")

            print(f"\n[COMPLETE] Processed {line_count:,} total records")
            print(f"[COMPLETE] Found {match_count} matches")

    except FileNotFoundError:
        print(f"\n[ERROR] File not found: {csv_filename}")
    except Exception as e:
        print(f"\n[ERROR] Error reading file: {e}")

    return results

def save_results(results, output_file='simcha_bendet_entities.csv'):
    """Save results to CSV file"""
    if not results:
        print("\n[INFO] No results to save")
        return

    print(f"\n[SAVING] Writing {len(results)} results to {output_file}")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"[SUCCESS] Results saved to {output_file}")

def main():
    """Main execution function"""
    print("\n" + "=" * 80)
    print("SIMCHA BENDET ENTITY FINDER")
    print("Searching NPPES Database for Associated Entities")
    print("=" * 80)

    print("\n[INFO] Search Criteria:")
    print(f"  Name variations: {len(NAME_VARIATIONS)}")
    for name in NAME_VARIATIONS:
        print(f"    - {name}")

    print(f"\n  Known addresses: {len(KNOWN_ADDRESSES)}")
    for addr in KNOWN_ADDRESSES:
        print(f"    - {addr}")

    print(f"\n  Known phones: {len(KNOWN_PHONES)}")
    for phone in KNOWN_PHONES:
        print(f"    - {phone}")

    # Check for existing NPPES CSV file
    print("\n" + "=" * 80)
    print("CHECKING FOR NPPES DATA FILE")
    print("=" * 80)

    csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'npidata' in f.lower()]

    if csv_files:
        print(f"\n[FOUND] Existing NPPES CSV file: {csv_files[0]}")
        results = search_csv_file(csv_files[0])
    else:
        print("\n[NOT FOUND] No NPPES CSV file found in current directory")
        print("\n[INSTRUCTIONS] To use this script:")
        print("  1. Visit: https://download.cms.gov/nppes/NPI_Files.html")
        print("  2. Download the 'NPPES Data Dissemination' file (ZIP format)")
        print("  3. Extract the CSV file to this directory")
        print("  4. Run this script again")
        print("\n[NOTE] The file is large (~6-8 GB compressed, ~20-30 GB uncompressed)")
        print("[NOTE] Download may take 10-30 minutes depending on connection")

        # Try alternative approach
        print("\n" + "=" * 80)
        print("ALTERNATIVE: MANUAL NPI REGISTRY SEARCH")
        print("=" * 80)
        print("\nYou can manually search the NPI Registry at:")
        print("https://npiregistry.cms.hhs.gov/")
        print("\nSearch by:")
        print("  - Authorized Official: 'Simcha Bendet' or 'Bunim Ben'")
        print("  - Address: '1255 E 31st Street, Brooklyn, NY'")
        print("  - Phone: (347) 668-9113")

        return

    # Save results
    if results:
        output_file = f'simcha_bendet_entities_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        save_results(results, output_file)

        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total entities found: {len(results)}")
        print(f"\nBreakdown by match type:")

        match_types = {}
        for r in results:
            mt = r['Match_Type']
            match_types[mt] = match_types.get(mt, 0) + 1

        for match_type, count in match_types.items():
            print(f"  {match_type}: {count}")

        print(f"\nDistinct organizations: {len(set(r['Organization_Name'] for r in results))}")
        print(f"Distinct NPIs: {len(set(r['NPI'] for r in results))}")

        # Show sample results
        print("\n" + "=" * 80)
        print("SAMPLE RESULTS (First 10)")
        print("=" * 80)
        for i, result in enumerate(results[:10], 1):
            print(f"\n{i}. {result['Organization_Name']}")
            print(f"   NPI: {result['NPI']}")
            print(f"   Address: {result['Address']}, {result['City']}, {result['State']} {result['Zip']}")
            print(f"   Authorized Official: {result['Authorized_Official']} ({result['AO_Title']})")
            print(f"   Match Type: {result['Match_Type']}")

if __name__ == "__main__":
    main()