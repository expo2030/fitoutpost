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

    # ── Performance: do NOT inline 5,000+ signals into the HTML ──────────────
    # The template already has a fetch("pipeline.json") fallback; use it.
    # We inject an empty <script> so the slot resolves but textContent is blank.
    empty_slot = f'<script type="application/json" id="{PL_SLOT_ID}"></script>'
    built = tmpl.replace(PL_DATA_SLOT, empty_slot, 1)
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
    built = inject_partials(built, "Awards", include_footer=False)
    built = _inject_site_updated(built, _compute_site_updated())
    AW_OUTPUT.write_text(built, encoding="utf-8")

    sz  = AW_OUTPUT.stat().st_size / 1024
    now = datetime.now(timezone.utc).strftime("Built %d %b %Y %H:%M UTC")
    print(f"✅  awards.html — {len(unique)} award signals, {now}, {sz:.0f} KB")


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
    "contact": {
        "output":     "contact.html",
        "title":      "Contact — FitOut Post",
        "active_nav": "",
        "meta": (
            '<meta name="description" content="Contact the FitOut Post team — editorial,'
            ' industry submissions, press, technical issues, and advertising enquiries." />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/contact.html" />'
        ),
        "extra_js": "",
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
(async function(){
  const fmt = n => n >= 1000 ? (n/1000).toFixed(1).replace(/\.0$/,'') + 'k' : String(n);
  try {
    const r = await fetch('news.json');
    const d = await r.json();
    if (d.total_articles) document.getElementById('ad-stat-news').textContent = fmt(d.total_articles) + '+';
  } catch(e) {}
})();
(function(){
  const form = document.getElementById('ad-form');
  if (!form) return;
  form.addEventListener('submit', function(e){
    e.preventDefault();
    const name = document.getElementById('ad-name').value.trim();
    const email = document.getElementById('ad-email').value.trim();
    if (!name || !email) return;
    const enq = { name, email, company: document.getElementById('ad-company').value.trim(), title: document.getElementById('ad-title').value.trim(), format: document.getElementById('ad-format').value, budget: document.getElementById('ad-budget').value, message: document.getElementById('ad-message').value.trim(), at: new Date().toISOString(), type: 'advertising' };
    try { const list = JSON.parse(localStorage.getItem('fop_ad_enquiries') || '[]'); list.push(enq); localStorage.setItem('fop_ad_enquiries', JSON.stringify(list)); } catch(e) {}
    document.getElementById('ad-confirm').classList.add('show');
    this.style.display = 'none';
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
    "events": {
        "output":     "events.html",
        "title":      "Fit-Out Industry Events 2025–2027 — FitOut Post",
        "active_nav": "Events",
        "meta": (
            '<meta name="description" content="Global calendar of fit-out and interior construction'
            ' industry events: trade shows, design weeks, conferences and summits — 2025 to 2027." />\n'
            '  <meta property="og:title" content="Fit-Out Industry Events — FitOut Post" />\n'
            '  <link rel="canonical" href="https://fitoutpost.com/events.html" />'
        ),
        "extra_js": r"""
// ── Event data ────────────────────────────────────────────────────────────────
const EVENTS = [
  // ── 2025 ──────────────────────────────────────────────────────────────────
  { name:"Orgatec 2026", type:"show", dates:"20–23 Oct 2026", iso:"2026-10-20",
    location:"Cologne, Germany", region:"Europe",
    desc:"The world's leading trade fair for modern working environments, office furniture and workplace design. Held biennially; 2026 edition expected 50,000+ visitors from 100+ countries.",
    url:"https://www.orgatec.com" },
  { name:"NeoCon 2025", type:"show", dates:"9–11 Jun 2025", iso:"2025-06-09",
    location:"Chicago, USA", region:"Americas",
    desc:"North America's largest commercial interiors trade show and conference. Merchandise Mart, Chicago. Covers workplace, hospitality, healthcare and retail interiors.",
    url:"https://neocon.com" },
  { name:"NeoCon 2026", type:"show", dates:"8–10 Jun 2026", iso:"2026-06-08",
    location:"Chicago, USA", region:"Americas",
    desc:"North America's largest commercial interiors trade show. 50,000+ attendees, 500+ exhibitors covering workplace, hospitality and healthcare fit-out.",
    url:"https://neocon.com" },
  { name:"Salone del Mobile 2025", type:"show", dates:"8–13 Apr 2025", iso:"2025-04-08",
    location:"Milan, Italy", region:"Europe",
    desc:"The world's premier furniture and design fair. Euroluce, SaloneSatellite and EuroCucina among the key features. A must-attend for interior design and fit-out specifiers.",
    url:"https://www.salonemilano.it" },
  { name:"Salone del Mobile 2026", type:"show", dates:"Apr 2026", iso:"2026-04-01",
    location:"Milan, Italy", region:"Europe",
    desc:"Annual international furniture and design exhibition. The most influential gathering of the global interior design community. 2026 dates TBC.",
    url:"https://www.salonemilano.it" },
  { name:"Clerkenwell Design Week 2025", type:"design", dates:"20–22 May 2025", iso:"2025-05-20",
    location:"London, United Kingdom", region:"Europe",
    desc:"Europe's largest design festival. Showrooms, studios, exhibitions and events across Clerkenwell — the highest concentration of creative businesses in the world.",
    url:"https://www.clerkenwelldesignweek.com" },
  { name:"Clerkenwell Design Week 2026", type:"design", dates:"May 2026", iso:"2026-05-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"Annual celebration of design in London's creative hub. Hundreds of showroom openings, installations and talks relevant to fit-out specifiers and designers.",
    url:"https://www.clerkenwelldesignweek.com" },
  { name:"INDEX Design 2025", type:"show", dates:"21–24 Oct 2025", iso:"2025-10-21",
    location:"Dubai, UAE", region:"Middle East",
    desc:"The Middle East's largest interiors, fit-out and design event. Covers commercial, hospitality and residential sectors. Dubai World Trade Centre.",
    url:"https://www.indexexhibition.com" },
  { name:"INDEX Design 2026", type:"show", dates:"Oct 2026", iso:"2026-10-01",
    location:"Dubai, UAE", region:"Middle East",
    desc:"Middle East's flagship interiors event. Essential for fit-out professionals active in the Gulf region.",
    url:"https://www.indexexhibition.com" },
  { name:"The Hotel Show Dubai 2025", type:"show", dates:"22–24 Sep 2025", iso:"2025-09-22",
    location:"Dubai, UAE", region:"Middle East",
    desc:"The MENA region's leading hospitality procurement and fit-out event. 350+ exhibitors covering FF&E, operating supplies and hotel construction.",
    url:"https://www.thehotelshow.com" },
  { name:"The Hotel Show Dubai 2026", type:"show", dates:"Sep 2026", iso:"2026-09-01",
    location:"Dubai, UAE", region:"Middle East",
    desc:"MENA's leading event for hotel fit-out, FF&E procurement and hospitality construction.",
    url:"https://www.thehotelshow.com" },
  { name:"Workspace Design Show 2026", type:"show", dates:"Feb 2026", iso:"2026-02-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"Dedicated exhibition for workplace design, office fit-out and workplace strategy professionals. Business Design Centre, London.",
    url:"https://www.workspaceshow.co.uk" },
  { name:"Workspace Design Show 2025", type:"show", dates:"25–26 Feb 2025", iso:"2025-02-25",
    location:"London, United Kingdom", region:"Europe",
    desc:"UK's dedicated workplace design and fit-out event. Business Design Centre, Islington. Covers Cat A, Cat B, design & build and workplace consultancy.",
    url:"https://www.workspaceshow.co.uk" },
  { name:"InterZUM 2025", type:"show", dates:"20–23 May 2025", iso:"2025-05-20",
    location:"Cologne, Germany", region:"Europe",
    desc:"Global trade fair for furniture production and interior construction. Suppliers of fittings, surfaces, materials and semi-finished products.",
    url:"https://www.interzum.com" },
  { name:"Cersaie 2025", type:"show", dates:"22–26 Sep 2025", iso:"2025-09-22",
    location:"Bologna, Italy", region:"Europe",
    desc:"International exhibition of ceramic tile and bathroom furnishings. Key sourcing event for fit-out material specifiers.",
    url:"https://www.cersaie.it" },
  { name:"BIEL Light + Building 2026", type:"show", dates:"Mar 2026", iso:"2026-03-01",
    location:"Frankfurt, Germany", region:"Europe",
    desc:"World's leading trade fair for lighting and building services technology. Essential for interior lighting specification in fit-out.",
    url:"https://light-building.messefrankfurt.com" },
  { name:"London Build 2025", type:"show", dates:"19–20 Nov 2025", iso:"2025-11-19",
    location:"London, United Kingdom", region:"Europe",
    desc:"The UK's largest construction and design show. Dedicated fit-out, interior design and workplace zones. ExCeL, London.",
    url:"https://www.londonbuildexpo.com" },
  { name:"London Build 2026", type:"show", dates:"Nov 2026", iso:"2026-11-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"UK's leading construction, design and fit-out event. 30,000+ attendees, 800+ exhibitors.",
    url:"https://www.londonbuildexpo.com" },
  { name:"DOMOTEX 2026", type:"show", dates:"Jan 2026", iso:"2026-01-10",
    location:"Hannover, Germany", region:"Europe",
    desc:"World's leading trade fair for floor coverings and installation technology. Critical specification event for floor finishes in commercial fit-out.",
    url:"https://www.domotex.de" },
  { name:"ISH 2025", type:"show", dates:"17–21 Mar 2025", iso:"2025-03-17",
    location:"Frankfurt, Germany", region:"Europe",
    desc:"World's leading trade fair for water, heat and air — HVAC systems essential to commercial fit-out MEP integration.",
    url:"https://www.ish.messefrankfurt.com" },
  { name:"BAU 2025", type:"show", dates:"13–17 Jan 2025", iso:"2025-01-13",
    location:"Munich, Germany", region:"Europe",
    desc:"World's leading trade fair for architecture, materials and systems. Key product sourcing event for commercial interior construction.",
    url:"https://www.bau-muenchen.com" },
  { name:"EXPOREAL 2025", type:"show", dates:"6–8 Oct 2025", iso:"2025-10-06",
    location:"Munich, Germany", region:"Europe",
    desc:"Europe's largest real estate investment and finance event. Substantial fit-out and tenant improvement discussions among property investors and developers.",
    url:"https://www.exporeal.net" },
  { name:"MIPIM 2026", type:"conf", dates:"10–13 Mar 2026", iso:"2026-03-10",
    location:"Cannes, France", region:"Europe",
    desc:"World's leading property market. 26,000+ participants, 100+ countries. Significant pipeline of fit-out projects discussed by developers and investors.",
    url:"https://www.mipim.com" },
  { name:"MIPIM 2025", type:"conf", dates:"11–14 Mar 2025", iso:"2025-03-11",
    location:"Cannes, France", region:"Europe",
    desc:"The world's leading property market event. Fit-out, office and retail development pipeline discussed by 26,000 investors and developers.",
    url:"https://www.mipim.com" },
  { name:"CITYSCAPE Global 2025", type:"show", dates:"7–9 Oct 2025", iso:"2025-10-07",
    location:"Riyadh, Saudi Arabia", region:"Middle East",
    desc:"The largest real estate event in the MENA region. Major fit-out demand signals from Vision 2030 projects.",
    url:"https://www.cityscapeglobal.com" },
  { name:"Big 5 Global 2025", type:"show", dates:"24–27 Nov 2025", iso:"2025-11-24",
    location:"Dubai, UAE", region:"Middle East",
    desc:"The Middle East's largest construction event. 60,000+ visitors, dedicated interiors and fit-out zones. Dubai World Trade Centre.",
    url:"https://www.thebig5.ae" },
  { name:"Big 5 Global 2026", type:"show", dates:"Nov 2026", iso:"2026-11-01",
    location:"Dubai, UAE", region:"Middle East",
    desc:"MENA's leading construction, interiors and fit-out trade event.",
    url:"https://www.thebig5.ae" },
  { name:"Designjunction 2025", type:"design", dates:"Nov 2025", iso:"2025-11-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"International showcase of contemporary design. Curated exhibition of brands and designers relevant to commercial interior specification.",
    url:"https://www.thedesignjunction.co.uk" },
  { name:"100% Design 2025", type:"show", dates:"Oct 2025", iso:"2025-10-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"UK's largest trade event for interior design. ExCeL London. Covers furniture, lighting, surfaces and spatial design.",
    url:"https://www.100percentdesign.co.uk" },
  { name:"Design Shanghai 2025", type:"show", dates:"Jun 2025", iso:"2025-06-01",
    location:"Shanghai, China", region:"Asia Pacific",
    desc:"China's most prestigious international design event. Covers architecture, interiors and design products relevant to Asia Pacific fit-out.",
    url:"https://www.designshanghai.com" },
  { name:"Design Shanghai 2026", type:"show", dates:"Jun 2026", iso:"2026-06-01",
    location:"Shanghai, China", region:"Asia Pacific",
    desc:"Leading international design event in China. Attended by developers, interior designers and fit-out contractors.",
    url:"https://www.designshanghai.com" },
  { name:"Architect@Work 2025 London", type:"show", dates:"5–6 Nov 2025", iso:"2025-11-05",
    location:"London, United Kingdom", region:"Europe",
    desc:"Invited architects and interior designers only. Curated product exhibition for commercial and residential interiors specification.",
    url:"https://www.architectatwork.co.uk" },
  { name:"Facilities Show 2025", type:"show", dates:"3–5 Jun 2025", iso:"2025-06-03",
    location:"Birmingham, United Kingdom", region:"Europe",
    desc:"UK's leading facilities management show. Covers workplace services, maintenance and post-occupancy aspects of commercial fit-out.",
    url:"https://www.facilitiesshow.com" },
  { name:"World of Concrete 2026", type:"show", dates:"Jan 2026", iso:"2026-01-20",
    location:"Las Vegas, USA", region:"Americas",
    desc:"North America's largest international event dedicated to the commercial concrete and masonry construction industries. Fit-out foundations and structural elements.",
    url:"https://www.worldofconcrete.com" },
  { name:"AIA Conference on Architecture 2025", type:"conf", dates:"5–7 Jun 2025", iso:"2025-06-05",
    location:"Boston, USA", region:"Americas",
    desc:"The American Institute of Architects annual conference. 15,000+ architects, designers and industry professionals. Interior design and commercial space sessions.",
    url:"https://aiaconference.com" },
  { name:"AIA Conference on Architecture 2026", type:"conf", dates:"Jun 2026", iso:"2026-06-01",
    location:"USA", region:"Americas",
    desc:"Annual gathering of the US architecture and design community. Covers commercial interiors, workplace design and building systems.",
    url:"https://aiaconference.com" },
  { name:"BDAV Annual Conference 2025", type:"conf", dates:"Nov 2025", iso:"2025-11-01",
    location:"Melbourne, Australia", region:"Oceania",
    desc:"Building Designers Association of Victoria. Interior design and commercial fit-out industry professionals.",
    url:"https://www.bdav.org.au" },
  { name:"Construct Australia 2025", type:"show", dates:"Oct 2025", iso:"2025-10-01",
    location:"Sydney, Australia", region:"Oceania",
    desc:"Australia's commercial construction and fit-out industry event. Contractors, developers and interior designers.",
    url:"https://constructaustralia.com.au" },
  { name:"FX International Interior Design Awards 2025", type:"awards", dates:"Nov 2025", iso:"2025-11-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"Prestigious annual awards recognising outstanding interior design and fit-out projects across commercial, hospitality and retail sectors.",
    url:"https://www.fxawards.com" },
  { name:"SBID International Design Awards 2025", type:"awards", dates:"Oct 2025", iso:"2025-10-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"Society of British and International Design annual awards. Commercial, hospitality and healthcare interior design categories.",
    url:"https://www.sbid.org/awards" },
  { name:"Contract Magazine Interior Design Excellence Awards 2025", type:"awards", dates:"Jun 2025", iso:"2025-06-01",
    location:"Chicago, USA", region:"Americas",
    desc:"IDEA Awards recognising the best commercial and institutional interior design in North America.",
    url:"https://www.contractdesign.com" },
  { name:"Hospitality Design Awards 2025", type:"awards", dates:"Jun 2025", iso:"2025-06-01",
    location:"Las Vegas, USA", region:"Americas",
    desc:"Celebrating the best in hotel design, FF&E specification and hospitality interior fit-out globally.",
    url:"https://www.hdexpo.com" },
  { name:"AHEAD Global 2025", type:"awards", dates:"Nov 2025", iso:"2025-11-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"Awards for Hospitality Experience and Design — recognising the best hotel and hospitality interior design worldwide.",
    url:"https://www.ahead.global" },
  { name:"Workspace Leaders Summit 2025", type:"summit", dates:"Sep 2025", iso:"2025-09-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"Senior workplace strategy, real estate and fit-out decision-makers. Future of work, hybrid office design and post-pandemic workplace planning.",
    url:"https://workspaceleaderssummit.com" },
  { name:"Corporate Real Estate Summit EMEA 2025", type:"summit", dates:"Oct 2025", iso:"2025-10-01",
    location:"Amsterdam, Netherlands", region:"Europe",
    desc:"Senior CRE executives discussing portfolio strategy, fit-out investment and workplace transformation across Europe.",
    url:"https://cresummit.com" },
  { name:"Global Workplace Summit 2025", type:"summit", dates:"2025", iso:"2025-06-01",
    location:"USA", region:"Americas",
    desc:"IFMA's flagship event for facility managers and corporate real estate professionals. Workplace transformation and fit-out strategy.",
    url:"https://www.ifma.org" },
  { name:"AHEAD Americas 2025", type:"awards", dates:"Jun 2025", iso:"2025-06-01",
    location:"New York, USA", region:"Americas",
    desc:"Awards for hospitality experience and design — North and South America. Hotel interior design and fit-out excellence.",
    url:"https://www.ahead.global/americas" },
  { name:"World Retail Congress 2025", type:"conf", dates:"Apr 2025", iso:"2025-04-01",
    location:"Barcelona, Spain", region:"Europe",
    desc:"World's leading retail industry conference. Store design, shopfitting and retail fit-out investment discussed by C-suite retail executives.",
    url:"https://www.worldretailcongress.com" },
  { name:"EuroCIS 2026", type:"show", dates:"Feb 2026", iso:"2026-02-17",
    location:"Düsseldorf, Germany", region:"Europe",
    desc:"Europe's leading retail technology trade fair. Digital signage, store systems and smart retail interior solutions.",
    url:"https://www.eurocis.com" },
  { name:"Intersec 2026", type:"show", dates:"Jan 2026", iso:"2026-01-20",
    location:"Dubai, UAE", region:"Middle East",
    desc:"World's leading trade fair for security, safety and fire protection — including building systems integration in fit-out projects.",
    url:"https://www.intersec.com" },
  { name:"Futurespace 2025", type:"conf", dates:"Nov 2025", iso:"2025-11-01",
    location:"Sydney, Australia", region:"Oceania",
    desc:"Australia's leading workplace strategy and office design conference. Fit-out contractors, designers and corporate occupiers.",
    url:"https://www.futurespace.com.au" },
  { name:"Healthcare Estates 2025", type:"conf", dates:"Oct 2025", iso:"2025-10-01",
    location:"Manchester, United Kingdom", region:"Europe",
    desc:"UK's leading event for healthcare estates, infrastructure and NHS fit-out. 2,000+ delegates, 200+ exhibitors.",
    url:"https://www.healthcareestates.co.uk" },
  { name:"Designregio Kortrijk 2025", type:"design", dates:"Oct 2025", iso:"2025-10-24",
    location:"Kortrijk, Belgium", region:"Europe",
    desc:"International furniture and interior design fair. Belgian design district event focused on commercial and contract interior products.",
    url:"https://www.designregio-kortrijk.be" },
  { name:"Stockholm Furniture Fair 2026", type:"show", dates:"3–7 Feb 2026", iso:"2026-02-03",
    location:"Stockholm, Sweden", region:"Europe",
    desc:"Scandinavia's largest design event. Nordic furniture and interiors — influential in sustainable commercial fit-out specification.",
    url:"https://www.stockholmfurniturefair.se" },
  { name:"Maison&Objet Paris 2026", type:"show", dates:"Jan 2026", iso:"2026-01-16",
    location:"Paris, France", region:"Europe",
    desc:"International reference for interior design, decoration and lifestyle. Covers hospitality, retail and contract markets.",
    url:"https://www.maison-objet.com" },
  { name:"IIDEX Canada 2025", type:"show", dates:"Nov 2025", iso:"2025-11-01",
    location:"Toronto, Canada", region:"Americas",
    desc:"Canada's largest interior design and facilities management expo. Office and commercial interiors focus.",
    url:"https://www.iidexcanada.com" },
  { name:"Retail Design Expo 2025", type:"show", dates:"Jun 2025", iso:"2025-06-01",
    location:"London, United Kingdom", region:"Europe",
    desc:"UK retail design, shopfitting and visual merchandising event. Covers in-store fit-out, fixtures and signage.",
    url:"https://www.retaildesignexpo.com" },
  // ── Asia Pacific additions ─────────────────────────────────────────────
  { name:"Japan Shop 2026", type:"show", dates:"5–8 Mar 2026", iso:"2026-03-05",
    location:"Tokyo, Japan", region:"Asia Pacific",
    desc:"Japan's largest commercial space design and shopfitting trade show. Tokyo Big Sight. Covers store fixtures, display systems, signage, retail interior design and commercial fit-out across Japan's leading retailers.",
    url:"https://www.japan-shop.jp/en/" },
  { name:"Japan Shop 2025", type:"show", dates:"Mar 2025", iso:"2025-03-01",
    location:"Tokyo, Japan", region:"Asia Pacific",
    desc:"Japan's premier commercial interior and retail fit-out trade show. Annually at Tokyo Big Sight, drawing 50,000+ retail and hospitality professionals.",
    url:"https://www.japan-shop.jp/en/" },
  { name:"Interior Lifestyle Tokyo 2025", type:"show", dates:"Jun 2025", iso:"2025-06-04",
    location:"Tokyo, Japan", region:"Asia Pacific",
    desc:"International trade fair for interior and lifestyle products. Tokyo Big Sight. Covers contract furniture, lighting and materials relevant to high-end commercial interior specification in Japan.",
    url:"https://www.interior-lifestyle.com" },
  { name:"Design Festa 2025", type:"design", dates:"Nov 2025", iso:"2025-11-01",
    location:"Tokyo, Japan", region:"Asia Pacific",
    desc:"Asia's largest art and design event. Tokyo Big Sight. Extensive commercial interior design and product innovation showcases relevant to fit-out specifiers.",
    url:"https://www.designfesta.com" },
  { name:"ArchXpo Singapore 2025", type:"show", dates:"Oct 2025", iso:"2025-10-01",
    location:"Singapore", region:"Asia Pacific",
    desc:"Singapore's key architecture, interior design and fit-out trade exhibition. Sands Expo and Convention Centre. Covers commercial, hospitality and retail fit-out across South East Asia.",
    url:"https://www.archxpo.com.sg" },
  { name:"Singapore International Furniture Fair 2026", type:"show", dates:"Mar 2026", iso:"2026-03-06",
    location:"Singapore", region:"Asia Pacific",
    desc:"Asia's premier contract furniture and commercial interior fair. Singapore Expo. Attended by hospitality and commercial fit-out specifiers from across South East Asia.",
    url:"https://www.siff.com.sg" },
  { name:"Domotex Asia/ChinaFloor 2025", type:"show", dates:"May 2025", iso:"2025-05-20",
    location:"Shanghai, China", region:"Asia Pacific",
    desc:"The world's largest floor covering trade event — Asia edition. Shanghai National Exhibition & Convention Center. Critical specification event for flooring in commercial fit-out projects across APAC.",
    url:"https://www.domotexasia.com" },
  { name:"Build & Interiors Australia 2025", type:"show", dates:"Jul 2025", iso:"2025-07-01",
    location:"Melbourne, Australia", region:"Oceania",
    desc:"Australia's dedicated commercial construction and interior fit-out event. Covers Cat A and Cat B office fit-out, retail shopfitting and hospitality design.",
    url:"https://www.buildinteriors.com.au" },
  { name:"Design Melbourne 2025", type:"design", dates:"Aug 2025", iso:"2025-08-21",
    location:"Melbourne, Australia", region:"Oceania",
    desc:"Melbourne's premier design festival. Commercial and residential interior design showcases, product launches and industry talks relevant to fit-out specifiers.",
    url:"https://designmelbourne.com.au" },
  { name:"DESIGNEX Australia 2025", type:"show", dates:"Jul 2025", iso:"2025-07-23",
    location:"Sydney, Australia", region:"Oceania",
    desc:"Australia and New Zealand's largest trade show for interior designers, architects and fit-out contractors. ICC Sydney. Covers commercial, hospitality and retail fit-out.",
    url:"https://www.designex.net.au" },
  { name:"HDC Workspace Korea 2025", type:"show", dates:"Sep 2025", iso:"2025-09-01",
    location:"Seoul, South Korea", region:"Asia Pacific",
    desc:"South Korea's leading workplace design and commercial interior trade event. COEX, Seoul. Covers office fit-out, furniture systems and workplace technology for the Korean market.",
    url:"https://www.hdcexpo.co.kr" },
  { name:"Architect@Work Tokyo 2025", type:"show", dates:"Oct 2025", iso:"2025-10-01",
    location:"Tokyo, Japan", region:"Asia Pacific",
    desc:"Invitation-only trade event for architects and interior designers. Curated product showcases for commercial interior specification in Japan.",
    url:"https://www.architectatwork.jp" },
  { name:"HOFEX Hong Kong 2025", type:"show", dates:"May 2025", iso:"2025-05-07",
    location:"Hong Kong", region:"Asia Pacific",
    desc:"Asia's premier food, hospitality and equipment trade exhibition. Significant hospitality fit-out and FF&E specification event for the Greater China and APAC region.",
    url:"https://www.hofex.com" },
  { name:"Thailand Build 2025", type:"show", dates:"Oct 2025", iso:"2025-10-01",
    location:"Bangkok, Thailand", region:"Asia Pacific",
    desc:"Thailand's leading construction and interior trade fair. IMPACT Exhibition Center, Bangkok. Covers commercial fit-out, interior materials and building systems for the Thai and ASEAN market.",
    url:"https://www.thailandbuild.com" },
  // ── Americas additions ─────────────────────────────────────────────────
  { name:"HD Expo + Conference 2025", type:"conf", dates:"7–9 May 2025", iso:"2025-05-07",
    location:"Las Vegas, USA", region:"Americas",
    desc:"The leading hospitality design conference and trade show. Mandalay Bay, Las Vegas. 500+ exhibitors covering hotel interiors, FF&E specification and hospitality fit-out. Attended by 12,000+ designers and developers.",
    url:"https://www.hdexpo.com" },
  { name:"HD Expo + Conference 2026", type:"conf", dates:"May 2026", iso:"2026-05-01",
    location:"Las Vegas, USA", region:"Americas",
    desc:"The industry's leading hospitality design event. Hotel, restaurant and resort interior design and fit-out across North America and globally.",
    url:"https://www.hdexpo.com" },
  { name:"Commercial Construction & Renovation Summit 2025", type:"summit", dates:"Nov 2025", iso:"2025-11-01",
    location:"Atlanta, USA", region:"Americas",
    desc:"Senior decision-makers in US commercial construction, tenant improvement and retail fit-out. Covers project pipeline, contractor selection and materials innovation.",
    url:"https://www.ccr-mag.com" },
  { name:"BISNOW National Office Summit 2025", type:"summit", dates:"Oct 2025", iso:"2025-10-01",
    location:"New York, USA", region:"Americas",
    desc:"Senior real estate leaders discussing office fit-out investment, tenant improvement allowances and workplace strategy in the post-pandemic US office market.",
    url:"https://www.bisnow.com" },
  { name:"Greenbuild 2025", type:"conf", dates:"Nov 2025", iso:"2025-11-01",
    location:"Philadelphia, USA", region:"Americas",
    desc:"The world's largest conference and expo dedicated to green building. USGBC event covering LEED-certified fit-out, sustainable materials and net-zero commercial interiors.",
    url:"https://www.greenbuildexpo.com" },
  { name:"Greenbuild 2026", type:"conf", dates:"Nov 2026", iso:"2026-11-01",
    location:"USA", region:"Americas",
    desc:"Global green building conference. Essential for fit-out teams targeting LEED certification and sustainable interior specification.",
    url:"https://www.greenbuildexpo.com" },
  { name:"ExpoRevestir 2026", type:"show", dates:"Mar 2026", iso:"2026-03-17",
    location:"São Paulo, Brazil", region:"Americas",
    desc:"Latin America's largest tile, stone and surfaces trade fair. São Paulo Expo. Key material specification event for commercial fit-out across Brazil and Latin America. 50,000+ visitors.",
    url:"https://www.exporevestir.com.br" },
  { name:"ExpoRevestir 2025", type:"show", dates:"Mar 2025", iso:"2025-03-18",
    location:"São Paulo, Brazil", region:"Americas",
    desc:"Brazil's premier surfaces and interior construction materials fair. Covers flooring, wall cladding and ceiling systems for commercial fit-out.",
    url:"https://www.exporevestir.com.br" },
  { name:"FIMMA Brasil 2025", type:"show", dates:"May 2025", iso:"2025-05-01",
    location:"Porto Alegre, Brazil", region:"Americas",
    desc:"International fair for the wood processing and furniture industry. Critical supplier event for joinery and millwork used in Brazilian commercial fit-out projects.",
    url:"https://www.fimma.com.br" },
  { name:"Expo CIHAC Mexico 2025", type:"show", dates:"Oct 2025", iso:"2025-10-01",
    location:"Mexico City, Mexico", region:"Americas",
    desc:"Mexico's most important construction, interiors and architectural products fair. Centro Citibanamex. Covers commercial fit-out materials, MEP systems and interior products for the Mexican market.",
    url:"https://www.expocihac.com" },
  { name:"Expo Muebles Mexico 2025", type:"show", dates:"Sep 2025", iso:"2025-09-01",
    location:"Guadalajara, Mexico", region:"Americas",
    desc:"Mexico's leading furniture and commercial interiors trade show. Expo Guadalajara. Covers contract furniture, workspace design and commercial interior fit-out for the Mexican and Latin American market.",
    url:"https://www.expomuebles.com.mx" },
  { name:"Buildex Vancouver 2026", type:"show", dates:"Feb 2026", iso:"2026-02-25",
    location:"Vancouver, Canada", region:"Americas",
    desc:"British Columbia's largest architecture, interior design and commercial construction event. Vancouver Convention Centre. Covers office fit-out, tenant improvement and sustainable commercial interiors for the Canadian West Coast.",
    url:"https://www.buildex.ca" },
  { name:"Buildex Toronto 2025", type:"show", dates:"Nov 2025", iso:"2025-11-01",
    location:"Toronto, Canada", region:"Americas",
    desc:"Canada's East Coast architecture and commercial construction event. Office fit-out, sustainable design and tenant improvement coverage.",
    url:"https://www.buildex.ca" },
  { name:"AHEAD Americas 2026", type:"awards", dates:"Jun 2026", iso:"2026-06-01",
    location:"New York, USA", region:"Americas",
    desc:"Awards for Hospitality Experience and Design — Americas. Recognises the best hotel interior design and hospitality fit-out projects across North and South America.",
    url:"https://www.ahead.global/americas" },
];

// ── Render logic ──────────────────────────────────────────────────────────────
let activeFilter = "all";
const today = new Date();
today.setHours(0,0,0,0);

function setFilter(f, btn) {
  activeFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderEvents();
}

function toggleYear(year) {
  const body = document.getElementById('body-' + year);
  const toggle = document.getElementById('toggle-' + year);
  const open = body.style.display !== 'none';
  body.style.display = open ? 'none' : '';
  toggle.textContent = open ? '▼ show' : '▲ hide';
}

function groupByYearMonth(evts) {
  const years = {};
  evts.forEach(e => {
    const d = new Date(e.iso);
    const year = d.getFullYear();
    const mKey = year + '-' + String(d.getMonth()+1).padStart(2,'0');
    const mLabel = d.toLocaleDateString('en-GB',{month:'long',year:'numeric'});
    if (!years[year]) years[year] = {};
    if (!years[year][mKey]) years[year][mKey] = {label:mLabel, events:[]};
    years[year][mKey].events.push(e);
  });
  return Object.entries(years)
    .sort((a,b) => b[0] - a[0])
    .map(([year, months]) => ({
      year,
      months: Object.entries(months).sort((a,b) => b[0].localeCompare(a[0]))
    }));
}

function badgeClass(type) {
  return {show:'badge-show',conf:'badge-conf',design:'badge-design',awards:'badge-awards',summit:'badge-summit'}[type]||'badge-show';
}
function badgeLabel(type) {
  return {show:'Trade show',conf:'Conference',design:'Design week',awards:'Awards',summit:'Summit'}[type]||type;
}

function renderEvents() {
  let filtered = EVENTS.filter(e => {
    if (activeFilter === 'upcoming') return new Date(e.iso) >= today;
    if (activeFilter === 'all') return true;
    return e.type === activeFilter;
  });

  filtered.sort((a,b) => b.iso.localeCompare(a.iso));

  const container = document.getElementById('events-wrap');
  const grouped = groupByYearMonth(filtered);
  let html = '';

  grouped.forEach(({year, months}) => {
    const collapsed = parseInt(year) < 2026;
    const count = months.reduce((s,[,{events}]) => s + events.length, 0);
    html += `<div class="year-section">`;
    html += `<div class="year-heading" onclick="toggleYear('${year}')">`;
    html += `<span class="year-label">${year}</span>`;
    html += `<span class="year-count">${count} events</span>`;
    html += `<span class="year-toggle" id="toggle-${year}">${collapsed ? '▼ show' : '▲ hide'}</span>`;
    html += `</div>`;
    html += `<div class="year-body" id="body-${year}"${collapsed ? ' style="display:none"' : ''}>`;

    months.forEach(([,{label, events}]) => {
      html += `<div class="month-group">`;
      html += `<h2 class="month-heading">${label}</h2>`;
      html += `<div class="events-grid">`;
      events.forEach(e => {
        const isPast = new Date(e.iso) < today;
        html += `<article class="event-card${isPast?' past':''}">`;
        html += `<div class="event-meta">`;
        html += `<span class="event-date">${e.dates}</span>`;
        html += `<span class="event-badge ${badgeClass(e.type)}">${badgeLabel(e.type)}</span>`;
        html += `</div>`;
        html += `<h3 class="event-name">${e.name}</h3>`;
        html += `<div class="event-location"><span>📍</span>${e.location}</div>`;
        html += `<p class="event-desc">${e.desc}</p>`;
        if (e.url) html += `<a class="event-link" href="${e.url}" target="_blank" rel="noopener">Official website →</a>`;
        html += `</article>`;
      });
      html += `</div></div>`;
    });

    html += `</div></div>`;
  });

  if (!html) html = `<p style="color:var(--warm-gray);padding:40px 0;">No events match this filter.</p>`;
  container.innerHTML = html;
}

renderEvents();
""",
    },
}


def build_static_pages() -> None:
    """Stamp _static_template.html with per-page content to build 8 static pages."""
    import re

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
        build_intelligence()
        build_tenders()
        build_pipeline()
        build_awards()
        build_companies_site()
        build_static_pages()
        build_sitemap()
