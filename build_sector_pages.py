#!/usr/bin/env python3
"""
Build per-sector intelligence pages for FitOut Post.
Generates sectors/[slug].html for each major fit-out sector.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

BASE    = Path(__file__).parent
OUT_DIR = BASE / "sectors"
OUT_DIR.mkdir(exist_ok=True)

# ── Sector definitions ────────────────────────────────────────────────────────
SECTORS = [
    {
        "slug": "offices",
        "name": "Offices & Workplace",
        "icon": "🏢",
        "pipeline_key": "Offices & Workplace",
        "tender_cats": ["Office", "Commercial"],
        "news_keywords": ["office", "workplace", "workspace", "coworking", "co-working",
                          "headquarters", " hq ", "workplaces", "open plan", "fit-out"],
        "description": (
            "Office and workplace fit-out is one of the most active segments in the global "
            "interior construction market. From Category A shell-and-core works to full "
            "Category B tenant fit-out, this sector drives significant spend across "
            "corporate real estate, co-working operators and public sector occupiers."
        ),
        "meta": "Office and workplace fit-out news, pipeline projects, tenders and market intelligence worldwide.",
    },
    {
        "slug": "hospitality",
        "name": "Hospitality Fit-Out",
        "icon": "🏨",
        "pipeline_key": "Hospitality",
        "tender_cats": ["Hospitality"],
        "news_keywords": ["hotel", "hospitality", "resort", "restaurant", "bar", "cafe",
                          "spa", "leisure", "accommodation", "lodging"],
        "description": (
            "Hospitality fit-out encompasses hotels, resorts, restaurants, bars and "
            "serviced apartments. Operator-branded programmes, refurbishments and new-build "
            "FF&E packages make this one of the highest-value segments globally, "
            "concentrated in the Middle East, Asia Pacific and major gateway cities."
        ),
        "meta": "Hospitality fit-out news, hotel pipeline projects, tenders and market intelligence worldwide.",
    },
    {
        "slug": "retail",
        "name": "Retail & Commercial",
        "icon": "🛍️",
        "pipeline_key": "Retail & Mixed-Use",
        "tender_cats": ["Commercial"],
        "news_keywords": ["retail", "shop", "store", "mall", "shopping centre",
                          "shopping center", "boutique", "flagship", "shopfitting"],
        "description": (
            "Retail fit-out and shopfitting covers everything from luxury flagship stores "
            "to supermarket refits and mixed-use retail podiums. The sector has undergone "
            "significant transformation driven by experiential retail, pop-up formats and "
            "the integration of digital technology into physical environments."
        ),
        "meta": "Retail fit-out news, pipeline projects, shopfitting tenders and market intelligence worldwide.",
    },
    {
        "slug": "healthcare",
        "name": "Healthcare Fit-Out",
        "icon": "🏥",
        "pipeline_key": "Healthcare",
        "tender_cats": ["Healthcare"],
        "news_keywords": ["hospital", "clinic", "healthcare", "medical", "nhs",
                          "surgery", "diagnostic", "ward", "health centre", "health center"],
        "description": (
            "Healthcare fit-out is a technically demanding, heavily regulated sector "
            "covering hospitals, clinics, diagnostic centres and specialist care facilities. "
            "Infection control, medical gas pipework, cleanroom standards and compliance "
            "with HTM/HBN guidance make this a specialist area requiring accredited contractors."
        ),
        "meta": "Healthcare fit-out news, hospital pipeline projects, tenders and market intelligence worldwide.",
    },
    {
        "slug": "education",
        "name": "Education Fit-Out",
        "icon": "🎓",
        "pipeline_key": "Education",
        "tender_cats": ["Education"],
        "news_keywords": ["school", "university", "college", "campus", "education",
                          "academy", "library", "learning", "student"],
        "description": (
            "Education fit-out spans primary schools through to research universities "
            "and vocational training centres. Capital programmes, academy conversions, "
            "student accommodation and science laboratory fit-out are key sub-sectors, "
            "often procured through public frameworks in Europe and the Middle East."
        ),
        "meta": "Education fit-out news, university and school pipeline projects, tenders worldwide.",
    },
    {
        "slug": "cultural",
        "name": "Cultural & Museums",
        "icon": "🏛️",
        "pipeline_key": "Cultural & Museums",
        "tender_cats": ["Public"],
        "news_keywords": ["museum", "gallery", "cultural", "theatre", "theater",
                          "library", "heritage", "exhibition", "arts centre", "arts center"],
        "description": (
            "Cultural and museum fit-out requires specialist skills in exhibition design, "
            "display case manufacture, climate control, security integration and sensitive "
            "handling of heritage fabric. Public sector funding, lottery grants and "
            "philanthropic endowments drive major capital programmes in this sector."
        ),
        "meta": "Museum, gallery and cultural fit-out news, pipeline projects, tenders and intelligence.",
    },
    {
        "slug": "commercial",
        "name": "Commercial Development",
        "icon": "🏗️",
        "pipeline_key": "Commercial Development",
        "tender_cats": ["Commercial", "Industrial"],
        "news_keywords": ["commercial", "development", "mixed-use", "tower", "skyscraper",
                          "office tower", "business park", "grade a"],
        "description": (
            "Commercial development fit-out covers the interior works associated with "
            "large-scale office towers, mixed-use schemes and business parks. "
            "Shell-and-core delivery, landlord Cat A and tenant Cat B packages are "
            "all active procurement routes, often running concurrently on major schemes."
        ),
        "meta": "Commercial development fit-out news, pipeline projects, tenders and intelligence worldwide.",
    },
    {
        "slug": "transport",
        "name": "Infrastructure & Transport",
        "icon": "✈️",
        "pipeline_key": "Infrastructure & Transport",
        "tender_cats": ["Public", "Industrial"],
        "news_keywords": ["airport", "station", "transport", "transit", "terminal",
                          "metro", "rail", "port", "infrastructure"],
        "description": (
            "Transport and infrastructure fit-out encompasses airports, metro stations, "
            "rail terminals and port facilities. These are high-footfall, operationally "
            "complex environments requiring phased delivery around live operations, "
            "stringent fire and security standards and specialist wayfinding design."
        ),
        "meta": "Airport, transport and infrastructure fit-out news, pipeline projects, tenders worldwide.",
    },
    {
        "slug": "leisure",
        "name": "Sports & Leisure",
        "icon": "⚽",
        "pipeline_key": "Sports & Leisure",
        "tender_cats": ["Commercial"],
        "news_keywords": ["sport", "leisure", "gym", "stadium", "arena", "fitness",
                          "swimming", "athletic", "recreation", "wellness"],
        "description": (
            "Sports and leisure fit-out covers stadia, arenas, health clubs, gyms, "
            "swimming pools and recreational facilities. The sector benefits from "
            "growing investment in wellness infrastructure, premium fan experience "
            "upgrades and the global expansion of branded fitness operators."
        ),
        "meta": "Sports and leisure fit-out news, stadium pipeline projects, tenders and intelligence.",
    },
]


def esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def load_data():
    news     = json.loads((BASE / "news.json").read_text(encoding="utf-8"))["articles"]
    pipeline = json.loads((BASE / "pipeline.json").read_text(encoding="utf-8"))["projects"]
    tenders  = json.loads((BASE / "tenders.json").read_text(encoding="utf-8"))["tenders"]
    return news, pipeline, tenders


def match_news(sector, news):
    kws = sector["news_keywords"]
    out = []
    for a in news:
        text = f"{a.get('title', '')} {a.get('description', '')}".lower()
        if any(k in text for k in kws):
            out.append(a)
    return out


def match_pipeline(sector, pipeline):
    pk = sector["pipeline_key"].lower()
    return [p for p in pipeline if (p.get("sector") or "").lower() == pk]


def match_tenders(sector, tenders):
    cats = [c.lower() for c in sector["tender_cats"]]
    return [t for t in tenders if (t.get("category") or "").lower() in cats]


# ── Shared CSS (matches main site) ───────────────────────────────────────────
SHARED_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --salmon:      #FFF1E5;
    --salmon-dk:   #F2DFCE;
    --white:       #FFFFFF;
    --black:       #1a1a1a;
    --black-mid:   #262626;
    --claret:      #990033;
    --claret-lt:   #CC0044;
    --teal:        #0D7680;
    --amber:       #E8820C;
    --warm-gray:   #66605A;
    --mid-gray:    #9A948E;
    --card-bg:     #FFFFFF;
    --card-hover:  #FFF8F3;
    --border:      #D8C9A8;
    --border-dk:   #BBA898;
    --border-lt:   #EDE3DA;
    --serif:       'Playfair Display', 'EB Garamond', Georgia, serif;
    --serif-body:  'EB Garamond', Georgia, 'Times New Roman', serif;
    --sans:        Inter, system-ui, sans-serif;
  }
  html { scroll-behavior: smooth; font-size: 16px; }
  body { font-family: var(--sans); background: var(--salmon); color: var(--black);
         min-height: 100vh; -webkit-font-smoothing: antialiased; }
  a { color: inherit; text-decoration: none; }
  a:hover { color: var(--claret); }

  /* ── Utility bar ─────────────────────────────────────────────────── */
  #utility-bar { background: var(--black); color: #9A8A80; font-size: 11px;
    font-family: var(--sans); letter-spacing: .3px; border-bottom: 1px solid #333; padding: 0 24px; }
  #utility-inner { max-width: 1320px; margin: 0 auto; height: 34px;
    display: flex; align-items: center; justify-content: space-between; }
  #utility-left  { display: flex; align-items: center; gap: 20px; }
  #utility-right { display: flex; align-items: center; gap: 20px; }
  .util-link { color: #9A8A80; transition: color .15s; }
  .util-link:hover { color: #D4C4BA; }

  /* ── Masthead ────────────────────────────────────────────────────── */
  #masthead { background: var(--salmon); border-bottom: 2px solid var(--black);
    position: sticky; top: 0; z-index: 200; }
  #masthead-inner { max-width: 1320px; margin: 0 auto; padding: 0 24px;
    height: 72px; display: flex; align-items: center; gap: 24px; }
  #fop-logo { display: flex; align-items: center; gap: 14px; flex-shrink: 0; text-decoration: none; }
  #fop-logo:hover { color: inherit; }
  #fop-box { width: 52px; height: 52px; background: var(--black); display: flex;
    align-items: center; justify-content: center; flex-shrink: 0; }
  #fop-box span { font-family: var(--serif); font-weight: 800; font-size: 24px;
    letter-spacing: 1px; color: #fff; line-height: 1; }
  #fop-wordmark { display: flex; flex-direction: column; line-height: 1.2; }
  #fop-wordmark strong { font-family: var(--serif); font-weight: 700; font-size: 20px; color: var(--black); }
  #fop-wordmark em { font-style: normal; font-size: 10px; letter-spacing: 1.4px;
    text-transform: uppercase; color: var(--warm-gray); font-weight: 500; margin-top: 2px; }
  #masthead-right { margin-left: auto; display: flex; align-items: center; gap: 16px; flex-shrink: 0; }
  .masthead-nav-link { font-size: 12.5px; font-weight: 500; color: var(--black);
    padding: 6px 14px; border: 1px solid var(--border-dk);
    transition: background .15s, border-color .15s, color .15s; white-space: nowrap; font-family: var(--sans); }
  .masthead-nav-link:hover { background: var(--black); border-color: var(--black); color: #fff; }
  .masthead-nav-link--cta { background: var(--claret); border-color: var(--claret);
    color: #fff; font-weight: 600; padding: 6px 18px; }
  .masthead-nav-link--cta:hover { background: var(--claret-lt); border-color: var(--claret-lt); color: #fff; }

  /* ── Product nav ─────────────────────────────────────────────────── */
  #product-nav { background: var(--black); position: sticky; top: 72px; z-index: 195; }
  #product-nav-inner { max-width: 1320px; margin: 0 auto; padding: 0 24px; display: flex; gap: 0; overflow-x: auto; }
  .pnav-link { display: inline-block; padding: 0 16px; height: 38px; line-height: 38px;
    font-family: var(--sans); font-size: 12.5px; font-weight: 500;
    color: rgba(255,255,255,.65); letter-spacing: .3px;
    border-right: 1px solid rgba(255,255,255,.1);
    transition: color .15s, background .15s; white-space: nowrap; }
  .pnav-link:first-child { border-left: 1px solid rgba(255,255,255,.1); }
  .pnav-link:hover { color: #fff; background: rgba(255,255,255,.08); }
  .pnav-link.active { color: #fff; background: var(--claret); border-color: var(--claret); }

  /* ── Section header ──────────────────────────────────────────────── */
  .sec-header { background: var(--black); color: #fff; padding: 40px 0 32px; border-bottom: 1px solid #333; }
  .sec-header-inner { max-width: 1320px; margin: 0 auto; padding: 0 24px; }
  .sec-icon { font-size: 36px; display: block; margin-bottom: 10px; }
  .sec-title { font-family: var(--serif); font-size: 46px; font-weight: 700;
    line-height: 1.2; color: #fff; margin-bottom: 8px; }
  .sec-title span { color: var(--claret); }
  .sec-tagline { font-size: 14px; color: rgba(255,255,255,.55); max-width: 520px; line-height: 1.6; font-family: var(--sans); }
  .stats-row { display: flex; gap: 32px; flex-wrap: wrap; margin-top: 20px; }
  .stat { font-family: var(--sans); min-width: 60px; }
  .stat-val { font-size: 22px; font-weight: 700; color: #fff; display: block; }
  .stat-label { font-size: 10px; color: rgba(255,255,255,.4); text-transform: uppercase; letter-spacing: .1em; }

  /* ── Sector chips ────────────────────────────────────────────────── */
  #sector-nav { background: var(--card-bg); border-bottom: 1px solid var(--border); padding: 10px 0; }
  #sector-nav-inner { max-width: 1320px; margin: 0 auto; padding: 0 24px;
    display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .sector-chip { font-family: var(--sans); font-size: 11px; padding: 4px 12px;
    border: 1px solid var(--border); color: var(--warm-gray);
    transition: border-color .15s, color .15s; }
  .sector-chip:hover { border-color: var(--claret); color: var(--claret); }
  .sector-chip-label { font-family: var(--sans); font-size: 11px; font-weight: 600;
    color: var(--mid-gray); text-transform: uppercase; letter-spacing: .1em; margin-right: 4px; }

  /* ── Main content ────────────────────────────────────────────────── */
  #main { max-width: 1320px; margin: 0 auto; padding: 36px 24px 80px; }
  .description { font-family: var(--serif-body); font-size: 17px; line-height: 1.75;
    color: var(--black-mid); max-width: 740px; margin-bottom: 36px; }
  .back-link { font-family: var(--sans); font-size: 13px; color: var(--warm-gray);
    margin-bottom: 20px; display: inline-block; }
  .back-link:hover { color: var(--claret); }

  /* ── Section sub-headers ─────────────────────────────────────────── */
  .sub-header { display: flex; align-items: baseline; gap: 14px; margin: 40px 0 16px; padding-bottom: 10px;
    border-bottom: 2px solid var(--border); }
  .sub-header-title { font-family: var(--serif); font-size: 24px; font-weight: 700; color: var(--black); }
  .sub-header-count { font-family: var(--sans); font-size: 11px; font-weight: 600;
    color: var(--mid-gray); text-transform: uppercase; letter-spacing: .08em; }

  /* ── Article grid + cards (matches news.html) ────────────────────── */
  .articles-grid { display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 1px; background: var(--border); border: 1px solid var(--border); }
  .card { background: var(--card-bg); display: flex; flex-direction: column;
    padding: 20px 22px 18px; border-top: 3px solid var(--claret);
    transition: background .18s; position: relative; }
  .card:hover { background: var(--card-hover); }
  .card-top-row { display: flex; align-items: center; gap: 8px; margin-bottom: 9px; flex-wrap: wrap; }
  .card-category { font-size: 10px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; color: var(--claret); font-family: var(--sans); flex-shrink: 0; }
  .card-badge { font-size: 9px; font-weight: 700; letter-spacing: .8px;
    text-transform: uppercase; padding: 2px 7px; flex-shrink: 0; display: inline-block; }
  .card-badge.badge-pipeline { background: #0D7680; color: #fff; }
  .card-badge.badge-tender   { background: #1a1a1a; color: #fff; }
  .card-badge.badge-news     { background: var(--claret); color: #fff; }
  .card-flag { font-family: var(--sans); font-size: 11px; color: var(--warm-gray); }
  .card-val  { font-family: var(--sans); font-size: 11px; font-weight: 600; color: var(--teal); }
  .card-rel-time { font-size: 11px; color: var(--mid-gray); font-family: var(--sans);
    margin-left: auto; white-space: nowrap; flex-shrink: 0; }
  .card-title { font-family: var(--serif); font-size: 17px; font-weight: 700;
    line-height: 1.4; color: var(--black); margin-bottom: 10px;
    display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;
    transition: color .15s; }
  .card:hover .card-title { color: var(--claret); }
  .card-title a { color: inherit; }
  .card-title a:hover { color: var(--claret); }
  .card-desc { font-family: var(--serif-body); font-size: 15px; font-weight: 400;
    line-height: 1.55; color: var(--warm-gray);
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
    flex: 1; margin-bottom: 14px; }
  .card-footer { padding-top: 12px; border-top: 1px solid var(--border-lt); margin-top: auto; }
  .card-attribution { font-size: 11px; line-height: 1.7; color: var(--mid-gray); margin-bottom: 9px; font-family: var(--sans); }
  .card-attribution-row { display: flex; align-items: baseline; gap: 4px; flex-wrap: wrap; }
  .attr-label { font-weight: 600; color: #8a8078; font-size: 10px; letter-spacing: .5px;
    text-transform: uppercase; flex-shrink: 0; }
  .attr-source { font-weight: 600; color: var(--black); max-width: 200px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .attr-sep   { color: #ccc; padding: 0 2px; }
  .attr-date  { color: var(--mid-gray); }
  .card-footer-actions { display: flex; align-items: center; justify-content: flex-end; }
  .card-link { font-size: 11.5px; font-weight: 600; color: var(--claret);
    white-space: nowrap; flex-shrink: 0; letter-spacing: .1px; transition: color .15s; font-family: var(--sans); }
  .card-link:hover { color: var(--claret-lt); }
  .card-link::after { content: " ›"; }
  .premium-note { font-family: var(--sans); font-size: 11px; color: var(--amber); margin-top: 6px; }
  .no-data { font-family: var(--sans); font-size: 14px; color: var(--warm-gray);
    padding: 32px 0; font-style: italic; }
  .more-link { font-family: var(--sans); font-size: 13px; margin-top: 14px; display: block; }
  .more-link a { color: var(--claret); border-bottom: 1px solid currentColor; padding-bottom: 1px; }
  .more-link a:hover { color: var(--claret-lt); }

  /* ── Footer ──────────────────────────────────────────────────────── */
  #footer { background: var(--black); color: #A09890; margin-top: 80px; }
  #footer-main { max-width: 1320px; margin: 0 auto; padding: 48px 24px 40px;
    display: grid; grid-template-columns: 2fr 1.2fr; gap: 48px; border-bottom: 1px solid #2e2e2e; }
  #footer-brand .footer-logo-wrap { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
  #footer-fop-box { width: 40px; height: 40px; background: #fff; display: flex;
    align-items: center; justify-content: center; }
  #footer-fop-box span { font-family: var(--serif); font-weight: 800; font-size: 18px; color: var(--black); line-height: 1; }
  #footer-fop-wordmark { display: flex; flex-direction: column; }
  #footer-fop-name { font-family: var(--serif); font-weight: 700; font-size: 16px; color: #fff; }
  #footer-fop-tagline { font-size: 9px; letter-spacing: 1.2px; text-transform: uppercase; color: #7a706a; margin-top: 2px; }
  #footer-brand p { font-size: 12px; line-height: 1.6; color: #7a706a; margin-bottom: 10px; }
  .footer-disclaimer { font-size: 10px; line-height: 1.55; color: #5a5050; }
  #footer-ad-box { background: #1e1e1e; border: 1px solid #2e2e2e; padding: 24px; }
  #footer-ad-badge { font-size: 9px; letter-spacing: .12em; text-transform: uppercase; color: #5a5050; margin-bottom: 10px; }
  #footer-ad-headline { font-family: var(--serif); font-size: 17px; color: #D4C4BA; margin-bottom: 8px; line-height: 1.35; }
  #footer-ad-sub { font-size: 12px; color: #7a706a; margin-bottom: 14px; line-height: 1.5; }
  #footer-ad-cta { display: inline-block; font-size: 12px; color: var(--amber);
    border-bottom: 1px solid currentColor; padding-bottom: 1px; }
  #footer-bottom { max-width: 1320px; margin: 0 auto; padding: 18px 24px;
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
  #footer-copyright { font-size: 11.5px; color: #7a706a; }
  #footer-legal-links { display: flex; gap: 20px; }
  #footer-legal-links a { font-size: 11.5px; color: #7a706a; transition: color .15s; }
  #footer-legal-links a:hover { color: #9A8A80; }

  /* ── Dark mode ───────────────────────────────────────────────────── */
  @media (prefers-color-scheme: dark) {
    :root {
      --salmon:     #1e1912;
      --black:      #f0ede8;
      --black-mid:  #d8d2cc;
      --warm-gray:  #9a948e;
      --mid-gray:   #7a746e;
      --card-bg:    #2a2624;
      --card-hover: #332e2b;
      --border:     #3a3530;
      --border-dk:  #4a4540;
      --border-lt:  #302c28;
    }
    body { background: var(--salmon); }
    #utility-bar { background: #0d0b08; border-color: #1e1916; }
    #masthead { background: var(--salmon); border-color: #3a3530; }
    #fop-wordmark strong { color: var(--black); }
    #product-nav { background: #0d0b08; }
    .sec-header { background: #0d0b08; }
    #sector-nav { background: var(--card-bg); border-color: var(--border); }
    .sector-chip { color: var(--mid-gray); border-color: var(--border); }
    .card { background: var(--card-bg); }
    .card:hover { background: var(--card-hover); }
    .card-link { color: var(--claret-lt); }
  }

  /* ── Responsive ──────────────────────────────────────────────────── */
  @media (max-width: 960px) {
    .articles-grid { grid-template-columns: repeat(2, 1fr); }
    .sec-title { font-size: 34px; }
  }
  @media (max-width: 600px) {
    .articles-grid { grid-template-columns: 1fr; }
    .sec-title { font-size: 26px; }
    #utility-bar { display: none; }
    #footer-main { grid-template-columns: 1fr; gap: 24px; }
    #footer-bottom { flex-direction: column; align-items: flex-start; }
  }
"""

