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

# ── Partials ──────────────────────────────────────────────────────────────────
PARTIALS_DIR = BASE / "_partials"
_PARTIALS: dict = {}

def _load_partials() -> None:
    """Load shared HTML partials from _partials/ directory."""
    for name in ("masthead", "nav", "footer"):
        path = PARTIALS_DIR / f"{name}.html"
        if path.exists():
            _PARTIALS[name] = path.read_text(encoding="utf-8")
        else:
            print(f"⚠  Partial not found: _partials/{name}.html")
            _PARTIALS[name] = f"<!-- PARTIAL:{name.upper()} MISSING -->"

_NAV_KEYS = ["Home", "News", "Roundup", "Tenders", "Pipeline",
             "Awards", "Intelligence", "Companies", "Countries", "Events"]

def inject_partials(html: str, active_nav: str = "", include_footer: bool = True) -> str:
    """Replace <!--PARTIAL:X--> slots with shared masthead, nav, and footer HTML."""
    html = html.replace("<!--PARTIAL:MASTHEAD-->", _PARTIALS.get("masthead", ""))
    # Nav — activate the matching link at build time
    nav = _PARTIALS.get("nav", "")
    for key in _NAV_KEYS:
        nav = nav.replace(f"<!--PNAV:{key}-->", " active" if key == active_nav else "")
    html = html.replace("<!--PARTIAL:NAV-->", nav)
    html = html.replace("<!--PARTIAL:FOOTER-->", _PARTIALS.get("footer", "") if include_footer else "")
    return html

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


def _compute_site_updated() -> str:
    """Return the most recent data date across all content JSON files (e.g. '7 May 2026')."""
    latest = None
    for fname, keys in [
        ("news.json",         ["last_updated", "generated"]),
        ("tenders.json",      ["last_updated", "generated"]),
        ("pipeline.json",     ["last_updated", "generated"]),
        ("intelligence.json", ["last_updated", "generated"]),
        ("weekly.json",       ["last_updated", "generated"]),
        ("alphaedge.json",    ["last_updated", "generated"]),
    ]:
        try:
            d = json.loads((BASE / fname).read_text(encoding="utf-8"))
            for key in keys:
                val = d.get(key)
                if not val and key == "generated" and isinstance(d.get("weeks"), list) and d["weeks"]:
                    val = d["weeks"][0].get("generated")
                if val:
                    val = val.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(val)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if latest is None or dt > latest:
                        latest = dt
                    break
        except Exception:
            pass
    if latest:
        return latest.strftime("%-d %B %Y")
    return datetime.now(timezone.utc).strftime("%-d %B %Y")


def _inject_site_updated(html: str, site_updated: str) -> str:
    """No-op — masthead-updated element removed; kept to avoid refactoring all call sites."""
    return html


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
    built = inject_partials(built, "News", include_footer=False)
    built = _inject_site_updated(built, _compute_site_updated())

    for out in NEWS_OUTPUTS:
        out.write_text(built, encoding="utf-8")
        sz = out.stat().st_size / 1024
        print(f"✅  {out.name} — {n} articles, {stamp_disp}, {sz:.0f} KB")

    _write_receipt(n, news_path, stamp_disp)
    print(f"✅  BUILD_INFO.txt written")
    print(f"\n    Open index.html in any browser — no server required.")


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
    built = inject_partials(built, "Intelligence", include_footer=False)
    built = _inject_site_updated(built, _compute_site_updated())
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
    built = inject_partials(built, "Roundup", include_footer=False)
    built = _inject_site_updated(built, _compute_site_updated())
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
    built = inject_partials(built, "Tenders", include_footer=False)
    built = _inject_site_updated(built, _compute_site_updated())
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

    # ── Do NOT embed the full 6k-project JSON inline (causes 4.5 MB HTML) ────
    # The template JS falls back to fetch("pipeline.json") when the inline slot
    # is empty — which is always the case on GitHub Pages (static file served
    # alongside pipeline.html). Replacing the slot with an empty script tag
    # keeps pipeline.html under 350 KB.
    built = tmpl.replace(
        PL_DATA_SLOT,
        f'<script type="application/json" id="{PL_SLOT_ID}"></script>',
    )
    built = inject_partials(built, "Pipeline", include_footer=False)
    built = _inject_site_updated(built, _compute_site_updated())
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

