#!/usr/bin/env python3
"""
FitOut Post — Weekly Roundup Generator

Reads news.json, extracts the previous week's articles (Mon–Sun),
groups them geographically (continent → country), and appends an
entry to weekly.json.  Then rebuilds weekly.html via build.py.

Schedule: every Monday at 08:00 Madrid time (Europe/Madrid).

Usage
-----
    python fetch_weekly.py              # last week (default)
    python fetch_weekly.py --weeks-ago 2   # two weeks ago
    python fetch_weekly.py --dry-run    # print only, don't save
"""

import json
import sys
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

BASE = Path(__file__).parent

# ── Continent display order ────────────────────────────────────────────────────
CONTINENT_ORDER = [
    "Europe",
    "Middle East",
    "Asia Pacific",
    "Americas",
    "Africa",
    "Oceania",
    "Global",
]


def monday_of_week(d: date) -> date:
    """Return the Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def week_range(weeks_ago: int = 1):
    """Return (start, end) dates for the target week (Mon inclusive, Sun inclusive)."""
    today = date.today()
    this_monday = monday_of_week(today)
    target_monday = this_monday - timedelta(weeks=weeks_ago)
    target_sunday = target_monday + timedelta(days=6)
    return target_monday, target_sunday


def iso_to_date(iso: str) -> date | None:
    """Parse ISO-8601 datetime string to a date, return None on failure."""
    if not iso:
        return None
    try:
        # Handle offsets like +00:00, +02:00, Z
        iso_clean = iso.replace("Z", "+00:00")
        return datetime.fromisoformat(iso_clean).date()
    except Exception:
        try:
            return date.fromisoformat(iso[:10])
        except Exception:
            return None


def load_articles(news_path: Path) -> list:
    if not news_path.exists():
        print(f"❌  {news_path.name} not found. Run fetch_news.py first.")
        sys.exit(1)
    return json.loads(news_path.read_text(encoding="utf-8")).get("articles", [])


def filter_articles(articles: list, start: date, end: date) -> list:
    """Return articles whose published date falls within [start, end]."""
    result = []
    for a in articles:
        d = iso_to_date(a.get("published", ""))
        if d and start <= d <= end:
            result.append(a)
    return result


def format_article(a: dict, d: date) -> dict:
    return {
        "date":         d.isoformat(),
        "date_display": d.strftime("%-d %b").lstrip("0"),
        "country":      a.get("country") or "—",
        "continent":    a.get("continent") or "Global",
        "headline":     (a.get("title") or "").strip(),
        "source":       a.get("source") or "",
        "url":          a.get("url") or "#",
    }


def group_by_continent(articles: list) -> list:
    """Return list of {continent, articles[]} dicts in display order."""
    buckets: dict[str, list] = {c: [] for c in CONTINENT_ORDER}
    for a in articles:
        c = a["continent"]
        if c not in buckets:
            buckets[c] = []
        buckets[c].append(a)

    # Sort each bucket: country asc, then date asc
    for arts in buckets.values():
        arts.sort(key=lambda x: (x["country"], x["date"]))

    # Build ordered list, skip empty continents
    result = []
    for c in CONTINENT_ORDER:
        if buckets.get(c):
            result.append({"continent": c, "articles": buckets[c]})
    # Any unknown continents at the end
    for c, arts in buckets.items():
        if c not in CONTINENT_ORDER and arts:
            result.append({"continent": c, "articles": arts})
    return result


def build_week_entry(weeks_ago: int = 1) -> dict:
    start, end = week_range(weeks_ago)
    articles_raw = load_articles(BASE / "news.json")
    filtered = filter_articles(articles_raw, start, end)

    formatted = []
    for a in filtered:
        d = iso_to_date(a.get("published", ""))
        if d:
            formatted.append(format_article(a, d))

    # Sort overall by date, then continent, then country
    formatted.sort(key=lambda x: (x["date"], x["continent"], x["country"]))

    groups = group_by_continent(formatted)

    iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    week_id  = f"{start.isocalendar().year}-W{start.isocalendar().week:02d}"

    return {
        "id":         week_id,
        "week_start": start.isoformat(),
        "week_end":   end.isoformat(),
        "label":      f"{start.strftime('%-d %b')} – {end.strftime('%-d %b %Y')}",
        "generated":  iso_now,
        "total":      len(formatted),
        "groups":     groups,
    }


def save_entry(entry: dict) -> None:
    weekly_path = BASE / "weekly.json"
    if weekly_path.exists():
        data = json.loads(weekly_path.read_text(encoding="utf-8"))
    else:
        data = {"last_updated": "", "weeks": []}

    # Replace existing entry for same week id, or prepend
    weeks = data.get("weeks", [])
    weeks = [w for w in weeks if w.get("id") != entry["id"]]
    weeks.insert(0, entry)          # newest first
    weeks = weeks[:52]              # keep at most one year

    data["weeks"] = weeks
    data["last_updated"] = entry["generated"]
    weekly_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅  weekly.json updated — {entry['total']} articles, week {entry['id']}")


def rebuild_html() -> None:
    """Call build.py --weekly to regenerate weekly.html."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(BASE / "build.py"), "--weekly"],
        capture_output=True, text=True, cwd=str(BASE)
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and result.stderr:
        print("⚠️ ", result.stderr.strip())


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    weeks_ago = 1
    dry_run   = "--dry-run" in args

    for arg in args:
        if arg.startswith("--weeks-ago="):
            weeks_ago = int(arg.split("=")[1])
        elif arg == "--weeks-ago" and args.index(arg) + 1 < len(args):
            weeks_ago = int(args[args.index(arg) + 1])

    start, end = week_range(weeks_ago)
    print(f"📅  Target week: {start.strftime('%-d %b')} – {end.strftime('%-d %b %Y')}")

    entry = build_week_entry(weeks_ago)
    print(f"📰  Found {entry['total']} articles across "
          f"{len(entry['groups'])} continent(s)")

    if dry_run:
        print("\n─── DRY RUN — not saving ───────────────────────────────────────")
        for g in entry["groups"]:
            print(f"\n  {g['continent'].upper()} ({len(g['articles'])} articles)")
            for a in g["articles"][:3]:
                print(f"    {a['date_display']:6}  {a['country'][:20]:<20}  {a['headline'][:60]}")
            if len(g["articles"]) > 3:
                print(f"    … and {len(g['articles']) - 3} more")
    else:
        save_entry(entry)
        rebuild_html()
        print(f"\n    Open weekly.html in any browser — no server required.")