# ── Shared HTML fragments ─────────────────────────────────────────────────────
LINKEDIN_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#0A66C2"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'


def utility_bar(prefix="../"):
    return f"""<div id="utility-bar">
  <div id="utility-inner">
    <div id="utility-left"><span id="utility-date"></span></div>
    <div id="utility-right">
      <a class="util-link" href="mailto:hello@fitoutpost.com">Contact: hello@fitoutpost.com</a>
      <a class="util-link" href="{prefix}legal.html">Privacy</a>
      <a class="util-link" href="{prefix}advertise.html">Advertise</a>
    </div>
  </div>
</div>"""


def masthead(prefix="../"):
    return f"""<header id="masthead" role="banner">
  <div id="masthead-inner">
    <a href="{prefix}index.html" id="fop-logo">
      <div id="fop-box"><span>FO</span><span style="color:var(--claret)">P</span></div>
      <div id="fop-wordmark">
        <strong>Fit&nbsp;Out <span style="color:var(--claret)">Post</span></strong>
        <em>Global Industry Intelligence</em>
      </div>
    </a>
    <div id="masthead-right">
      <a class="masthead-nav-link masthead-nav-link--cta" href="{prefix}register.html">Register free →</a>
      <a href="https://www.linkedin.com/company/fitoutpost" target="_blank" rel="noopener" aria-label="FitOut Post on LinkedIn">
        {LINKEDIN_SVG}
      </a>
    </div>
  </div>
</header>"""


