#!/usr/bin/env python3
"""
fetch_companies.py — Weekly company directory enrichment via Claude Haiku.

What it does:
  1. Reads news.json + pipeline.json for the past 14 days of signals.
  2. Sends batches of titles+summaries to claude-haiku-4-5 to:
       a. Extract company names that appear in a FIT-OUT role (contractor,
          designer, winner of award, etc.) — NOT as client/owner.
       b. Enrich existing companies: add newly spotted notable_projects.
       c. Draft stub records for genuinely new companies not yet in the directory.
  3. Updates companies.json in place (enrichment applied directly).
  4. Writes company_candidates.json — new companies found, for human review.
  5. Writes company_watch_report.md — weekly digest for Victor.

Requires env var: ANTHROPIC_API_KEY
"""

import json
import os
import re
import sys
import time
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("anthropic package not installed — run: pip install anthropic")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE            = Path(__file__).parent
COMPANIES_PATH  = BASE / "companies.json"
NEWS_PATH       = BASE / "news.json"
PIPELINE_PATH   = BASE / "pipeline.json"
CANDIDATES_PATH = BASE / "company_candidates.json"
REPORT_PATH     = BASE / "company_watch_report.md"

# ── Config ─────────────────────────────────────────────────────────────────
MODEL           = "claude-haiku-4-5-20251001"
LOOKBACK_DAYS   = 14          # how far back to scan for signals
BATCH_SIZE      = 40          # signals per Claude call
MAX_BATCHES     = 8           # cap to control cost (~$0.01-0.03 per run)
MIN_APPEARANCES = 2           # unknown company must appear ≥ N times to be flagged

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ── Helpers ────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def now_utc():
    return datetime.now(timezone.utc)

def cutoff_date():
    return (now_utc() - timedelta(days=LOOKBACK_DAYS)).date().isoformat()


def load_companies():
    raw = load_json(COMPANIES_PATH)
    if isinstance(raw, list):
        return raw
    return raw.get("companies", list(raw.values()))


def build_name_index(companies):
    """Map lowercase name variants → company record."""
    idx = {}
    for c in companies:
        idx[c["name"].lower()] = c
        # also index common short forms
        name = c["name"]
        # strip Ltd/LLC/plc suffixes for matching
        short = re.sub(r'\b(ltd|llc|plc|inc|gmbh|sa|srl|bv|ag|llp|group|co\.?)\b', '', name, flags=re.I).strip('. ')
        if short and short.lower() != name.lower():
            idx[short.lower()] = c
    return idx


def collect_signals():
    """Return list of {title, summary, source, published, type} within lookback window."""
    cutoff = cutoff_date()
    signals = []

    news = load_json(NEWS_PATH)
    for a in news.get("articles", []):
        if a.get("published", "") >= cutoff:
            signals.append({
                "type": "news",
                "title": a.get("title", ""),
                "summary": a.get("summary", "")[:300],
                "source": a.get("source", ""),
                "published": a.get("published", ""),
            })

    pipeline = load_json(PIPELINE_PATH)
    for p in pipeline.get("projects", []):
        if p.get("published", "") >= cutoff:
            signals.append({
                "type": "pipeline",
                "title": p.get("title", ""),
                "summary": p.get("summary", "")[:300],
                "source": p.get("source", ""),
                "published": p.get("published", ""),
                "sector": p.get("sector", ""),
            })

    return signals


# ── Claude extraction ──────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are an expert on the fit-out and interior construction industry.

I will give you a batch of news headlines and summaries about fit-out, interior fit-out, refurbishment, and related construction work.

For each signal, extract any companies that appear in a FIT-OUT DELIVERY role:
- contractors awarded a fit-out contract
- designers/architects delivering an interior project
- companies completing/winning fit-out work
- companies mentioned as fit-out specialist or interior contractor

Do NOT extract:
- Property developers or building owners (clients)
- REITs, funds, or investors
- Generic construction companies doing structural/civils work only
- Companies mentioned only as the project location or client

Return a JSON array. Each element:
{
  "company_name": "Exact name as written",
  "role": "short phrase: e.g. fit-out contractor, interior designer, awarded contract",
  "project": "brief project description, ≤15 words",
  "sector": "one of: Offices, Retail, Hospitality, Healthcare, Education, Residential, Mixed-Use, Other",
  "signal_title": "verbatim headline"
}

If no qualifying companies found in a signal, skip it entirely.
Return [] if nothing qualifies across the whole batch.
Return only valid JSON — no explanation.