AW_DATA_FILE = BASE / "awards.json"

def build_awards(news_path: str = "news.json", pipeline_path: str = "pipeline.json") -> None:
    """Build awards.html from awards.json (persistent store) + new signals from news/pipeline.

    awards.json ACCUMULATES over time — awards are never deleted on rebuild.
    New signals found in news.json / pipeline.json are merged in by URL key.
    This ensures the page is never empty even if news data is sparse.
    """
    if not AW_TEMPLATE.exists():
        print(f"❌  Template {AW_TEMPLATE.name} not found.")
        return

    # ── 1. Load persistent awards store ──────────────────────────────────────
    if AW_DATA_FILE.exists():
        store = json.loads(AW_DATA_FILE.read_text(encoding="utf-8"))
        existing = store.get("awards", [])
    else:
        existing = []

    # Index existing awards by URL (primary) or id (fallback)
    seen_keys: set = set()
    for a in existing:
        key = a.get("url") or a.get("id")
        if key:
            seen_keys.add(key)

    new_candidates = []

    # ── 2. Extract candidates from news.json ──────────────────────────────────
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
                new_candidates.append({
                    "id":           a.get("id", ""),
                    "headline":     a.get("headline") or a.get("title", ""),
                    "url":          a.get("url", ""),
                    "source":       a.get("source", ""),
                    "pub_date":     a.get("pub_date") or a.get("published", ""),
                    "date_display": a.get("date_display") or a.get("published", ""),
                    "accessed_at":  a.get("accessed_at", ""),
                    "country":      a.get("country") or a.get("geo_country", ""),
                    "continent":    a.get("continent") or a.get("geo_continent", ""),
                    "sector":       a.get("sector", ""),
                    "signal_type":  "Award",
                    "_source":      "news",
                })

    # ── 3. Extract candidates from pipeline.json ──────────────────────────────
    pipeline_file = BASE / pipeline_path
    if pipeline_file.exists():
        pl = json.loads(pipeline_file.read_text(encoding="utf-8"))
        for a in pl.get("items", []):
            text = ((a.get("headline") or a.get("title") or "") + " " +
                    (a.get("description") or a.get("summary") or "")).lower()
            has_award_kw = any(kw in text for kw in AWARD_KEYWORDS)
            has_neg_kw   = any(kw in text for kw in AWARD_NEGATIVE_KEYWORDS)
            if has_award_kw and not has_neg_kw:
                new_candidates.append({
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

    # ── 4. Merge new candidates into persistent store ─────────────────────────
    added = 0
    for a in new_candidates:
        key = a.get("url") or a.get("id")
        if key and key not in seen_keys:
            seen_keys.add(key)
            existing.append(a)
            added += 1

    # ── 5. Sort by pub_date descending and write back awards.json ─────────────
    existing.sort(key=lambda x: x.get("pub_date", ""), reverse=True)

    store_out = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total": len(existing),
        "awards": existing,
    }
    AW_DATA_FILE.write_text(json.dumps(store_out, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    # ── 6. Build awards.html from the persistent store ────────────────────────
    data = {
        "total_awards": len(existing),
        "generated": datetime.now(timezone.utc).isoformat(),
        "awards": existing,
    }

    tmpl  = AW_TEMPLATE.read_text(encoding="utf-8")
    built = _embed_json(tmpl, data, AW_DATA_SLOT, AW_SLOT_ID)
    built = inject_partials(built, "Awards", include_footer=False)
    built = _inject_site_updated(built, _compute_site_updated())
    AW_OUTPUT.write_text(built, encoding="utf-8")

    sz  = AW_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  awards.html — {len(existing)} total awards ({added} new today), {now}, {sz:.0f} KB")


# ── Events build ─────────────────────────────────────────────────────────────
EV_TEMPLATE  = BASE / "_events_template.html"
EV_OUTPUT    = BASE / "events.html"
EV_DATA_FILE = BASE / "events.json"
EV_DATA_SLOT = "<!--EVENTS-DATA-SLOT-->"
EV_SLOT_ID   = "events-data"


def build_events(data_path: str = "events.json") -> None:
    """Build events.html from events.json + _events_template.html."""
    data_file = BASE / data_path

    if not EV_TEMPLATE.exists():
        print(f"❌  Template {EV_TEMPLATE.name} not found.")
        return

    if not data_file.exists():
        empty = {"last_updated": "", "total": 0, "events": []}
        data_file.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    data = json.loads(data_file.read_text(encoding="utf-8"))
    tmpl = EV_TEMPLATE.read_text(encoding="utf-8")
    n    = len(data.get("events", []))

    built = _embed_json(tmpl, data, EV_DATA_SLOT, EV_SLOT_ID)
    built = inject_partials(built, "Events", include_footer=False)
    EV_OUTPUT.write_text(built, encoding="utf-8")
    sz  = EV_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  events.html — {n} event(s), {now}, {sz:.0f} KB")


# ── Newsletter archive build ──────────────────────────────────────────────────
NL_TEMPLATE  = BASE / "_newsletter_template.html"
NL_OUTPUT    = BASE / "newsletter.html"
NL_DATA_FILE = BASE / "newsletter_archive.json"
NL_DATA_SLOT = "<!--NEWSLETTER-DATA-SLOT-->"
NL_SLOT_ID   = "newsletter-data"


def build_newsletter(data_path: str = "newsletter_archive.json") -> None:
    """Build newsletter.html from newsletter_archive.json + _newsletter_template.html."""
    data_file = BASE / data_path

    if not NL_TEMPLATE.exists():
        print(f"❌  Template {NL_TEMPLATE.name} not found.")
        return

    if not data_file.exists():
        empty = {"last_updated": "", "newsletters": []}
        data_file.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    data = json.loads(data_file.read_text(encoding="utf-8"))
    tmpl = NL_TEMPLATE.read_text(encoding="utf-8")
    n    = len(data.get("newsletters", []))

    built = _embed_json(tmpl, data, NL_DATA_SLOT, NL_SLOT_ID)
    built = inject_partials(built, "", include_footer=False)
    NL_OUTPUT.write_text(built, encoding="utf-8")
    sz  = NL_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  newsletter.html — {n} edition(s), {now}, {sz:.0f} KB")


# ── Static pages build ────────────────────────────────────────────────────────
STATIC_TEMPLATE  = BASE / "_static_template.html"
STATIC_PAGES_DIR = BASE / "_pages"

STATIC_PAGES = {
    "about": {
        "output":     "about.html",
        "title":      "About — FitOut Post",
        "active_nav": "About",
        "meta": (
            '<meta name="description" content="FitOut Post is an independent global aggregator'
            ' of fit-out and interior construction intelligence. Our mission, coverage, and data sources." />\n'
            '  <meta property="og:title" content="About — FitOut Post" />\n'
            '  <meta property="og:description" content="FitOut Post is an independent global aggregator'
            ' of fit-out and interior construction intelligence." />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/about.html" />'
        ),
        "extra_js": r"""
// Stats
(async function(){
  const fmt = n => n >= 1000 ? (n/1000).toFixed(1).replace(/\.0$/,'') + 'k' : String(n);
  const load = async (url) => { try { const r = await fetch(url); return r.ok ? r.json() : null; } catch(e) { return null; } };
  const [news, tenders, pipeline, companies] = await Promise.all([
    load('news.json'), load('tenders.json'), load('pipeline.json'), load('companies.json')
  ]);
  if (news && news.total_articles)       document.getElementById('ps-news').textContent     = fmt(news.total_articles);
  if (tenders && tenders.total_tenders)  document.getElementById('ps-tenders').textContent  = fmt(tenders.total_tenders);
  if (pipeline && pipeline.total_items)  document.getElementById('ps-pipeline').textContent = fmt(pipeline.total_items);
  if (companies && companies.companies)  document.getElementById('ps-companies').textContent = fmt(companies.companies.length);
})();
// Enquiry form
(function(){
  const form = document.getElementById('enquiry-form');
  if (!form) return;
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    const name  = document.getElementById('enq-name').value.trim();
    const email = document.getElementById('enq-email').value.trim();
    if (!name || !email) return;
    const enq = { name, email, company: document.getElementById('enq-company').value.trim(), interest: document.getElementById('enq-interest').value, message: document.getElementById('enq-message').value.trim(), at: new Date().toISOString() };
    try { const list = JSON.parse(localStorage.getItem('fop_ad_enquiries') || '[]'); list.push(enq); localStorage.setItem('fop_ad_enquiries', JSON.stringify(list)); } catch(e) {}
    document.getElementById('enq-confirm').classList.add('show');
    this.style.display = 'none';
  });
})();
""",
    },

    "legal": {
        "output":     "legal.html",
        "title":      "Legal — FitOut Post",
        "active_nav": "",
        "meta": (
            '<meta name="description" content="FitOut Post terms of use, privacy policy,'
            ' and cookie policy." />\n'
            '  <meta name="robots" content="noindex" />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/legal.html" />'
        ),
        "extra_js": "",
    },
    "advertise": {
        "output":     "advertise.html",
        "title":      "Advertise — FitOut Post",
        "active_nav": "Advertise",
        "meta": (
            '<meta name="description" content="Reach the global fit-out industry.'
            ' Advertising and sponsorship options on FitOut Post." />\n'
            '  <meta property="og:title" content="Advertise — FitOut Post" />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/advertise.html" />'
        ),
        "extra_js": r"""
// Show thank-you if redirected back after FormSubmit delivery
if (new URLSearchParams(location.search).get('sent') === '1') {
  const form = document.getElementById('ad-form');
  const confirm = document.getElementById('ad-confirm');
  if (form) form.style.display = 'none';
  if (confirm) confirm.classList.add('show');
}
// Client-side validation before FormSubmit POST
(function(){
  const form = document.getElementById('ad-form');
  if (!form) return;
  form.addEventListener('submit', function(e){
    const name = document.getElementById('ad-name').value.trim();
    const email = document.getElementById('ad-email').value.trim();
    const code = document.getElementById('ad-phone-code').value;
    const num = document.getElementById('ad-phone-num').value.trim();
    if (!name || !email || !code || !num) { e.preventDefault(); return; }
  });
})();
""",
    },
    "pricing": {
        "output":     "pricing.html",
        "title":      "Pricing — FitOut Post",
        "active_nav": "Pro ↑",
        "meta": (
            '<meta name="description" content="FitOut Post Free vs Pro. Full access'
            ' to global fit-out intelligence, tender alerts, pipeline data and API access." />\n'
            '  <meta property="og:title" content="Pricing — FitOut Post" />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/pricing.html" />'
        ),
        "extra_js": r"""
// Billing toggle
const toggle = document.getElementById('billing-toggle');
const priceEl = document.getElementById('pro-price');
const annualNote = document.getElementById('pro-annual-note');
const stripePriceDisplay = document.getElementById('stripe-price-display');
const planSelect = document.getElementById('ps-plan');
function updatePricing(annual) {
  if (annual) {
    priceEl.textContent = '€39';
    annualNote.textContent = '€470 billed annually — save €118';
    stripePriceDisplay.textContent = '€470/year';
    planSelect.value = 'annual';
  } else {
    priceEl.textContent = '€49';
    annualNote.textContent = '€588 billed monthly';
    stripePriceDisplay.textContent = '€49/month';
    planSelect.value = 'monthly';
  }
}
toggle.addEventListener('change', () => updatePricing(toggle.checked));
// FAQ accordion
function toggleFaq(btn) {
  const item = btn.closest('.faq-item');
  const isOpen = item.classList.contains('open');
  document.querySelectorAll('.faq-item.open').forEach(i => i.classList.remove('open'));
  if (!isOpen) item.classList.add('open');
}
// Pro signup form
function handleProSignup(e) {
  e.preventDefault();
  const member = {
    name: document.getElementById('ps-name').value.trim(),
    email: document.getElementById('ps-email').value.trim(),
    company: document.getElementById('ps-company').value.trim(),
    plan: document.getElementById('ps-plan').value,
    tier: 'pro',
    trialStart: new Date().toISOString(),
    id: 'pro_' + Date.now()
  };
  try {
    const existing = JSON.parse(localStorage.getItem('fop_members_list') || '[]');
    const idx = existing.findIndex(m => m.email === member.email);
    if (idx >= 0) { existing[idx] = { ...existing[idx], ...member }; }
    else { existing.push(member); }
    localStorage.setItem('fop_members_list', JSON.stringify(existing));
    localStorage.setItem('fop_member', JSON.stringify(member));
  } catch(err) {}
  document.getElementById('pro-signup-form').style.display = 'none';
  document.getElementById('stripe-success').style.display = 'block';
}
planSelect.addEventListener('change', () => {
  toggle.checked = planSelect.value === 'annual';
  updatePricing(toggle.checked);
});
""",
    },
    "register": {
        "output":     "register.html",
        "title":      "Register Free — FitOut Post",
        "active_nav": "Register Free",
        "meta": (
            '<meta name="description" content="Join FitOut Post free. Get daily fit-out news,'
            ' tender alerts, and pipeline intelligence from every continent." />\n'
            '  <meta property="og:title" content="Register Free — FitOut Post" />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/register.html" />'
        ),
        "extra_js": r"""
// Load stats
(async function() {
  const load = async (url) => { try { const r = await fetch(url); if (!r.ok) return null; return await r.json(); } catch(e) { return null; } };
  const fmt = n => n >= 1000 ? (n/1000).toFixed(1).replace(/\.0$/,'') + 'k' : String(n);
  const [news, tenders, pipeline] = await Promise.all([load('news.json'), load('tenders.json'), load('pipeline.json')]);
  if (news && news.total_articles) document.getElementById('stat-news').textContent = fmt(news.total_articles);
  if (tenders && tenders.total_tenders) document.getElementById('stat-tenders').textContent = fmt(tenders.total_tenders);
  if (pipeline && pipeline.total_items) document.getElementById('stat-pipeline').textContent = fmt(pipeline.total_items);
})();
// Member gate
(function() {
  const member = localStorage.getItem('fop_member');
  if (member) { try { const m = JSON.parse(member); showSuccess(m.email || ''); } catch(e) {} }
})();
// Login link
document.getElementById('login-link').addEventListener('click', function(e) {
  e.preventDefault();
  const member = localStorage.getItem('fop_member');
  if (member) { window.location.href = 'index.html'; }
  else { document.getElementById('email').focus(); document.getElementById('email').scrollIntoView({ behavior: 'smooth', block: 'center' }); }
});
// Form submit
document.getElementById('reg-form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  const errEl = document.getElementById('form-error');
  errEl.className = 'form-msg error'; errEl.textContent = '';
  const first = document.getElementById('first-name').value.trim();
  const last = document.getElementById('last-name').value.trim();
  const email = document.getElementById('email').value.trim().toLowerCase();
  const company = document.getElementById('company').value.trim();
  const role = document.getElementById('role').value;
  const region = document.getElementById('region').value;
  const gdpr = document.getElementById('gdpr-consent').checked;
  const interests = Array.from(document.querySelectorAll('.check-grid input[type="checkbox"]:checked')).map(cb => cb.value);
  if (!first || !last) return showError('Please enter your first and last name.');
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return showError('Please enter a valid email address.');
  if (!gdpr) return showError('Please accept the Privacy Policy and Terms of Use to continue.');
  btn.disabled = true; btn.textContent = 'Registering…';
  const member = { firstName: first, lastName: last, email, company, role, region, interests, registeredAt: new Date().toISOString(), id: 'fop_' + Date.now() };
  localStorage.setItem('fop_member', JSON.stringify(member));
  try { const list = JSON.parse(localStorage.getItem('fop_members_list') || '[]'); list.push(member); localStorage.setItem('fop_members_list', JSON.stringify(list)); } catch(e) {}
  setTimeout(() => showSuccess(email), 600);
  function showError(msg) { errEl.textContent = msg; errEl.className = 'form-msg error show'; btn.disabled = false; btn.textContent = 'Create free account →'; }
});
function showSuccess(email) {
  document.getElementById('form-panel').style.display = 'none';
  const panel = document.getElementById('success-panel');
  panel.classList.add('show');
  if (email) document.getElementById('success-email').textContent = email;
  renderAlerts();
}
// Keyword alert management
const FREE_LIMIT = 10;
function renderAlerts() {
  const member = JSON.parse(localStorage.getItem('fop_member') || '{}');
  const alerts = member.keyword_alerts || [];
  const container = document.getElementById('alerts-list');
  if (!container) return;
  container.innerHTML = alerts.length === 0 ? '<span style="font-size:13px;color:var(--mid-gray);font-style:italic;">No alerts saved yet.</span>' : alerts.map((kw, i) => `<span style="display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid var(--border-dk);padding:5px 12px;font-size:13px;font-weight:500;">${escH(kw)}<button onclick="removeAlert(${i})" style="background:none;border:none;cursor:pointer;color:var(--mid-gray);font-size:14px;padding:0 0 1px;line-height:1;" title="Remove">×</button></span>`).join('');
}
function escH(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function saveAlerts(alerts) {
  const member = JSON.parse(localStorage.getItem('fop_member') || '{}');
  member.keyword_alerts = alerts;
  localStorage.setItem('fop_member', JSON.stringify(member));
  try { const list = JSON.parse(localStorage.getItem('fop_members_list') || '[]'); const idx = list.findIndex(m => m.email === member.email); if (idx >= 0) list[idx] = member; else list.push(member); localStorage.setItem('fop_members_list', JSON.stringify(list)); } catch(e) {}
  const msg = document.getElementById('alerts-save-msg');
  if (msg) { msg.style.display = 'block'; setTimeout(() => msg.style.display = 'none', 2000); }
  renderAlerts();
}
function addAlert() {
  const input = document.getElementById('alert-input');
  const kw = (input.value || '').trim();
  if (!kw) return;
  const member = JSON.parse(localStorage.getItem('fop_member') || '{}');
  const alerts = member.keyword_alerts || [];
  if (alerts.includes(kw)) { input.value = ''; return; }
  if (alerts.length >= FREE_LIMIT) { alert('Free accounts can save up to ' + FREE_LIMIT + ' keyword alerts. Upgrade to Pro for unlimited.'); return; }
  alerts.push(kw); input.value = '';
  saveAlerts(alerts);
}
function removeAlert(index) {
  const member = JSON.parse(localStorage.getItem('fop_member') || '{}');
  const alerts = member.keyword_alerts || [];
  alerts.splice(index, 1);
  saveAlerts(alerts);
}
document.addEventListener('DOMContentLoaded', () => {
  const inp = document.getElementById('alert-input');
  if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); addAlert(); } });
});
if (document.getElementById('alerts-section')) renderAlerts();
""",
    },
    "api": {
        "output":     "api.html",
        "title":      "API Documentation — FitOut Post",
        "active_nav": "API",
        "meta": (
            '<meta name="description" content="FitOut Post REST API — read-only JSON endpoints'
            ' for Pro members. Access global fit-out news, tenders and pipeline data programmatically." />\n'
            '  <meta property="og:title" content="API Documentation — FitOut Post" />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/api.html" />'
        ),
        "extra_js": r"""
// Sidebar active link on scroll
const sections = document.querySelectorAll('.api-section');
const navLinks = document.querySelectorAll('.api-nav a');
window.addEventListener('scroll', () => {
  let current = '';
  sections.forEach(s => { if (window.scrollY >= s.offsetTop - 80) current = s.id; });
  navLinks.forEach(a => { a.classList.toggle('active', a.getAttribute('href') === '#' + current); });
});
// Copy code buttons
function copyCode(btn) {
  const block = btn.closest('.code-block');
  const text = block.innerText.replace(/^(JSON|Python|cURL|JavaScript|HTTP)\n/, '').replace(/^Copy\n/, '').trim();
  navigator.clipboard.writeText(text).then(() => { btn.textContent = 'Copied!'; setTimeout(() => btn.textContent = 'Copy', 1800); });
}
""",
    },
    "404": {
        "output":     "404.html",
        "title":      "404 — Page not found — FitOut Post",
        "active_nav": "",
        "meta": (
            '<meta name="robots" content="noindex" />'
        ),
        "extra_js": "",
    },
    "home": {
        "output":     "home.html",
        "title":      "FitOut Post — Global Fit-Out Industry Intelligence",
        "active_nav": "Home",
        "meta": (
            '<meta name="description" content="The global fit-out industry intelligence platform.'
            ' News, tenders, pipeline projects, contract awards, $/m² benchmarks and country intelligence — updated daily." />\n'
            '  <meta property="og:title" content="FitOut Post — Global Fit-Out Industry Intelligence" />\n'
            '  <meta property="og:description" content="The world\'s fit-out industry — all in one place.'
            ' News, tenders, pipeline, awards and country intelligence." />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/home.html" />'
        ),
        "extra_js": "",
    },
    "index": {
        "output":     "index.html",
        "title":      "FitOut Post — Global Fit-Out Industry Intelligence",
        "active_nav": "Home",
        "meta": (
            '<meta name="description" content="The global fit-out industry intelligence platform.'
            ' News, tenders, pipeline projects, contract awards, $/m² benchmarks and country intelligence — updated daily." />\n'
            '  <meta property="og:title" content="FitOut Post — Global Fit-Out Industry Intelligence" />\n'
            '  <meta property="og:description" content="The world\'s fit-out industry — all in one place.'
            ' News, tenders, pipeline, awards and country intelligence." />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/" />'
        ),
        "extra_js": "",
    },
}


def build_static_pages() -> None:
    """Stamp _static_template.html with per-page content to build 8 static pages."""
    import re

    if not _PARTIALS:
        _load_partials()

    if not STATIC_TEMPLATE.exists():
        print(f"❌  Static template {STATIC_TEMPLATE.name} not found.")
        return
    if not STATIC_PAGES_DIR.exists():
        print(f"❌  _pages/ directory not found.")
        return

    template = STATIC_TEMPLATE.read_text(encoding="utf-8")

    for key, cfg in STATIC_PAGES.items():
        frag_path = STATIC_PAGES_DIR / f"{key}.html"
        if not frag_path.exists():
            print(f"  ⚠  Fragment not found: _pages/{key}.html — skipping")
            continue

        frag = frag_path.read_text(encoding="utf-8")

        # Extract page-specific CSS from the <style>...</style> block at top of fragment
        css_match = re.search(r'<style>(.*?)</style>', frag, re.DOTALL)
        page_css = ""
        if css_match:
            page_css = f"<style>\n{css_match.group(1)}\n</style>"
            # Body is everything after the closing </style>
            body = frag[css_match.end():].strip()
        else:
            body = frag.strip()

        # Build the extra JS block
        extra_js = cfg.get("extra_js", "").strip()
        js_block  = f"<script>\n{extra_js}\n</script>" if extra_js else ""

        built = template
        built = built.replace("<!--STATIC-TITLE-->",      cfg["title"],      1)
        built = built.replace("<!--STATIC-META-->",        cfg["meta"],       1)
        built = built.replace("<!--STATIC-ACTIVE-NAV-->",  cfg["active_nav"], 1)
        built = built.replace("<!--STATIC-CSS-->",         page_css,          1)
        built = built.replace("<!--STATIC-BODY-->",        body,              1)
        built = built.replace("<!--STATIC-JS-->",          js_block,          1)
        show_footer = cfg["output"] in ("home.html", "index.html")
        built = inject_partials(built, cfg["active_nav"], include_footer=show_footer)

        out_path = BASE / cfg["output"]
        out_path.write_text(built, encoding="utf-8")
        sz = out_path.stat().st_size / 1024
        print(f"✅  {cfg['output']} — {sz:.0f} KB")

    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"    Static pages built ({now})")


def build_rss_feed(news_path: str = "news.json", output: str = "feed.xml") -> None:
    """Generate a valid RSS 2.0 feed from the top 50 articles in news.json."""
    import xml.sax.saxutils as saxutils

    data_file = BASE / news_path
    if not data_file.exists():
        print("⚠  feed.xml skipped — news.json not found")
        return

    data = json.loads(data_file.read_text(encoding="utf-8"))
    articles = data.get("articles", [])[:50]

    BASE_URL = "https://fitoutpost.com"
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    def rfc_date(iso: str) -> str:
        try:
            from email.utils import format_datetime
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return format_datetime(dt)
        except Exception:
            return now_rfc

    def esc(s: str) -> str:
        return saxutils.escape(str(s) if s else "")

    items = []
    for a in articles:
        title   = esc(a.get("title", ""))
        url     = esc(a.get("url", ""))
        source  = esc(a.get("source", ""))
        desc    = esc(a.get("description", "") or a.get("title", ""))
        pub     = rfc_date(a.get("published", ""))
        sig     = esc(a.get("signal_type", "Industry News"))
        country = esc(a.get("country", "") or a.get("continent", ""))
        guid    = esc(a.get("url", a.get("id", "")))
        cat_geo = f"<category>{country}</category>" if country and country != "Global" else ""
        items.append(f"""  <item>
    <title>{title}</title>
    <link>{url}</link>
    <description>{desc}</description>
    <pubDate>{pub}</pubDate>
    <source url="{url}">{source}</source>
    <category>{sig}</category>
    {cat_geo}
    <guid isPermaLink="true">{guid}</guid>
  </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>FitOut Post — Global Fit-Out Industry News</title>
  <link>{BASE_URL}</link>
  <description>Daily intelligence on fit-out, interior construction and workplace projects worldwide. Contract wins, project announcements, market data and company news.</description>
  <language>en</language>
  <lastBuildDate>{now_rfc}</lastBuildDate>
  <ttl>360</ttl>
  <image>
    <url>{BASE_URL}/og-image.png</url>
    <title>FitOut Post</title>
    <link>{BASE_URL}</link>
  </image>
  <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
</channel>
</rss>"""

    out_path = BASE / output
    out_path.write_text(rss, encoding="utf-8")
    sz = out_path.stat().st_size / 1024
    print(f"✅  feed.xml — {len(articles)} items, {sz:.0f} KB")


def build_sitemap() -> None:
    """Auto-generate sitemap.xml from all HTML pages in the site root and countries/."""
    BASE_URL = "https://fitoutpost.com"
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Priority / changefreq rules
    RULES = {
        "index.html":        ("1.0", "daily"),
        "news.html":         ("0.9", "daily"),
        "tenders.html":      ("0.9", "daily"),
        "pipeline.html":     ("0.9", "daily"),
        "events.html":       ("0.8", "monthly"),
        "companies_site.html": ("0.8", "weekly"),
        "intelligence.html": ("0.8", "weekly"),
        "weekly.html":       ("0.8", "weekly"),
        "awards.html":       ("0.7", "weekly"),
        "about.html":        ("0.5", "monthly"),

        "register.html":     ("0.5", "monthly"),
        "pricing.html":      ("0.5", "monthly"),
        "advertise.html":    ("0.4", "monthly"),
        "api.html":          ("0.4", "monthly"),
        "legal.html":        ("0.3", "yearly"),
    }

    urls = []

    # RSS feed
    urls.append((f"{BASE_URL}/feed.xml", today, "daily", "0.9"))

    # Root HTML pages (exclude private/build files)
    EXCLUDE = {"credentials.html", "site.html", "companies.html", "timeline.html",
               "alphaedge.html", "betaedge.html", "gammaedge.html"}
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
    """Rebuild companies_site.html from _companies_template.html + companies.json."""
    import re as _re
    co_file   = BASE / data_path
    tmpl_file = BASE / "_companies_template.html"
    site_file = BASE / "companies_site.html"

    if not co_file.exists():
        print(f"⚠️  {data_path} not found — skipping companies_site rebuild.")
        return
    if not tmpl_file.exists():
        print(f"⚠️  _companies_template.html not found.")
        return

    current = json.loads(co_file.read_text(encoding="utf-8"))
    html    = tmpl_file.read_text(encoding="utf-8")
    html    = inject_partials(html, "Companies", include_footer=False)

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
    _load_partials()
    args = sys.argv[1:]
    if "--weekly" in args:
        build_weekly()
    elif "--newsletter" in args:
        build_newsletter()
    elif "--events" in args:
        build_events()
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
    elif "--static" in args:
        build_static_pages()
    else:
        build()
        build_weekly()
        build_newsletter()
        build_events()
        build_intelligence()
        build_tenders()
        build_pipeline()
        build_awards()
        build_companies_site()
        build_static_pages()
        build_rss_feed()
        build_sitemap()