def product_nav(active_slug, prefix="../"):
    links = [
        ("Home",         f"{prefix}index.html"),
        ("News",         f"{prefix}news.html"),
        ("Roundup",      f"{prefix}weekly.html"),
        ("Tenders",      f"{prefix}tenders.html"),
        ("Pipeline",     f"{prefix}pipeline.html"),
        ("Awards",       f"{prefix}awards.html"),
        ("Intelligence", f"{prefix}intelligence.html"),
        ("Companies",    f"{prefix}companies_site.html"),
        ("Countries",    f"{prefix}countries/index.html"),
        ("Sectors",      f"{prefix}sectors/index.html"),
        ("Events",       f"{prefix}events.html"),
    ]
    items = "\n    ".join(
        f'<a class="pnav-link{" active" if label == active_slug else ""}" href="{href}">{label}</a>'
        for label, href in links
    )
    return f"""<nav id="product-nav" role="navigation" aria-label="Sections">
  <div id="product-nav-inner">
    {items}
  </div>
</nav>"""


def footer_html(prefix="../"):
    return f"""<footer id="footer" role="contentinfo">
  <div id="footer-main">
    <div id="footer-brand">
      <div class="footer-logo-wrap">
        <div id="footer-fop-box"><span>FO</span><span style="color:var(--claret)">P</span></div>
        <div id="footer-fop-wordmark">
          <div id="footer-fop-name">Fit&nbsp;Out <span style="color:var(--claret)">Post</span></div>
          <div id="footer-fop-tagline">Global Industry Intelligence</div>
        </div>
      </div>
      <p>An independent aggregator of global fit-out and interior construction news. Articles are drawn from industry publications, company announcements, and newswires across more than 50 countries. Updated daily.</p>
      <p class="footer-disclaimer">FitOut Post is not affiliated with any company featured in its coverage. Article links open the original source. Content is for reference only. This website is an independent news aggregator. Content is sourced from publicly available media and official announcements. The content published on this platform may be incomplete, inaccurate, or not fully representative of all relevant developments. We do not verify, endorse, or accept responsibility for the accuracy, completeness, or timeliness of any information presented. This site accepts no liability for any loss, damage, or inconvenience arising from reliance on its content.</p>
    </div>
    <div id="footer-ad-box">
      <div id="footer-ad-badge">Advertisement</div>
      <p id="footer-ad-headline">Your fit-out product or service here.</p>
      <p id="footer-ad-sub">Reach decision-makers tracking interior construction projects. Decision-makers, specifiers and contractors — every day.</p>
      <a href="mailto:hello@fitoutpost.com" id="footer-ad-cta">hello@fitoutpost.com</a>
    </div>
  </div>
  <div id="footer-bottom">
    <div id="footer-copyright">
      © <span id="footer-year"></span> FitOut Post. An independent publication. All rights reserved.
    </div>
    <div id="footer-legal-links">
      <a href="{prefix}legal.html#terms">Terms of use</a>
      <a href="{prefix}legal.html#privacy">Privacy policy</a>
      <a href="{prefix}legal.html#cookies">Cookie policy</a>
      <a href="mailto:hello@fitoutpost.com">Contact</a>
    </div>
  </div>
</footer>
<script>
  (function() {{
    var y = document.getElementById('footer-year');
    if (y) y.textContent = new Date().getFullYear();
    var d = document.getElementById('utility-date');
    if (d) d.textContent = new Date().toLocaleDateString('en-GB', {{weekday:'long',day:'numeric',month:'long',year:'numeric'}});
  }})();
</script>"""


