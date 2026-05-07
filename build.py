#!/usr/bin/env python3
"""
FitOut Post — Site Builder

Embeds data JSON into HTML templates using <script type="application/json">.
Works on file://, http://, and any browser without restrictions.

Produces:
  news.html        — main news page
  site.html        — alias of index.html
  alphaedge.html   — curated reading (α Edge)
  betaedge.html    — industry polling (β Edge)
  BUILD_INFO.txt   — human-readable build receipt

Source templates: _template.html, _alphaedge_template.html, _betaedge_template.html
                  (never overwrite these files)

Usage:
    python build.py              # build everything
    python build.py --news       # rebuild news only
    python build.py --alphaedge  # rebuild AlphaEdge only
    python build.py --betaedge   # rebuild BetaEdge only
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent

# ── News build ────────────────────────────────────────────────────────────────
TEMPLATE      = BASE / "_template.html"
NEWS_OUTPUTS  = [BASE / "news.html", BASE / "site.html"]
DATA_SLOT     = "<!--FITOUT-DATA-SLOT-->"
STAMP_SLOT    = "<!--BUILD-STAMP-SLOT-->"
DATA_SLOT_ID  = "fitout-data"

# ── AlphaEdge build ───────────────────────────────────────────────────────────
AE_TEMPLATE   = BASE / "_alphaedge_template.html"
AE_OUTPUT     = BASE / "alphaedge.html"
AE_DATA_FILE  = BASE / "alphaedge.json"
AE_DATA_SLOT  = "<!--ALPHAEDGE-DATA-SLOT-->"
AE_SLOT_ID    = "alphaedge-data"

# ── BetaEdge build ────────────────────────────────────────────────────────────
BE_TEMPLATE   = BASE / "_betaedge_template.html"
BE_OUTPUT     = BASE / "betaedge.html"
BE_DATA_FILE  = BASE / "polls.json"
BE_DATA_SLOT  = "<!--BETAEDGE-DATA-SLOT-->"
BE_SLOT_ID    = "betaedge-data"

# ── GammaEdge build ──────────────────────────────────────────────────────────
GE_TEMPLATE   = BASE / "_gammaedge_template.html"
GE_OUTPUT     = BASE / "gammaedge.html"
GE_DATA_FILE  = BASE / "gammaedge.json"
GE_DATA_SLOT  = "<!--GAMMAEDGE-DATA-SLOT-->"
GE_SLOT_ID    = "gammaedge-data"

# ── Weekly Roundup build ───────────────────────────────────────────────────────
WR_TEMPLATE   = BASE / "_weekly_template.html"
WR_OUTPUT     = BASE / "weekly.html"
WR_DATA_FILE  = BASE / "weekly.json"
WR_DATA_SLOT  = "<!--WEEKLY-DATA-SLOT-->"
WR_SLOT_ID    = "weekly-data"

# ── Intelligence build ────────────────────────────────────────────────────────
IN_TEMPLATE   = BASE / "_intelligence_template.html"
IN_OUTPUT     = BASE / "intelligence.html"
IN_DATA_FILE  = BASE / "intelligence.json"
IN_DATA_SLOT  = "<!--INTELLIGENCE-DATA-SLOT-->"
IN_SLOT_ID    = "intelligence-data"

# ── Tenders build ─────────────────────────────────────────────────────────────
TD_TEMPLATE   = BASE / "_tenders_template.html"
TD_OUTPUT     = BASE / "tenders.html"
TD_DATA_FILE  = BASE / "tenders.json"
TD_DATA_SLOT  = "<!--TENDERS-DATA-SLOT-->"
TD_SLOT_ID    = "tenders-data"

# ── Pipeline build ────────────────────────────────────────────────────────────
PL_TEMPLATE   = BASE / "_pipeline_template.html"
PL_OUTPUT     = BASE / "pipeline.html"
PL_DATA_FILE  = BASE / "pipeline.json"
PL_DATA_SLOT  = "<!--PIPELINE-DATA-SLOT-->"
PL_SLOT_ID    = "pipeline-data"


def _embed_json(template_text: str, data: dict, slot: str, slot_id: str) -> str:
    """Replace slot placeholder with an embedded <script type="application/json"> block."""
    if slot not in template_text:
        raise ValueError(f"Slot '{slot}' not found in template")
    j = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    j = j.replace("</", "<\\/")   # prevent premature </script> closure
    tag = (
        f'<script type="application/json" id="{slot_id}">\n'
        f'{j}\n'
        f'</script>'
    )
    return template_text.replace(slot, tag, 1)


def build(news_path: str = "news.json") -> None:
    """Build index.html + site.html from news.json + _template.html."""
    news_file = BASE / news_path

    if not news_file.exists():
        print(f"❌  {news_path} not found. Run fetch_news.py first.")
        sys.exit(1)
    if not TEMPLATE.exists():
        print(f"❌  Template {TEMPLATE.name} not found.")
        sys.exit(1)

    news     = json.loads(news_file.read_text(encoding="utf-8"))
    template = TEMPLATE.read_text(encoding="utf-8")
    n        = news["total_articles"]

    now        = datetime.now(timezone.utc)
    stamp_iso  = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp_disp = now.strftime("Built %d %b %Y %H:%M UTC")

    built = _embed_json(template, news, DATA_SLOT, DATA_SLOT_ID)
    built = built.replace(STAMP_SLOT, stamp_iso, 1)

    for out in NEWS_OUTPUTS:
        out.write_text(built, encoding="utf-8")
        sz = out.stat().st_size / 1024
        print(f"✅  {out.name} — {n} articles, {stamp_disp}, {sz:.0f} KB")

    _write_receipt(n, news_path, stamp_disp)
    print(f"✅  BUILD_INFO.txt written")
    print(f"\n    Open index.html in any browser — no server required.")


def build_alphaedge(data_path: str = "alphaedge.json") -> None:
    """Build alphaedge.html from alphaedge.json + _alphaedge_template.html."""
    data_file = BASE / data_path

    if not AE_TEMPLATE.exists():
        print(f"❌  Template {AE_TEMPLATE.name} not found.")
        return

    # Create empty alphaedge.json if missing (first run)
    if not data_file.exists():
        empty = {"last_updated": "", "total_articles": 0, "articles": []}
        data_file.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    data = json.loads(data_file.read_text(encoding="utf-8"))
    tmpl = AE_TEMPLATE.read_text(encoding="utf-8")
    n    = data.get("total_articles", len(data.get("articles", [])))

    built = _embed_json(tmpl, data, AE_DATA_SLOT, AE_SLOT_ID)
    AE_OUTPUT.write_text(built, encoding="utf-8")
    sz = AE_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  alphaedge.html — {n} articles, {now}, {sz:.0f} KB")


def build_betaedge(data_path: str = "polls.json") -> None:
    """Build betaedge.html from polls.json + _betaedge_template.html."""
    data_file = BASE / data_path

    if not BE_TEMPLATE.exists():
        print(f"❌  Template {BE_TEMPLATE.name} not found.")
        return

    # Create empty polls.json if missing (first run)
    if not data_file.exists():
        empty = {"polls": []}
        data_file.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    raw  = json.loads(data_file.read_text(encoding="utf-8"))
    tmpl = BE_TEMPLATE.read_text(encoding="utf-8")

    # Include vote_counts if votes.json exists alongside polls.json
    votes_file = BASE / "votes.json"
    if votes_file.exists():
        try:
            votes = json.loads(votes_file.read_text(encoding="utf-8")).get("votes", [])
            for p in raw.get("polls", []):
                pv = [v for v in votes if v.get("poll_id") == p["id"]]
                counts = {o: 0 for o in p.get("options", [])}
                for v in pv:
                    opt = v.get("option", "")
                    if opt in counts:
                        counts[opt] += 1
                p["vote_counts"]  = counts
                p["total_votes"]  = len(pv)
        except Exception:
            pass

    n = len(raw.get("polls", []))
    built = _embed_json(tmpl, raw, BE_DATA_SLOT, BE_SLOT_ID)
    BE_OUTPUT.write_text(built, encoding="utf-8")
    sz  = BE_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  betaedge.html — {n} polls, {now}, {sz:.0f} KB")


def build_gammaedge(data_path: str = "gammaedge.json") -> None:
    """Build gammaedge.html from gammaedge.json + _gammaedge_template.html."""
    data_file = BASE / data_path

    if not GE_TEMPLATE.exists():
        print(f"❌  Template {GE_TEMPLATE.name} not found.")
        return

    if not data_file.exists():
        empty = {"last_updated": "", "total_games": 0, "games": []}
        data_file.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    data = json.loads(data_file.read_text(encoding="utf-8"))
    tmpl = GE_TEMPLATE.read_text(encoding="utf-8")
    n    = len(data.get("games", []))

    built = _embed_json(tmpl, data, GE_DATA_SLOT, GE_SLOT_ID)
    GE_OUTPUT.write_text(built, encoding="utf-8")
    sz  = GE_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  gammaedge.html — {n} game(s), {now}, {sz:.0f} KB")


def build_intelligence(data_path: str = "intelligence.json") -> None:
    """Build intelligence.html from intelligence.json + _intelligence_template.html."""
    data_file = BASE / data_path

    if not IN_TEMPLATE.exists():
        print(f"❌  Template {IN_TEMPLATE.name} not found.")
        return

    if not data_file.exists():
        empty = {"last_updated": "", "total_datapoints": 0, "periods": []}
        data_file.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    data = json.loads(data_file.read_text(encoding="utf-8"))
    tmpl = IN_TEMPLATE.read_text(encoding="utf-8")
    n    = data.get("total_datapoints", 0)

    built = _embed_json(tmpl, data, IN_DATA_SLOT, IN_SLOT_ID)
    IN_OUTPUT.write_text(built, encoding="utf-8")
    sz  = IN_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  intelligence.html — {n} datapoint(s), {now}, {sz:.0f} KB")


def build_weekly(data_path: str = "weekly.json") -> None:
    """Build weekly.html from weekly.json + _weekly_template.html."""
    data_file = BASE / data_path

    if not WR_TEMPLATE.exists():
        print(f"❌  Template {WR_TEMPLATE.name} not found.")
        return

    # Create empty weekly.json if missing
    if not data_file.exists():
        empty = {"last_updated": "", "weeks": []}
        data_file.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    data = json.loads(data_file.read_text(encoding="utf-8"))
    tmpl = WR_TEMPLATE.read_text(encoding="utf-8")
    n    = len(data.get("weeks", []))

    built = _embed_json(tmpl, data, WR_DATA_SLOT, WR_SLOT_ID)
    WR_OUTPUT.write_text(built, encoding="utf-8")
    sz  = WR_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  weekly.html — {n} week(s), {now}, {sz:.0f} KB")


def build_tenders(data_path: str = "tenders.json") -> None:
    """Embed tenders data into the tenders template."""
    if not TD_TEMPLATE.exists():
        print(f"❌  Template {TD_TEMPLATE.name} not found.")
        return

    # Create empty tenders.json if missing
    if not TD_DATA_FILE.exists():
        empty = {"last_updated": "", "total": 0, "by_continent": {}, "by_status": {},
                 "by_category": {}, "by_source": {}, "tenders": []}
        TD_DATA_FILE.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    data = json.loads(TD_DATA_FILE.read_text(encoding="utf-8"))
    tmpl = TD_TEMPLATE.read_text(encoding="utf-8")
    n    = len(data.get("tenders", []))

    built = _embed_json(tmpl, data, TD_DATA_SLOT, TD_SLOT_ID)
    TD_OUTPUT.write_text(built, encoding="utf-8")
    sz  = TD_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  tenders.html — {n} tender(s), {now}, {sz:.0f} KB")


def build_pipeline(data_path: str = "pipeline.json") -> None:
    """Embed pipeline data into the pipeline template, merging tracked updates if present."""
    if not PL_TEMPLATE.exists():
        print(f"❌  Template {PL_TEMPLATE.name} not found.")
        return

    # Create empty pipeline.json if missing
    if not PL_DATA_FILE.exists():
        empty = {"last_updated": "", "total": 0, "by_continent": {}, "by_sector": {}, "projects": []}
        PL_DATA_FILE.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    data = json.loads(PL_DATA_FILE.read_text(encoding="utf-8"))
    tmpl = PL_TEMPLATE.read_text(encoding="utf-8")

    # Merge tracked updates if pipeline_updates.json exists
    updates_file = BASE / "pipeline_updates.json"
    merged_count = 0
    if updates_file.exists():
        try:
            updates_data = json.loads(updates_file.read_text(encoding="utf-8"))
            tracked = updates_data.get("tracked", {})
            if tracked:
                # Build index of project updates keyed by project ID
                upd_index = {pid: rec.get("updates", []) for pid, rec in tracked.items()}
                for p in data.get("projects", []):
                    if p.get("id") in upd_index:
                        p["updates"] = upd_index[p["id"]]
                        merged_count += 1
        except Exception as e:
            print(f"  ⚠  Could not merge pipeline_updates.json: {e}")

    n = data.get("total", len(data.get("projects", [])))

    # ── Performance: do NOT inline 5,000+ signals into the HTML ──────────────
    # The template already has a fetch("pipeline.json") fallback; use it.
    # We inject an empty <script> so the slot resolves but textContent is blank.
    empty_slot = f'<script type="application/json" id="{PL_SLOT_ID}"></script>'
    built = tmpl.replace(PL_DATA_SLOT, empty_slot, 1)
    PL_OUTPUT.write_text(built, encoding="utf-8")
    sz  = PL_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    upd_note = f", {merged_count} tracked with updates" if merged_count else ""
    print(f"✅  pipeline.html — {n} project(s){upd_note}, {now}, {sz:.0f} KB")


AW_TEMPLATE   = BASE / "_awards_template.html"
AW_OUTPUT     = BASE / "awards.html"
AW_DATA_SLOT  = "<!--AWARDS-DATA-SLOT-->"
AW_SLOT_ID    = "awards-data"

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

# Negative keywords — if any of these appear in the text, exclude the article
# These fire on the common false-positive "award-winning design" pattern
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

def build_awards(news_path: str = "news.json", pipeline_path: str = "pipeline.json") -> None:
    """Build awards.html by extracting contract award signals from news + pipeline data."""
    import re as _re

    if not AW_TEMPLATE.exists():
        print(f"❌  Template {AW_TEMPLATE.name} not found.")
        return

    awards = []

    # ── Extract from news.json ────────────────────────────────────────────────
    news_file = BASE / news_path
    if news_file.exists():
        news = json.loads(news_file.read_text(encoding="utf-8"))
        for a in news.get("articles", []):
            text = ((a.get("headline") or a.get("title") or "") + " " +
                    (a.get("description") or a.get("summary") or "")).lower()
            is_award_signal = a.get("signal_type", "").lower() == "award"
            has_award_kw    = any(kw in text for kw in AWARD_KEYWORDS)
            has_neg_kw      = any(kw in text for kw in AWARD_NEGATIVE_KEYWORDS)
            if (is_award_signal or has_award_kw) and not has_neg_kw:
                awards.append({
                    "id":           a.get("id", ""),
                    "headline":     a.get("headline") or a.get("title", ""),
                    "url":          a.get("url", ""),
                    "source":       a.get("source", ""),
                    "pub_date":     a.get("pub_date", ""),
                    "date_display": a.get("date_display", ""),
                    "country":      a.get("country") or a.get("geo_country", ""),
                    "continent":    a.get("continent") or a.get("geo_continent", ""),
                    "sector":       a.get("sector", ""),
                    "signal_type":  "Award",
                    "_source":      "news",
                })

    # ── Extract from pipeline.json ────────────────────────────────────────────
    pipeline_file = BASE / pipeline_path
    if pipeline_file.exists():
        pl = json.loads(pipeline_file.read_text(encoding="utf-8"))
        for a in pl.get("items", []):
            text = ((a.get("headline") or a.get("title") or "") + " " +
                    (a.get("description") or a.get("summary") or "")).lower()
            has_award_kw = any(kw in text for kw in AWARD_KEYWORDS)
            has_neg_kw   = any(kw in text for kw in AWARD_NEGATIVE_KEYWORDS)
            if has_award_kw and not has_neg_kw:
                awards.append({
                    "id":           a.get("id", ""),
                    "headline":     a.get("headline") or a.get("title", ""),
                    "url":          a.get("url", ""),
                    "source":       a.get("source", ""),
                    "pub_date":     a.get("pub_date", ""),
                    "date_display": a.get("date_display", ""),
                    "country":      a.get("country") or a.get("geo_country", ""),
                    "continent":    a.get("continent") or a.get("geo_continent", ""),
                    "sector":       a.get("sector", ""),
                    "signal_type":  "Award",
                    "_source":      "pipeline",
                })

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in awards:
        key = a.get("url") or a.get("id")
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    # Sort by pub_date descending
    unique.sort(key=lambda x: x.get("pub_date", ""), reverse=True)

    data = {
        "total_awards": len(unique),
        "generated": datetime.now(timezone.utc).isoformat(),
        "awards": unique,
    }

    tmpl  = AW_TEMPLATE.read_text(encoding="utf-8")
    built = _embed_json(tmpl, data, AW_DATA_SLOT, AW_SLOT_ID)
    AW_OUTPUT.write_text(built, encoding="utf-8")

    sz  = AW_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  awards.html — {len(unique)} award signals, {now}, {sz:.0f} KB")


def build_sitemap() -> None:
    """Auto-generate sitemap.xml from all HTML pages in the site root and countries/."""
    BASE_URL = "https://fitoutpost.com"
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Priority / changefreq rules
    RULES = {
        "index.html":        ("1.0", "daily"),
        "news.html":         ("0.9", "daily"),
        "home.html":         ("0.9", "daily"),
        "news.html":         ("0.9", "daily"),
        "tenders.html":      ("0.9", "daily"),
        "pipeline.html":     ("0.9", "daily"),
        "events.html":       ("0.8", "monthly"),
        "companies_site.html": ("0.8", "weekly"),
        "intelligence.html": ("0.8", "weekly"),
        "weekly.html":       ("0.8", "weekly"),
        "awards.html":       ("0.7", "weekly"),
        "alphaedge.html":    ("0.6", "weekly"),
        "betaedge.html":     ("0.6", "weekly"),
        "gammaedge.html":    ("0.6", "monthly"),
        "about.html":        ("0.5", "monthly"),
        "contact.html":      ("0.5", "monthly"),
        "register.html":     ("0.5", "monthly"),
        "pricing.html":      ("0.5", "monthly"),
        "advertise.html":    ("0.4", "monthly"),
        "api.html":          ("0.4", "monthly"),
        "legal.html":        ("0.3", "yearly"),
    }

    urls = []

    # Root HTML pages (exclude private/build files)
    EXCLUDE = {"credentials.html", "site.html", "companies.html", "timeline.html"}
    for p in sorted(BASE.glob("*.html")):
        if p.name.startswith("_") or p.name in EXCLUDE:
            continue
        priority, changefreq = RULES.get(p.name, ("0.5", "monthly"))
        urls.append((f"{BASE_URL}/{p.name}", today, changefreq, priority))

    # Country pages
    countries_dir = BASE / "countries"
    if countries_dir.exists():
        for p in sorted(countries_dir.glob("*.html")):
            urls.append((f"{BASE_URL}/countries/{p.name}", today, "weekly", "0.6"))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for loc, lastmod, changefreq, priority in urls:
        lines.append(f"  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append(f"  </url>")
    lines.append("</urlset>")

    sitemap_path = BASE / "sitemap.xml"
    sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅  sitemap.xml — {len(urls)} URLs")


def build_companies_site(data_path: str = "companies.json") -> None:
    """Rebuild the embedded companies data in companies_site.html."""
    import re as _re
    co_file = BASE / data_path
    site_file = BASE / "companies_site.html"

    if not co_file.exists():
        print(f"⚠️  {data_path} not found — skipping companies_site rebuild.")
        return
    if not site_file.exists():
        print(f"⚠️  companies_site.html not found.")
        return

    current = json.loads(co_file.read_text(encoding="utf-8"))
    html    = site_file.read_text(encoding="utf-8")

    start_marker = "<script>window.__FITOUT_CO__ = "
    end_marker   = ";</script>"
    try:
        sp = html.index(start_marker)
        ep = html.index(end_marker, sp) + len(end_marker)
    except ValueError:
        print("⚠️  Could not find embedded companies data in companies_site.html")
        return

    payload = {
        "meta": {
            "last_updated":   current.get("last_updated", ""),
            "total_companies": current.get("total_companies", len(current.get("companies", []))),
            "notes": "Global fit-out company directory. Sources: company websites, industry reports, CN Specialists Index."
        },
        "companies": current.get("companies", [])
    }
    new_script = start_marker + json.dumps(payload, ensure_ascii=False) + end_marker
    new_html   = html[:sp] + new_script + html[ep:]
    site_file.write_text(new_html, encoding="utf-8")

    n   = payload["meta"]["total_companies"]
    sz  = site_file.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  companies_site.html — {n} companies, {now}, {sz:.0f} KB")


def _write_receipt(n: int, source: str, stamp: str):
    receipt = (
        f"FitOut Post — Build Receipt\n"
        f"===========================\n"
        f"Built    : {stamp}\n"
        f"Articles : {n}\n"
        f"Source   : {source}\n"
        f"Outputs  : news.html, site.html, alphaedge.html, betaedge.html\n\n"
        f"If news.html shows no articles, confirm you are opening\n"
        f"THIS folder's news.html (not a browser bookmark to an old copy).\n"
        f"\nDiagnostic: open check.html in the same folder first.\n"
        f"Admin (αEdge + βEdge): python admin.py\n"
    )
    (BASE / "BUILD_INFO.txt").write_text(receipt, encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--alphaedge" in args:
        build_alphaedge()
    elif "--betaedge" in args:
        build_betaedge()
    elif "--weekly" in args:
        build_weekly()
    elif "--gammaedge" in args:
        build_gammaedge()
    elif "--intelligence" in args:
        build_intelligence()
    elif "--tenders" in args:
        build_tenders()
    elif "--pipeline" in args:
        build_pipeline()
    elif "--awards" in args:
        build_awards()
    elif "--news" in args:
        build()
    else:
        build()
        build_alphaedge()
        build_betaedge()
        build_gammaedge()
        build_weekly()
        build_intelligence()
        build_tenders()
        build_pipeline()
        build_awards()
        build_companies_site()
        build_sitemap()
