#!/usr/bin/env python3
"""
FitOut Post — Weekly Roundup Generator

Reads news.json, pipeline.json, and tenders.json, extracts the previous
week's signals (Mon–Sun), groups each signal type geographically
(continent → country), and appends an entry to weekly.json.
Then rebuilds weekly.html via build.py.

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

# ── Award keyword detection (mirrors build.py) ─────────────────────────────────
AWARD_KEYWORDS = [
    "awarded", "wins contract", "win contract", "won contract",
    "secures contract", "secured contract", "appointed contractor",
    "appoints contractor", "signs contract", "signed contract",
    "contract signed", "contract win", "fit-out contract",
    "interior contract", "design-and-build contract",
    "appointed to deliver", "appointed to fit", "appointed to refurbish",
    "construction contract", "fitout contract", "bags contract",
    "clinches contract", "lands contract", "lands deal",
    "wins deal", "wins project", "selected as contractor", "appointed as contractor",
    "awarded the contract", "awarded contract", "awarded fit-out",
    "main contractor appointed", "contractor selected", "contractor appointed",
]

AWARD_NEGATIVE_KEYWORDS = [
    "award-winning", "award winning", "award-nominated",
    "design award", "awards ceremony", "award scheme",
    "awards programme", "awards program", "shortlisted for",
    "shortlisted at", "finalist at", "winner of the",
    "won the award", "won an award", "receives award",
    "received award", "prize winner", "prize-winning",
    "accolade", "recognition award", "industry award",
    "best workplace award", "design awards 2", "interior design award",
]


# ── Date helpers ───────────────────────────────────────────────────────────────

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
        iso_clean = iso.replace("Z", "+00:00")
        return datetime.fromisoformat(iso_clean).date()
    except Exception:
        try:
            return date.fromisoformat(iso[:10])
        except Exception:
            return None


def fmt_date_display(d: date) -> str:
    return d.strftime("%-d %b").lstrip("0")


def norm_continent(raw: str) -> str:
    """Normalise non-standard continent labels to a known value."""
    raw = (raw or "").strip()
    if raw in ("Other", "other", "Unknown", "unknown", ""):
        return "Global"
    return raw


# ── Data loaders ───────────────────────────────────────────────────────────────

def load_news(path: Path) -> list:
    if not path.exists():
        print(f"⚠️   {path.name} not found — skipping news")
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("articles", [])


def load_pipeline(path: Path) -> list:
    if not path.exists():
        print(f"⚠️   {path.name} not found — skipping pipeline")
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("projects", [])


def load_tenders(path: Path) -> list:
    if not path.exists():
        print(f"⚠️   {path.name} not found — skipping tenders")
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("tenders", [])


# ── Formatters ────────────────────────────────────────────────────────────────

def format_news_item(a: dict, d: date) -> dict:
    return {
        "date":         d.isoformat(),
        "date_display": fmt_date_display(d),
        "country":      a.get("country") or "—",
        "continent":    norm_continent(a.get("continent", "")),
        "headline":     (a.get("title") or a.get("headline") or "").strip(),
        "source":       a.get("source") or "",
        "url":          a.get("url") or "#",
    }


def format_pipeline_item(p: dict, d: date) -> dict:
    return {
        "date":         d.isoformat(),
        "date_display": fmt_date_display(d),
        "country":      p.get("country_name") or p.get("country") or "—",
        "continent":    norm_continent(p.get("continent", "")),
        "title":        (p.get("title") or "").strip(),
        "sector":       p.get("sector") or "",
        "source":       p.get("source") or "",
        "url":          p.get("source_url") or p.get("url") or "#",
        "summary":      (p.get("summary") or "")[:200],
    }


def format_tender_item(t: dict, d: date) -> dict:
    return {
        "date":          d.isoformat(),
        "date_display":  fmt_date_display(d),
        "country":       t.get("issuer_country_name") or t.get("issuer_country") or "—",
        "continent":     norm_continent(t.get("continent", "")),
        "title":         (t.get("title") or "").strip(),
        "issuer":        t.get("issuer") or "",
        "category":      t.get("category") or "",
        "deadline":      t.get("deadline") or "",
        "deadline_days": t.get("deadline_days"),
        "source":        t.get("source") or "",
        "url":           t.get("source_url") or t.get("url") or "#",
    }


def format_award_item(a: dict, d: date) -> dict:
    return {
        "date":         d.isoformat(),
        "date_display": fmt_date_display(d),
        "country":      a.get("country") or "—",
        "continent":    norm_continent(a.get("continent", "")),
        "headline":     (a.get("title") or a.get("headline") or "").strip(),
        "source":       a.get("source") or "",
        "url":          a.get("url") or "#",
    }


# ── Filtering ─────────────────────────────────────────────────────────────────

def filter_by_date(items: list, start: date, end: date,
                   date_field: str = "published") -> list:
    """Return items whose date_field falls within [start, end]."""
    result = []
    for item in items:
        d = iso_to_date(item.get(date_field, ""))
        if d and start <= d <= end:
            result.append((item, d))
    return result


def is_award(article: dict) -> bool:
    text = ((article.get("headline") or article.get("title") or "") + " " +
            (article.get("description") or article.get("summary") or "")).lower()
    has_kw  = any(kw in text for kw in AWARD_KEYWORDS)
    has_neg = any(kw in text for kw in AWARD_NEGATIVE_KEYWORDS)
    is_signal = article.get("signal_type", "").lower() == "award"
    return (is_signal or has_kw) and not has_neg


# ── Continent grouping ────────────────────────────────────────────────────────

def group_by_continent(formatted: list) -> list:
    """Return list of {continent, items[]} dicts in display order.
    Each item in `formatted` must have a 'continent' key.
    """
    buckets: dict[str, list] = {c: [] for c in CONTINENT_ORDER}
    for item in formatted:
        c = item.get("continent", "Global")
        if c not in buckets:
            buckets[c] = []
        buckets[c].append(item)

    # Sort each bucket: country asc, then date asc
    for items in buckets.values():
        items.sort(key=lambda x: (x.get("country", ""), x.get("date", "")))

    result = []
    for c in CONTINENT_ORDER:
        if buckets.get(c):
            result.append({"continent": c, "items": buckets[c]})
    for c, items in buckets.items():
        if c not in CONTINENT_ORDER and items:
            result.append({"continent": c, "items": items})
    return result


# ── Main entry builder ────────────────────────────────────────────────────────

def build_week_entry(weeks_ago: int = 1) -> dict:
    start, end = week_range(weeks_ago)

    # ── NEWS ──────────────────────────────────────────────────────────────────
    news_raw  = load_news(BASE / "news.json")
    news_week = filter_by_date(news_raw, start, end, "published")
    news_fmt  = [format_news_item(a, d) for a, d in news_week]
    news_fmt.sort(key=lambda x: (x["date"], x["continent"], x["country"]))
    news_groups = group_by_continent(news_fmt)

    # ── PIPELINE ──────────────────────────────────────────────────────────────
    pl_raw   = load_pipeline(BASE / "pipeline.json")
    pl_week  = filter_by_date(pl_raw, start, end, "published")
    pl_fmt   = [format_pipeline_item(p, d) for p, d in pl_week]
    pl_fmt.sort(key=lambda x: (x["date"], x["continent"], x["country"]))
    pl_groups = group_by_continent(pl_fmt)

    # ── TENDERS ───────────────────────────────────────────────────────────────
    td_raw   = load_tenders(BASE / "tenders.json")
    td_week  = filter_by_date(td_raw, start, end, "published")
    td_fmt   = [format_tender_item(t, d) for t, d in td_week]
    td_fmt.sort(key=lambda x: (x["date"], x["continent"], x["country"]))
    td_groups = group_by_continent(td_fmt)

    # ── AWARDS (from news, keyword-filtered) ──────────────────────────────────
    aw_fmt = []
    for a, d in news_week:
        if is_award(a):
            aw_fmt.append(format_award_item(a, d))
    aw_fmt.sort(key=lambda x: (x["date"], x["continent"], x["country"]))
    aw_groups = group_by_continent(aw_fmt)

    # ── Totals ────────────────────────────────────────────────────────────────
    total = len(news_fmt) + len(pl_fmt) + len(td_fmt) + len(aw_fmt)

    iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    week_id = f"{start.isocalendar().year}-W{start.isocalendar().week:02d}"

    return {
        "id":              week_id,
        "week_start":      start.isoformat(),
        "week_end":        end.isoformat(),
        "label":           f"{start.strftime('%-d %b')} – {end.strftime('%-d %b %Y')}",
        "generated":       iso_now,
        "total":           total,
        "news_total":      len(news_fmt),
        "pipeline_total":  len(pl_fmt),
        "tenders_total":   len(td_fmt),
        "awards_total":    len(aw_fmt),
        "groups":          news_groups,       # news by continent
        "pipeline_groups": pl_groups,         # pipeline by continent
        "tenders_groups":  td_groups,         # tenders by continent
        "awards_groups":   aw_groups,         # contract awards by continent
    }


def save_entry(entry: dict) -> None:
    weekly_path = BASE / "weekly.json"
    if weekly_path.exists():
        data = json.loads(weekly_path.read_text(encoding="utf-8"))
    else:
        data = {"last_updated": "", "weeks": []}

    weeks = data.get("weeks", [])
    weeks = [w for w in weeks if w.get("id") != entry["id"]]
    weeks.insert(0, entry)          # newest first
    weeks = weeks[:52]              # keep at most one year

    data["weeks"] = weeks
    data["last_updated"] = entry["generated"]
    weekly_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅  weekly.json updated — {entry['total']} signals "
          f"(news:{entry['news_total']} pipeline:{entry['pipeline_total']} "
          f"tenders:{entry['tenders_total']} awards:{entry['awards_total']}), "
          f"week {entry['id']}")


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
    print(f"📰  News:     {entry['news_total']} articles across {len(entry['groups'])} continent(s)")
    print(f"🏗️   Pipeline: {entry['pipeline_total']} projects across {len(entry['pipeline_groups'])} continent(s)")
    print(f"📋  Tenders:  {entry['tenders_total']} tenders across {len(entry['tenders_groups'])} continent(s)")
    print(f"🏆  Awards:   {entry['awards_total']} awards across {len(entry['awards_groups'])} continent(s)")
    print(f"─────────────────────────────────────────────────")
    print(f"     Total:   {entry['total']} signals")

    if dry_run:
        print("\n─── DRY RUN — not saving ───────────────────────────────────────")
        for section, label in [
            ("groups", "NEWS"),
            ("pipeline_groups", "PIPELINE"),
            ("tenders_groups", "TENDERS"),
            ("awards_groups", "AWARDS"),
        ]:
            groups = entry.get(section, [])
            if not groups:
                continue
            print(f"\n  ── {label} ──")
            for g in groups:
                items = g.get("items", g.get("articles", []))
                print(f"  {g['continent'].upper()} ({len(items)} items)")
                for it in items[:2]:
                    title = it.get("headline") or it.get("title") or "—"
                    print(f"    {it.get('date_display',''):6}  {it.get('country','')[:18]:<18}  {title[:55]}")
                if len(items) > 2:
                    print(f"    … and {len(items) - 2} more")
    else:
        save_entry(entry)
        rebuild_html()
        print(f"\n    Open weekly.html in any browser — no server required.")