# ── Card builders (matching news.html structure) ──────────────────────────────
def news_card(a):
    title  = esc(a.get("title", ""))
    url    = esc(a.get("url", "#"))
    src    = esc(a.get("source", ""))
    date   = esc((a.get("published", "") or "")[:10])
    ctry   = esc(a.get("country", ""))
    sig    = esc(a.get("signal_type", ""))
    desc   = esc((a.get("description", "") or "")[:200])
    badge  = f'<span class="card-badge badge-news">{sig}</span>' if sig and sig.lower() not in ("industry news", "") else ""
    flag   = f'<span class="card-flag">{ctry}</span>' if ctry else ""
    dtime  = f'<span class="card-rel-time">{date}</span>' if date else ""
    desc_h = f'<div class="card-desc">{desc}</div>' if desc else ""
    src_h  = (
        f'<div class="card-attribution"><div class="card-attribution-row">'
        f'<span class="attr-label">Via</span>'
        f'<span class="attr-source">{src}</span>'
        f'</div></div>'
    ) if src else ""
    return f'''<div class="card">
  <div class="card-top-row">{badge}{flag}{dtime}</div>
  <div class="card-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
  {desc_h}
  <div class="card-footer">
    {src_h}
    <div class="card-footer-actions">
      <a class="card-link" href="{url}" target="_blank" rel="noopener">Read more</a>
    </div>
  </div>
</div>'''


