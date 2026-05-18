#!/usr/bin/env python3
"""
Build per-sector intelligence pages for FitOut Post.
Generates sectors/[slug].html for each major fit-out sector.
"""
import json, re
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
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def load_data():
    news     = json.loads((BASE / "news.json").read_text(encoding="utf-8"))["articles"]
    pipeline = json.loads((BASE / "pipeline.json").read_text(encoding="utf-8"))["projects"]
    tenders  = json.loads((BASE / "tenders.json").read_text(encoding="utf-8"))["tenders"]
    return news, pipeline, tenders


def match_news(sector, news):
    kws = sector["news_keywords"]
    out = []
    for a in news:
        text = f"{a.get('title','')} {a.get('description','')}".lower()
        if any(k in text for k in kws):
            out.append(a)
    return out


def match_pipeline(sector, pipeline):
    pk = sector["pipeline_key"].lower()
    return [p for p in pipeline if (p.get("sector") or "").lower() == pk]


def match_tenders(sector, tenders):
    cats = [c.lower() for c in sector["tender_cats"]]
    return [t for t in tenders if (t.get("category") or "").lower() in cats]


def build_page(sector, news, pipeline, tenders):
    slug = sector["slug"]
    name = sector["name"]
    icon = sector["icon"]
    desc = sector["description"]
    meta = sector["meta"]

    s_news    = match_news(sector, news)[:24]
    s_pipe    = match_pipeline(sector, pipeline)[:30]
    s_tenders = match_tenders(sector, tenders)[:20]

    total = len(s_news) + len(s_pipe) + len(s_tenders)

    # ── Schema ───────────────────────────────────────────────────────────────
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type":"ListItem","position":1,"name":"FitOut Post","item":"https://fitoutpost.com/"},
            {"@type":"ListItem","position":2,"name":"Sectors","item":"https://fitoutpost.com/sectors/index.html"},
            {"@type":"ListItem","position":3,"name":name,"item":f"https://fitoutpost.com/sectors/{slug}.html"},
        ]
    }

    # Top pipeline items as ItemList
    item_list_ld = None
    if s_pipe:
        item_list_ld = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"{name} Pipeline Projects",
            "description": f"Fit-out pipeline projects in the {name.lower()} sector worldwide.",
            "numberOfItems": len(s_pipe),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": p.get("title",""),
                    "url": p.get("source_url",""),
                }
                for i, p in enumerate(s_pipe[:20])
            ]
        }

    # ── Cards ────────────────────────────────────────────────────────────────
    def news_card(a):
        title = esc(a.get("title",""))
        url   = esc(a.get("url","#"))
        src   = esc(a.get("source",""))
        date  = esc((a.get("published","") or "")[:10])
        country = esc(a.get("country",""))
        sig   = esc(a.get("signal_type",""))
        return f'''<div class="item-card">
          <div class="item-meta">{f'<span class="badge sig">{sig}</span>' if sig else ''}{f'<span class="item-flag">{country}</span>' if country else ''}{f'<span class="item-date">{date}</span>' if date else ''}</div>
          <div class="item-headline"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
          {f'<div class="item-source">{src}</div>' if src else ''}
        </div>'''

    def pipe_card(p):
        title   = esc(p.get("title",""))
        url     = esc(p.get("source_url","#"))
        country = esc(p.get("country_name",""))
        flag    = esc(p.get("country_flag",""))
        date    = esc((p.get("published","") or "")[:10])
        summary = esc((p.get("summary","") or "")[:120])
        return f'''<div class="item-card">
          <div class="item-meta"><span class="badge pipe">Pipeline</span>{f'<span class="item-flag">{flag} {country}</span>' if country else ''}{f'<span class="item-date">{date}</span>' if date else ''}</div>
          <div class="item-headline"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
          {f'<div class="item-summary">{summary}…</div>' if summary else ''}
        </div>'''

    def tender_card(t):
        title    = esc(t.get("title",""))
        url      = esc(t.get("source_url","#"))
        issuer   = esc(t.get("issuer",""))
        flag     = esc(t.get("issuer_flag",""))
        deadline = esc(t.get("deadline",""))
        val      = esc(t.get("value_display",""))
        is_prem  = t.get("is_premium", False)
        return f'''<div class="item-card">
          <div class="item-meta"><span class="badge tender">Tender</span>{f'<span class="item-flag">{flag}</span>' if flag else ''}{f'<span class="item-val">{val}</span>' if val else ''}{f'<span class="item-date">Deadline: {deadline}</span>' if deadline else ''}</div>
          <div class="item-headline"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
          {f'<div class="item-source">{issuer}</div>' if issuer else ''}
          {'<div class="premium-note">🔒 Premium tender</div>' if is_prem else ''}
        </div>'''

    news_html    = "\n".join(news_card(a) for a in s_news)   or '<div class="no-data">No recent news matched.</div>'
    pipe_html    = "\n".join(pipe_card(p) for p in s_pipe)   or '<div class="no-data">No pipeline signals found.</div>'
    tenders_html = "\n".join(tender_card(t) for t in s_tenders) or '<div class="no-data">No active tenders found.</div>'

    # ── Other sector nav ─────────────────────────────────────────────────────
    other_chips = "".join(
        f'<a class="sector-chip" href="{s["slug"]}.html">{s["icon"]} {esc(s["name"])}</a>'
        for s in SECTORS if s["slug"] != slug
    )

    ld_tags = f'<script type="application/ld+json">{json.dumps(breadcrumb_ld, ensure_ascii=False)}</script>\n'
    if item_list_ld:
        ld_tags += f'  <script type="application/ld+json">{json.dumps(item_list_ld, ensure_ascii=False)}</script>\n'

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
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
  :root{{
    --salmon:#FFF1E5;--salmon-dk:#F2DFCE;
    --white:#FFFFFF;--black:#1a1a1a;--black-mid:#262626;
    --claret:#990033;--claret-lt:#CC0044;--teal:#0D7680;--amber:#E8820C;
    --warm-gray:#66605A;--mid-gray:#9A948E;
    --border:#D8C9A8;--border-dk:#BBA898;
    --serif:'Playfair Display','EB Garamond',Georgia,serif;
    --garamond:'EB Garamond',Georgia,serif;
    --sans:Inter,system-ui,sans-serif;
  }}
  body{{background:var(--salmon);color:var(--black);font-family:var(--garamond);line-height:1.6;-webkit-font-smoothing:antialiased;}}
  a{{color:inherit;text-decoration:none;}}a:hover{{color:var(--claret);}}
  #masthead{{background:var(--salmon);border-bottom:2px solid var(--black);position:sticky;top:0;z-index:200;}}
  #masthead-inner{{max-width:1320px;margin:0 auto;padding:0 24px;height:72px;display:flex;align-items:center;gap:24px;}}
  #fop-logo{{display:flex;align-items:center;gap:14px;flex-shrink:0;text-decoration:none;}}
  #fop-logo:hover{{color:inherit;}}
  #fop-box{{width:52px;height:52px;background:var(--black);display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
  #fop-box span{{font-family:var(--serif);font-weight:800;font-size:24px;letter-spacing:1px;color:#fff;line-height:1;}}
  #fop-wordmark{{display:flex;flex-direction:column;line-height:1.2;}}
  #fop-wordmark strong{{font-family:var(--serif);font-weight:700;font-size:20px;color:var(--black);}}
  #fop-wordmark em{{font-style:normal;font-size:10px;letter-spacing:1.4px;text-transform:uppercase;color:var(--warm-gray);font-weight:500;margin-top:2px;}}
  #masthead-right{{margin-left:auto;display:flex;align-items:center;gap:16px;flex-shrink:0;}}
  .masthead-nav-link{{font-size:12.5px;font-weight:500;color:var(--black);padding:6px 14px;border:1px solid var(--border-dk);transition:background .15s,border-color .15s,color .15s;white-space:nowrap;}}
  .masthead-nav-link:hover{{background:var(--black);border-color:var(--black);color:#fff;}}
  .masthead-nav-link--cta{{background:var(--claret);border-color:var(--claret);color:#fff;font-weight:600;padding:6px 18px;}}
  .masthead-nav-link--cta:hover{{background:var(--claret-lt);border-color:var(--claret-lt);color:#fff;}}
  #product-nav{{background:var(--black);position:sticky;top:72px;z-index:195;}}
  #product-nav-inner{{max-width:1320px;margin:0 auto;padding:0 24px;display:flex;gap:0;}}
  .pnav-link{{display:inline-block;padding:0 20px;height:38px;line-height:38px;font-size:12.5px;font-weight:500;color:rgba(255,255,255,.65);letter-spacing:.3px;border-right:1px solid rgba(255,255,255,.1);transition:color .15s,background .15s;white-space:nowrap;}}
  .pnav-link:first-child{{border-left:1px solid rgba(255,255,255,.1);}}
  .pnav-link:hover{{color:#fff;background:rgba(255,255,255,.08);}}
  .pnav-link.active{{color:#fff;background:var(--claret);border-color:var(--claret);}}
  #hero{{background:var(--black);color:#fff;padding:36px 24px;}}
  #hero-inner{{max-width:1200px;margin:0 auto;}}
  .hero-eyebrow{{font-family:var(--sans);font-size:10px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--claret);margin-bottom:8px;}}
  .hero-icon{{font-size:48px;display:block;margin-bottom:12px;}}
  h1{{font-family:var(--serif);font-size:clamp(28px,4vw,44px);font-weight:800;line-height:1.1;margin-bottom:8px;}}
  .hero-sub{{font-family:var(--sans);font-size:13px;color:#B8A89A;}}
  .stats-row{{display:flex;gap:24px;flex-wrap:wrap;margin-top:20px;}}
  .stat{{font-family:var(--sans);text-align:center;min-width:80px;}}
  .stat-val{{font-size:24px;font-weight:700;color:#fff;display:block;}}
  .stat-label{{font-size:10px;color:#8a7f72;text-transform:uppercase;letter-spacing:.1em;}}
  #sector-nav{{background:#fff;border-bottom:1px solid var(--border);padding:10px 0;}}
  #sector-nav-inner{{max-width:1200px;margin:0 auto;padding:0 24px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;}}
  .sector-chip{{font-family:var(--sans);font-size:11px;padding:4px 12px;border:1px solid var(--border);border-radius:20px;color:#555;transition:all .15s;}}
  .sector-chip:hover{{border-color:var(--claret);color:var(--claret);}}
  #main{{max-width:1200px;margin:0 auto;padding:36px 24px 80px;}}
  .description{{font-size:16px;line-height:1.75;color:var(--black-mid);max-width:740px;margin-bottom:32px;}}
  .section-title{{font-family:var(--serif);font-size:20px;font-weight:700;border-bottom:2px solid var(--claret);padding-bottom:8px;margin:36px 0 16px;}}
  .items-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;}}
  .item-card{{background:#fff;border:1px solid var(--border);border-radius:2px;padding:14px 16px;border-left:3px solid var(--claret);}}
  .item-meta{{display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;}}
  .badge{{font-family:var(--sans);font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;border-radius:10px;}}
  .badge.sig{{background:#e8f0f8;color:#2a5f8f;}}
  .badge.pipe{{background:#fdf0e0;color:#8a4a00;}}
  .badge.tender{{background:#f3e8f3;color:#7a3f6e;}}
  .item-flag{{font-family:var(--sans);font-size:11px;color:var(--warm-gray);}}
  .item-date{{font-family:var(--sans);font-size:11px;color:var(--warm-gray);}}
  .item-val{{font-family:var(--sans);font-size:11px;font-weight:600;color:var(--teal);}}
  .item-headline{{font-family:var(--garamond);font-size:15px;line-height:1.35;}}
  .item-headline a{{color:var(--black);}}
  .item-headline a:hover{{color:var(--claret);}}
  .item-source{{font-family:var(--sans);font-size:11px;color:var(--warm-gray);margin-top:4px;}}
  .item-summary{{font-family:var(--sans);font-size:11px;color:var(--warm-gray);margin-top:6px;line-height:1.5;}}
  .premium-note{{font-family:var(--sans);font-size:11px;color:var(--amber);margin-top:4px;}}
  .no-data{{font-family:var(--sans);font-size:13px;color:var(--warm-gray);padding:20px 0;font-style:italic;}}
  .back-link{{font-family:var(--sans);font-size:13px;color:var(--warm-gray);margin-bottom:24px;display:inline-block;}}
  .back-link:hover{{color:var(--claret);}}
  @media(prefers-color-scheme:dark){{
    :root{{--salmon:#1e1912;--black:#f0ede8;--black-mid:#d8d2cc;--warm-gray:#9a948e;--border:#3a3530;--border-dk:#4a4540;}}
    body{{background:var(--salmon);color:var(--black);}}
    #hero{{background:#0d0b08;}}
    #sector-nav{{background:#252018;border-color:var(--border);}}
    .sector-chip{{color:#9a948e;border-color:var(--border);}}
    .item-card{{background:#252018;border-color:var(--border);}}
  }}
  </style>
</head>
<body>
<header id="masthead" role="banner">
  <div id="masthead-inner">
    <a href="../index.html" id="fop-logo">
      <div id="fop-box"><span>FO</span><span style="color:var(--claret)">P</span></div>
      <div id="fop-wordmark">
        <strong>Fit&nbsp;Out <span style="color:var(--claret)">Post</span></strong>
        <em>Global Industry Intelligence</em>
      </div>
    </a>
    <div id="masthead-right">
      <a class="masthead-nav-link masthead-nav-link--cta" href="../register.html">Register free →</a>
    </div>
  </div>
</header>

<nav id="product-nav" role="navigation" aria-label="Sections">
  <div id="product-nav-inner">
    <a class="pnav-link" href="../index.html">Home</a>
    <a class="pnav-link" href="../news.html">News</a>
    <a class="pnav-link" href="../tenders.html">Tenders</a>
    <a class="pnav-link" href="../pipeline.html">Pipeline</a>
    <a class="pnav-link" href="../intelligence.html">Intelligence</a>
    <a class="pnav-link" href="../companies_site.html">Companies</a>
    <a class="pnav-link" href="../countries/index.html">Countries</a>
    <a class="pnav-link active" href="index.html">Sectors</a>
  </div>
</nav>

<div id="hero">
  <div id="hero-inner">
    <div class="hero-eyebrow">Sector Intelligence</div>
    <span class="hero-icon">{icon}</span>
    <h1>{esc(name)}</h1>
    <div class="hero-sub">Global fit-out news, pipeline projects and tenders</div>
    <div class="stats-row">
      <div class="stat"><span class="stat-val">{len(s_news)}</span><span class="stat-label">News</span></div>
      <div class="stat"><span class="stat-val">{len(s_pipe)}</span><span class="stat-label">Pipeline</span></div>
      <div class="stat"><span class="stat-val">{len(s_tenders)}</span><span class="stat-label">Tenders</span></div>
    </div>
  </div>
</div>

<div id="sector-nav">
  <div id="sector-nav-inner">
    <span style="font-family:var(--sans);font-size:11px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.1em;margin-right:4px;">Other sectors:</span>
    {other_chips}
  </div>
</div>

<div id="main">
  <a class="back-link" href="index.html">← All sectors</a>

  <p class="description">{esc(desc)}</p>

  <div class="section-title">📰 Latest News</div>
  <div class="items-grid">{news_html}</div>
  <p style="font-family:var(--sans);font-size:13px;margin-top:16px;">
    <a href="../news.html" style="color:var(--claret);border-bottom:1px solid currentColor;padding-bottom:1px;">→ All fit-out industry news on FitOut Post</a>
  </p>

  <div class="section-title">🏗 Pipeline Projects</div>
  <div class="items-grid">{pipe_html}</div>
  <p style="font-family:var(--sans);font-size:13px;margin-top:16px;">
    <a href="../pipeline.html" style="color:var(--claret);border-bottom:1px solid currentColor;padding-bottom:1px;">→ Full pipeline on FitOut Post</a>
  </p>

  <div class="section-title">📋 Active Tenders</div>
  <div class="items-grid">{tenders_html}</div>
  <p style="font-family:var(--sans);font-size:13px;margin-top:16px;">
    <a href="../tenders.html" style="color:var(--claret);border-bottom:1px solid currentColor;padding-bottom:1px;">→ All tenders on FitOut Post</a>
  </p>
</div>

<script src="../cookie-consent.js"></script>
</body>
</html>"""

    out = OUT_DIR / f"{slug}.html"
    out.write_text(html, encoding="utf-8")
    return total


def build_index():
    """sectors/index.html — directory of all sector pages."""
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
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Fit-Out Sectors — FitOut Post</title>
  <meta name="description" content="Browse fit-out industry intelligence by sector: offices, hospitality, retail, healthcare, education, cultural and more."/>
  <link rel="canonical" href="https://fitoutpost.com/sectors/index.html"/>
  <link rel="icon" type="image/svg+xml" href="../favicon.svg"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=EB+Garamond:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
  <style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
  :root{{--salmon:#FFF1E5;--black:#1a1a1a;--claret:#990033;--border:#D8C9A8;--warm-gray:#66605A;
    --serif:'Playfair Display','EB Garamond',Georgia,serif;--sans:Inter,system-ui,sans-serif;}}
  body{{background:var(--salmon);color:var(--black);font-family:var(--sans);-webkit-font-smoothing:antialiased;}}
  a{{color:inherit;text-decoration:none;}}
  #masthead{{background:var(--salmon);border-bottom:2px solid var(--black);}}
  #masthead-inner{{max-width:1320px;margin:0 auto;padding:0 24px;height:72px;display:flex;align-items:center;}}
  #fop-box{{width:52px;height:52px;background:var(--black);display:flex;align-items:center;justify-content:center;}}
  #fop-box span{{font-family:var(--serif);font-weight:800;font-size:24px;color:#fff;}}
  #fop-wordmark{{margin-left:14px;}}
  #fop-wordmark strong{{font-family:var(--serif);font-weight:700;font-size:20px;}}
  #fop-wordmark em{{display:block;font-style:normal;font-size:10px;letter-spacing:1.4px;text-transform:uppercase;color:var(--warm-gray);}}
  #hero{{background:var(--black);color:#fff;padding:48px 24px;text-align:center;}}
  h1{{font-family:var(--serif);font-size:clamp(28px,4vw,48px);font-weight:800;margin-bottom:12px;}}
  .hero-sub{{font-size:14px;color:#B8A89A;}}
  #main{{max-width:1200px;margin:0 auto;padding:48px 24px 80px;}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px;}}
  .scard{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;
    padding:28px 16px;background:#fff;border:1px solid var(--border);border-radius:4px;
    transition:border-color .15s,box-shadow .15s;text-align:center;}}
  .scard:hover{{border-color:var(--claret);box-shadow:0 2px 12px rgba(153,0,51,.1);color:var(--claret);}}
  .scard-icon{{font-size:36px;}}
  .scard-name{{font-family:var(--serif);font-size:16px;font-weight:700;line-height:1.3;}}
  @media(prefers-color-scheme:dark){{
    :root{{--salmon:#1e1912;--black:#f0ede8;--border:#3a3530;}}
    .scard{{background:#252018;border-color:var(--border);}}
  }}
  </style>
</head>
<body>
<header id="masthead">
  <div id="masthead-inner">
    <a href="../index.html" style="display:flex;align-items:center;text-decoration:none;color:inherit;">
      <div id="fop-box"><span>FO</span><span style="color:var(--claret)">P</span></div>
      <div id="fop-wordmark">
        <strong>Fit&nbsp;Out <span style="color:var(--claret)">Post</span></strong>
        <em>Global Industry Intelligence</em>
      </div>
    </a>
  </div>
</header>
<div id="hero">
  <h1>Fit-Out Sectors</h1>
  <p class="hero-sub">Browse industry intelligence by sector — news, pipeline and tenders</p>
</div>
<div id="main">
  <div class="grid">{cards}</div>
</div>
<script src="../cookie-consent.js"></script>
</body>
</html>"""
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")


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