SIGNALS:
"""


def call_claude(signals_batch):
    """Send a batch of signals to Claude, return list of extracted company mentions."""
    lines = []
    for i, s in enumerate(signals_batch, 1):
        text = f"{i}. [{s['type'].upper()}] {s['title']}"
        if s.get("summary"):
            text += f"\n   {s['summary'][:200]}"
        lines.append(text)

    prompt = EXTRACTION_PROMPT + "\n".join(lines)

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"  ⚠ Claude error: {e}")
        return []


STUB_PROMPT = """You are an expert researcher on the global fit-out and interior construction industry.

I need a directory stub for the following fit-out company: "{name}"

Context from news: {context}

Return a single JSON object with these fields (use null for unknown):
{{
  "name": "canonical company name",
  "type": "one of: Fit-Out Contractor, Interior Designer, Furniture & FF&E, Design & Build, MEP Contractor, Other",
  "hq": "City, Country",
  "country": "country name",
  "continent": "one of: Europe, Asia, Middle East, Africa, Americas, Oceania",
  "sectors": ["list", "of", "sectors"],
  "description": "2-sentence factual description, max 50 words",
  "website": "https://... or null",
  "employees": "range e.g. 50-200 or null",
  "tags": ["up to 3 short tags"]
}}

Return only valid JSON — no explanation.
"""


def research_new_company(name, contexts):
    """Ask Claude to create a stub record for an unknown company."""
    context_str = " | ".join(contexts[:3])
    prompt = STUB_PROMPT.format(name=name, context=context_str)
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        stub = json.loads(raw)
        stub["id"] = re.sub(r"[^a-z0-9]+", "-", stub.get("name", name).lower()).strip("-")
        stub["source"] = "auto-discovered"
        stub["review_needed"] = True
        stub["notable_projects"] = []
        stub["revenue_gbp_m"] = None
        stub["revenue_year"] = None
        stub["founded"] = None
        stub["parent"] = None
        stub["listed"] = False
        stub["contact"] = {}
        stub["locations"] = []
        stub["services"] = []
        return stub
    except Exception as e:
        print(f"  ⚠ Stub research failed for {name}: {e}")
        return None


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("FitOutPost — Company Directory Enrichment")
    print(f"Model: {MODEL} | Lookback: {LOOKBACK_DAYS} days")
    print("=" * 60)

    companies = load_companies()
    name_idx  = build_name_index(companies)
    signals   = collect_signals()

    print(f"Signals collected: {len(signals)} | Companies in directory: {len(companies)}")

    if not signals:
        print("No signals in lookback window — exiting.")
        return

    # ── Run extraction in batches ──────────────────────────────────────────
    all_mentions = []
    batches = [signals[i:i+BATCH_SIZE] for i in range(0, len(signals), BATCH_SIZE)][:MAX_BATCHES]

    print(f"\nRunning {len(batches)} extraction batches...")
    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i}/{len(batches)} ({len(batch)} signals)...", end=" ", flush=True)
        mentions = call_claude(batch)
        print(f"{len(mentions)} mentions found")
        all_mentions.extend(mentions)
        if i < len(batches):
            time.sleep(1)  # gentle rate limiting

    print(f"\nTotal mentions extracted: {len(all_mentions)}")

    # ── Classify: known vs unknown ─────────────────────────────────────────
    known_updates   = {}   # id → {company, new_projects: []}
    unknown_counts  = {}   # name → [context strings]

    for m in all_mentions:
        raw_name = m.get("company_name", "").strip()
        if not raw_name or len(raw_name) < 3:
            continue

        project_str = m.get("project", "").strip()
        sector      = m.get("sector", "")
        context     = m.get("signal_title", "")

        # Try to match against directory
        match = name_idx.get(raw_name.lower())
        if not match:
            # Try partial: does the raw name appear as substring of any known name?
            for known_name, co in name_idx.items():
                if raw_name.lower() in known_name or known_name in raw_name.lower():
                    match = co
                    break

        if match:
            cid = match["id"]
            if cid not in known_updates:
                known_updates[cid] = {"company": match, "new_projects": []}
            if project_str:
                existing = [p.lower() for p in match.get("notable_projects", [])]
                if project_str.lower() not in existing:
                    known_updates[cid]["new_projects"].append(project_str)
        else:
            if raw_name not in unknown_counts:
                unknown_counts[raw_name] = []
            if context:
                unknown_counts[raw_name].append(context)

    # ── Apply enrichment to known companies ───────────────────────────────
    enriched_count = 0
    for cid, upd in known_updates.items():
        co  = upd["company"]
        new = upd["new_projects"]
        if new:
            existing = co.setdefault("notable_projects", [])
            added = 0
            for proj in new[:3]:  # cap additions per run
                if proj not in existing:
                    existing.insert(0, proj)  # newest first
                    added += 1
            if added:
                print(f"  ✓ Enriched {co['name']}: +{added} project(s)")
                enriched_count += 1

    # ── Research new company candidates ───────────────────────────────────
    candidates = []
    flagged = {name: ctxs for name, ctxs in unknown_counts.items()
               if len(ctxs) >= MIN_APPEARANCES}

    print(f"\nNew company candidates (≥{MIN_APPEARANCES} appearances): {len(flagged)}")

    for name, contexts in sorted(flagged.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  Researching: {name} ({len(contexts)}x)...", end=" ", flush=True)
        stub = research_new_company(name, contexts)
        if stub:
            stub["_appearances"] = len(contexts)
            stub["_contexts"] = contexts[:5]
            candidates.append(stub)
            print(f"✓ {stub.get('hq','?')}")
        else:
            print("✗ skipped")
        time.sleep(0.5)

    # ── Save updated companies.json ────────────────────────────────────────
    # Preserve original wrapper structure if it existed
    raw = load_json(COMPANIES_PATH)
    if isinstance(raw, list):
        save_json(COMPANIES_PATH, companies)
    elif isinstance(raw, dict) and "companies" in raw:
        raw["companies"] = companies
        raw["last_enriched"] = now_utc().isoformat()
        save_json(COMPANIES_PATH, raw)
    else:
        save_json(COMPANIES_PATH, companies)

    print(f"\n✅ companies.json updated — {enriched_count} existing companies enriched")

    # ── Save candidates ────────────────────────────────────────────────────
    existing_candidates = []
    if CANDIDATES_PATH.exists():
        try:
            existing_candidates = load_json(CANDIDATES_PATH)
        except Exception:
            pass

    # Merge: don't duplicate names already in candidates or directory
    existing_names = {c["name"].lower() for c in existing_candidates}
    existing_names.update(name_idx.keys())
    new_candidates = [c for c in candidates if c["name"].lower() not in existing_names]
    all_candidates = new_candidates + existing_candidates  # newest first

    save_json(CANDIDATES_PATH, all_candidates)
    print(f"✅ company_candidates.json — {len(new_candidates)} new stubs, {len(all_candidates)} total pending review")

    # ── Write weekly report ────────────────────────────────────────────────
    report_lines = [
        f"# Company Watch Report — {now_utc().strftime('%Y-%m-%d')}",
        f"",
        f"**Signals scanned:** {len(signals)} (last {LOOKBACK_DAYS} days)  ",
        f"**Mentions extracted:** {len(all_mentions)}  ",
        f"**Existing companies enriched:** {enriched_count}  ",
        f"**New candidates flagged:** {len(new_candidates)}  ",
        f"",
        f"---",
        f"",
        f"## Existing Companies — New Projects Added",
        f"",
    ]

    if enriched_count:
        for cid, upd in known_updates.items():
            if upd["new_projects"]:
                co = upd["company"]
                report_lines.append(f"### {co['name']}")
                for proj in upd["new_projects"][:3]:
                    report_lines.append(f"- {proj}")
                report_lines.append("")
    else:
        report_lines.append("_No new projects added this week._\n")

    report_lines += [
        f"---",
        f"",
        f"## New Company Candidates — Review Required",
        f"",
        f"> Edit `company_candidates.json`, remove any false positives, then run:",
        f"> `python approve_candidates.py` to merge approved stubs into `companies.json`.",
        f"",
    ]

    if new_candidates:
        for c in new_candidates:
            report_lines.append(f"### {c['name']} ⚠ REVIEW NEEDED")
            report_lines.append(f"- **Type:** {c.get('type','?')}")
            report_lines.append(f"- **HQ:** {c.get('hq','?')}")
            report_lines.append(f"- **Sectors:** {', '.join(c.get('sectors', []))}")
            report_lines.append(f"- **Description:** {c.get('description','')}")
            report_lines.append(f"- **Website:** {c.get('website','?')}")
            report_lines.append(f"- **Appearances:** {c.get('_appearances',0)}x in signals")
            report_lines.append(f"- **Contexts:** {' | '.join(c.get('_contexts',[])[:2])}")
            report_lines.append("")
    else:
        report_lines.append("_No new candidates this week._\n")

    report_lines += [
        f"---",
        f"",
        f"## All Pending Candidates",
        f"",
        f"Total in `company_candidates.json`: **{len(all_candidates)}**",
        f"",
    ]
    for c in all_candidates[:20]:
        flag = " ⭐ NEW" if c in new_candidates else ""
        report_lines.append(f"- {c['name']} ({c.get('hq','?')}){flag}")

    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"✅ company_watch_report.md written")
    print(f"\nDone. Run time: {now_utc().strftime('%H:%M UTC')}")


if __name__ == "__main__":
    main()