def pipe_card(p):
    title   = esc(p.get("title", ""))
    url     = esc(p.get("source_url", "#"))
    country = esc(p.get("country_name", ""))
    flag    = esc(p.get("country_flag", ""))
    date    = esc((p.get("published", "") or "")[:10])
    summary = esc((p.get("summary", "") or "")[:180])
    loc_str = f"{flag} {country}".strip()
    flag_h  = f'<span class="card-flag">{loc_str}</span>' if loc_str else ""
    dtime   = f'<span class="card-rel-time">{date}</span>' if date else ""
    desc_h  = f'<div class="card-desc">{summary}</div>' if summary else ""
    return f'''<div class="card" style="border-top-color:#0D7680;">
  <div class="card-top-row"><span class="card-badge badge-pipeline">Pipeline</span>{flag_h}{dtime}</div>
  <div class="card-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
  {desc_h}
  <div class="card-footer">
    <div class="card-footer-actions">
      <a class="card-link" href="{url}" target="_blank" rel="noopener">View signal</a>
    </div>
  </div>
</div>'''


def tender_card(t):
    title    = esc(t.get("title", ""))
    url      = esc(t.get("source_url", "#"))
    issuer   = esc(t.get("issuer", ""))
    flag     = esc(t.get("issuer_flag", ""))
    deadline = esc(t.get("deadline", ""))
    val      = esc(t.get("value_display", ""))
    is_prem  = t.get("is_premium", False)
    flag_h   = f'<span class="card-flag">{flag}</span>' if flag else ""
    val_h    = f'<span class="card-val">{val}</span>' if val else ""
    dl_h     = f'<span class="card-rel-time">Deadline: {deadline}</span>' if deadline else ""
    issuer_h = (
        f'<div class="card-attribution"><div class="card-attribution-row">'
        f'<span class="attr-label">Issuer</span>'
        f'<span class="attr-source">{issuer}</span>'
        f'</div></div>'
    ) if issuer else ""
    prem_h = '<div class="premium-note">🔒 Premium tender</div>' if is_prem else ""
    return f'''<div class="card" style="border-top-color:#1a1a1a;">
  <div class="card-top-row"><span class="card-badge badge-tender">Tender</span>{flag_h}{val_h}{dl_h}</div>
  <div class="card-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
  <div class="card-footer">
    {issuer_h}
    {prem_h}
    <div class="card-footer-actions">
      <a class="card-link" href="{url}" target="_blank" rel="noopener">View tender</a>
    </div>
  </div>
</div>'''


