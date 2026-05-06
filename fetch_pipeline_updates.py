#!/usr/bin/env python3
"""
fetch_pipeline_updates.py
─────────────────────────
For each project in tracked_ids.json, search Google News for recent
developments and append them to pipeline_updates.json.

Workflow:
  1. Browse pipeline.html → click 🔖 on projects you want to track
  2. Click "Export tracked" in the utility bar → saves tracked_ids.json
  3. Move tracked_ids.json to this folder (Fitoutpost/)
  4. Run:  python3 fetch_pipeline_updates.py
  5. Run:  python3 build.py --pipeline
  6. Reload pipeline.html — tracked cards show update count + timeline

Output: pipeline_updates.json
"""

from __future__ import annotations
import json, re, sys, time, urllib.request, urllib.parse, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

BASE = Path(__file__).parent
PIPELINE_JSON       = BASE / "pipeline.json"
TRACKED_IDS_FILE    = BASE / "tracked_ids.json"
UPDATES_JSON        = BASE / "pipeline_updates.json"

# ── Config ────────────────────────────────────────────────────────────────────
LOOKBACK_DAYS  = 60          # search news from last N days
MAX_UPDATES    = 20          # max updates to store per project
REQUEST_DELAY  = 1.4         # seconds between fetches (be polite)
TIMEOUT        = 10

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

# ── Google News RSS helper ────────────────────────────────────────────────────
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

def _gnews_fetch(query: str) -> list[dict]:
    url = GNEWS.format(q=urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
    except Exception as e:
        print(f"    ⚠ Fetch error: {e}")
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []

    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    for item in root.iter("item"):
        title   = (item.findtext("title") or "").strip()
        link    = (item.findtext("link")  or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        desc    = (item.findtext("description") or "").strip()

        # Parse date
        try:
            pub_dt = datetime.strptime(pub_raw, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        except Exception:
            pub_dt = datetime.now(timezone.utc)

        if pub_dt < cutoff:
            continue

        # Source from title "... - Source Name"
        source = ""
        if " - " in title:
            parts = title.rsplit(" - ", 1)
            title = parts[0].strip()
            source = parts[1].strip()

        # Clean description (strip HTML tags)
        clean_desc = re.sub(r"<[^>]+>", "", desc).strip()
        clean_desc = re.sub(r"\s+", " ", clean_desc)[:280]

        uid = "upd_" + hashlib.md5(link.encode()).hexdigest()[:10]

        items.append({
            "id":        uid,
            "title":     title,
            "source":    source,
            "url":       link,
            "published": pub_dt.strftime("%Y-%m-%d"),
            "summary":   clean_desc,
        })

    return items


# ── Build search query from project ──────────────────────────────────────────
STRIP_RE = re.compile(r'\b(the|a|an|of|in|at|for|and|or|to|on|from|with|by|new|opens|opening|set|plan|plans|planned)\b', re.I)

def _build_query(project: dict) -> str:
    """Derive a focused search query from a project's title and metadata."""
    title = project.get("title", "")
    country = project.get("country_name", "")
    sector = project.get("sector", "")

    # Extract the most distinctive 4-5 words from the title
    # Remove common words, keep proper nouns and key terms
    words = title.split()[:10]
    meaningful = [w for w in words if len(w) > 3 and not STRIP_RE.match(w)][:4]
    core = " ".join(meaningful) if meaningful else title[:50]

    # Add country if available
    if country and country not in core:
        core = f"{core} {country}"

    # Add sector signal word
    sector_hints = {
        "Hospitality": "hotel",
        "Cultural & Museums": "museum",
        "Offices & Workplace": "office",
        "Retail & Mixed-Use": "retail development",
        "Healthcare": "hospital",
        "Education": "university campus",
        "Sports & Leisure": "stadium resort",
        "Infrastructure & Transport": "terminal development",
        "Commercial Development": "development",
    }
    if sector in sector_hints:
        hint = sector_hints[sector]
        if hint.split()[0].lower() not in core.lower():
            core = f"{core} {hint}"

    return core.strip()


# ── Load / save updates store ─────────────────────────────────────────────────
def load_updates() -> dict:
    if UPDATES_JSON.exists():
        try:
            return json.loads(UPDATES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_updated": "", "tracked": {}}


def save_updates(store: dict):
    store["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    UPDATES_JSON.write_text(
        json.dumps(store, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # 1. Load tracked IDs
    if not TRACKED_IDS_FILE.exists():
        print("❌  tracked_ids.json not found.")
        print("    In pipeline.html: click 🔖 on projects, then 'Export tracked' in the toolbar.")
        sys.exit(1)

    try:
        tracked_data = json.loads(TRACKED_IDS_FILE.read_text(encoding="utf-8"))
        tracked_ids = tracked_data.get("tracked_ids", tracked_data if isinstance(tracked_data, list) else [])
    except Exception as e:
        print(f"❌  Could not parse tracked_ids.json: {e}")
        sys.exit(1)

    if not tracked_ids:
        print("⚠️  tracked_ids.json is empty — nothing to fetch.")
        sys.exit(0)

    # 2. Load pipeline.json to get project details
    if not PIPELINE_JSON.exists():
        print("❌  pipeline.json not found. Run fetch_pipeline.py first.")
        sys.exit(1)

    pipeline_data = json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))
    project_index = {p["id"]: p for p in pipeline_data.get("projects", [])}

    # 3. Load existing updates store
    store = load_updates()

    # 4. For each tracked project, fetch updates
    print(f"🔍  Fetching updates for {len(tracked_ids)} tracked project(s)…\n")
    fetched_total = 0

    for pid in tracked_ids:
        project = project_index.get(pid)
        if not project:
            print(f"  ⚠  {pid} not found in pipeline.json — skipped")
            continue

        title = project.get("title", pid)
        print(f"  [{pid}] {title[:70]}…")

        # Build query
        query = _build_query(project)
        print(f"         Query: {query!r}")

        # Fetch
        results = _gnews_fetch(query)

        # Filter out the original article itself (by URL similarity)
        orig_url = project.get("source_url", "")
        results = [r for r in results if r["url"] != orig_url]

        if not results:
            print(f"         → No new results")
        else:
            print(f"         → {len(results)} result(s)")

        # Merge into store
        if pid not in store["tracked"]:
            store["tracked"][pid] = {
                "project_id": pid,
                "title": title,
                "tracked_since": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "updates": []
            }

        existing_ids = {u["id"] for u in store["tracked"][pid]["updates"]}
        new_count = 0
        for r in results:
            if r["id"] not in existing_ids:
                store["tracked"][pid]["updates"].append(r)
                new_count += 1

        # Sort by date desc, cap at MAX_UPDATES
        store["tracked"][pid]["updates"].sort(key=lambda u: u["published"], reverse=True)
        store["tracked"][pid]["updates"] = store["tracked"][pid]["updates"][:MAX_UPDATES]

        fetched_total += new_count
        if new_count:
            print(f"         → {new_count} new update(s) saved")

        time.sleep(REQUEST_DELAY)

    # 5. Save
    save_updates(store)

    total_tracked = len(store["tracked"])
    print(f"\n✅  pipeline_updates.json — {total_tracked} project(s) tracked, {fetched_total} new update(s) added")
    print("\n    Next: run  python3 build.py --pipeline  to embed updates into pipeline.html")


if __name__ == "__main__":
    main()
