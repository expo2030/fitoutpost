#!/usr/bin/env python3
"""
approve_candidates.py — Merge reviewed company_candidates.json into companies.json.

Usage:
  python approve_candidates.py              # merge all (review_needed=True stubs)
  python approve_candidates.py --dry-run    # show what would be added without writing

Before running: open company_candidates.json, delete any false positives,
edit any stubs that need corrections, then run this script.
"""

import json
import sys
from pathlib import Path

BASE            = Path(__file__).parent
COMPANIES_PATH  = BASE / "companies.json"
CANDIDATES_PATH = BASE / "company_candidates.json"

DRY_RUN = "--dry-run" in sys.argv

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    if not CANDIDATES_PATH.exists():
        print("No company_candidates.json found.")
        return

    candidates = load_json(CANDIDATES_PATH)
    if not candidates:
        print("company_candidates.json is empty.")
        return

    raw = load_json(COMPANIES_PATH)
    if isinstance(raw, list):
        companies = raw
        wrapper = None
    elif isinstance(raw, dict) and "companies" in raw:
        companies = raw["companies"]
        wrapper = raw
    else:
        companies = list(raw.values())
        wrapper = None

    existing_ids   = {c["id"] for c in companies}
    existing_names = {c["name"].lower() for c in companies}

    added = []
    skipped = []
    for c in candidates:
        cid  = c.get("id", "")
        name = c.get("name", "")
        if cid in existing_ids or name.lower() in existing_names:
            skipped.append(name)
            continue
        # Clean up internal tracking fields before merging
        clean = {k: v for k, v in c.items() if not k.startswith("_")}
        clean.pop("review_needed", None)
        clean.pop("source", None)
        added.append(clean)

    print(f"Candidates to add:  {len(added)}")
    print(f"Already in dir:     {len(skipped)}")
    print()

    for c in added:
        print(f"  + {c['name']} ({c.get('hq','?')}) — {c.get('type','?')}")

    if skipped:
        print()
        for name in skipped:
            print(f"  ~ {name} (already exists, skipped)")

    if DRY_RUN:
        print("\n[dry-run] No files written.")
        return

    if not added:
        print("Nothing to add.")
        return

    companies.extend(added)

    if wrapper:
        wrapper["companies"] = companies
        save_json(COMPANIES_PATH, wrapper)
    else:
        save_json(COMPANIES_PATH, companies)

    # Clear approved entries from candidates file
    remaining = [c for c in candidates
                 if c.get("name","").lower() in {a["name"].lower() for a in added} is False]
    # Actually remove the ones we just merged
    merged_names = {a["name"].lower() for a in added}
    remaining = [c for c in candidates if c.get("name","").lower() not in merged_names]
    save_json(CANDIDATES_PATH, remaining)

    print(f"\n✅ Added {len(added)} companies to companies.json")
    print(f"   {len(remaining)} candidates remain in company_candidates.json")
    print(f"\nNext: run 'python build.py --static' and push to update companies_site.html")

if __name__ == "__main__":
    main()