# ── Build a single sector page ────────────────────────────────────────────────
def build_page(sector, news, pipeline, tenders):
    slug = sector["slug"]
    name = sector["name"]
    icon = sector["icon"]
    desc = sector["description"]
    meta = sector["meta"]

    s_news    = match_news(sector, news)[:24]
    s_pipe    = match_pipeline(sector, pipeline)[:30]
    s_tenders = match_tenders(sector, tenders)[:20]

    # Schema
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "FitOut Post", "item": "https://fitoutpost.com/"},
            {"@type": "ListItem", "position": 2, "name": "Sectors", "item": "https://fitoutpost.com/sectors/index.html"},
            {"@type": "ListItem", "position": 3, "name": name, "item": f"https://fitoutpost.com/sectors/{slug}.html"},
        ]
    }
    ld_tags = f'<script type="application/ld+json">{json.dumps(breadcrumb_ld, ensure_ascii=False)}</script>'
    if s_pipe:
        item_list_ld = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"{name} Pipeline Projects",
            "numberOfItems": len(s_pipe),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": p.get("title", ""), "url": p.get("source_url", "")}
                for i, p in enumerate(s_pipe[:20])
            ]
        }
        ld_tags += f'\n  <script type="application/ld+json">{json.dumps(item_list_ld, ensure_ascii=False)}</script>'

    # Cards
    news_html    = "\n".join(news_card(a) for a in s_news)    or f'<div class="no-data">No recent {name.lower()} news matched.</div>'
    pipe_html    = "\n".join(pipe_card(p) for p in s_pipe)    or f'<div class="no-data">No pipeline signals found for this sector.</div>'
    tenders_html = "\n".join(tender_card(t) for t in s_tenders) or f'<div class="no-data">No active tenders found for this sector.</div>'

    # Sector chips
    other_chips = "\n    ".join(
        f'<a class="sector-chip" href="{s["slug"]}.html">{s["icon"]} {esc(s["name"])}</a>'
        for s in SECTORS if s["slug"] != slug
    )

    # Use articles-grid only if we have results; fallback to plain block for no-data
    news_grid    = f'<div class="articles-grid">{news_html}</div>'    if s_news    else news_html
    pipe_grid    = f'<div class="articles-grid">{pipe_html}</div>'    if s_pipe    else pipe_html
    tenders_grid = f'<div class="articles-grid">{tenders_html}</div>' if s_tenders else tenders_html

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(name)} — Fit-Out Intelligence | FitOut Post</title>
  <meta name="description" content="{esc(meta)}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="FitOut Post" />
  <meta property="og:title" content="{esc(name)} — Fit-Out Intelligence" />
  <meta property="og:description" content="{esc(meta)}" />
  <meta property="og:url" content="https://fitoutpost.com/sectors/{slug}.html" />
  <meta property="og:image" content="https://fitoutpost.com/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="canonical" href="https://fitoutpost.com/sectors/{slug}.html" />
  <link rel="icon" type="image/svg+xml" href="../favicon.svg" />
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-9ECWT6671C"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-9ECWT6671C',{{anonymize_ip:true}});</script>
  {ld_tags}
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=EB+Garamond:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
{SHARED_CSS}
  </style>
</head>
<body>
{utility_bar()}
{masthead()}
{product_nav("Sectors")}

<div class="sec-header">
  <div class="sec-header-inner">
    <span class="sec-icon">{icon}</span>
    <div class="sec-title">{esc(name)}</div>
    <div class="sec-tagline">Global fit-out news, pipeline projects and tenders</div>
    <div class="stats-row">
      <div class="stat"><span class="stat-val">{len(s_news)}</span><span class="stat-label">News</span></div>
      <div class="stat"><span class="stat-val">{len(s_pipe)}</span><span class="stat-label">Pipeline</span></div>
      <div class="stat"><span class="stat-val">{len(s_tenders)}</span><span class="stat-label">Tenders</span></div>
    </div>
  </div>
</div>

<div id="sector-nav">
  <div id="sector-nav-inner">
    <span class="sector-chip-label">Other sectors:</span>
    {other_chips}
  </div>
</div>

<div id="main">
  <a class="back-link" href="index.html">← All sectors</a>
  <p class="description">{esc(desc)}</p>

  <div class="sub-header">
    <span class="sub-header-title">Latest News</span>
    <span class="sub-header-count">{len(s_news)} articles</span>
  </div>
  {news_grid}
  <p class="more-link"><a href="../news.html">→ All fit-out industry news on FitOut Post</a></p>

  <div class="sub-header">
    <span class="sub-header-title">Pipeline Projects</span>
    <span class="sub-header-count">{len(s_pipe)} signals</span>
  </div>
  {pipe_grid}
  <p class="more-link"><a href="../pipeline.html">→ Full pipeline on FitOut Post</a></p>

  <div class="sub-header">
    <span class="sub-header-title">Active Tenders</span>
    <span class="sub-header-count">{len(s_tenders)} tenders</span>
  </div>
  {tenders_grid}
  <p class="more-link"><a href="../tenders.html">→ All tenders on FitOut Post</a></p>
</div>

{footer_html()}
<script src="../cookie-consent.js"></script>
<script src="../search.js"></script>
</body>
</html>"""

    out = OUT_DIR / f"{slug}.html"
    out.write_text(html, encoding="utf-8")
    return len(s_news) + len(s_pipe) + len(s_tenders)


# ── Build sector index page ───────────────────────────────────────────────────
def build_index():
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "FitOut Post", "item": "https://fitoutpost.com/"},
            {"@type": "ListItem", "position": 2, "name": "Sectors", "item": "https://fitoutpost.com/sectors/index.html"},
        ]
    }

    cards = "\n".join(
        f'''<a class="scard" href="{s["slug"]}.html">
          <span class="scard-icon">{s["icon"]}</span>
          <span class="scard-name">{esc(s["name"])}</span>
        </a>'''
        for s in SECTORS
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Fit-Out Sectors — FitOut Post</title>
  <meta name="description" content="Browse fit-out industry intelligence by sector: offices, hospitality, retail, healthcare, education, cultural and more." />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="FitOut Post" />
  <meta property="og:title" content="Fit-Out Sectors — FitOut Post" />
  <meta property="og:description" content="Browse fit-out industry intelligence by sector: offices, hospitality, retail, healthcare, education, cultural and more." />
  <meta property="og:url" content="https://fitoutpost.com/sectors/index.html" />
  <meta property="og:image" content="https://fitoutpost.com/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="canonical" href="https://fitoutpost.com/sectors/index.html" />
  <link rel="icon" type="image/svg+xml" href="../favicon.svg" />
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-9ECWT6671C"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-9ECWT6671C',{{anonymize_ip:true}});</script>
  <script type="application/ld+json">{json.dumps(breadcrumb_ld, ensure_ascii=False)}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=EB+Garamond:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
{SHARED_CSS}
  /* Sector index cards */
  .sectors-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1px;
    background: var(--border); border: 1px solid var(--border); }}
  .scard {{ display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px;
    padding: 36px 16px; background: var(--card-bg);
    border-top: 3px solid var(--claret);
    transition: background .15s, color .15s; text-align: center; }}
  .scard:hover {{ background: var(--card-hover); color: var(--claret); }}
  .scard-icon {{ font-size: 40px; line-height: 1; }}
  .scard-name {{ font-family: var(--serif); font-size: 17px; font-weight: 700; line-height: 1.3; color: var(--black); }}
  .scard:hover .scard-name {{ color: var(--claret); }}
  @media (prefers-color-scheme: dark) {{
    .scard {{ background: var(--card-bg); }}
    .scard:hover {{ background: var(--card-hover); }}
  }}
  </style>
</head>
<body>
{utility_bar()}
{masthead()}
{product_nav("Sectors")}

<div class="sec-header">
  <div class="sec-header-inner">
    <div class="sec-title">Sectors</div>
    <div class="sec-tagline">Browse fit-out industry intelligence by sector — news, pipeline and tenders.</div>
  </div>
</div>

<div id="main">
  <div class="sectors-grid">
{cards}
  </div>
</div>

{footer_html()}
<script src="../cookie-consent.js"></script>
<script src="../search.js"></script>
</body>
</html>"""

    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")


# ── Entry point ───────────────────────────────────────────────────────────────
def build():
    print("Loading data…")
    news, pipeline, tenders = load_data()
    print(f"  News: {len(news)}, Pipeline: {len(pipeline)}, Tenders: {len(tenders)}")

    build_index()
    print("  ✅  sectors/index.html")

    for sector in SECTORS:
        total = build_page(sector, news, pipeline, tenders)
        kb = (OUT_DIR / f"{sector['slug']}.html").stat().st_size // 1024
        print(f"  ✅  {sector['icon']} {sector['name']} — {total} signals, {kb} KB")

    print(f"\n✅  {len(SECTORS)} sector pages in: sectors/")


if __name__ == "__main__":
    build()
