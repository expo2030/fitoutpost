#!/usr/bin/env python3
"""
Build per-country dossier pages for FitOut Post.
Generates countries/XX.html for each target market combining news + pipeline + tenders.
"""
import json, re
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).parent
OUT_DIR = BASE / "countries"
OUT_DIR.mkdir(exist_ok=True)

# ── Target countries ─────────────────────────────────────────────────────────
COUNTRIES = [
    {"code": "ae",  "name": "United Arab Emirates", "flag": "🇦🇪", "continent": "Middle East"},
    {"code": "gb",  "name": "United Kingdom",        "flag": "🇬🇧", "continent": "Europe"},
    {"code": "us",  "name": "United States",         "flag": "🇺🇸", "continent": "Americas"},
    {"code": "de",  "name": "Germany",               "flag": "🇩🇪", "continent": "Europe"},
    {"code": "au",  "name": "Australia",             "flag": "🇦🇺", "continent": "Oceania"},
    {"code": "in",  "name": "India",                 "flag": "🇮🇳", "continent": "Asia Pacific"},
    {"code": "sg",  "name": "Singapore",             "flag": "🇸🇬", "continent": "Asia Pacific"},
    {"code": "fr",  "name": "France",                "flag": "🇫🇷", "continent": "Europe"},
    {"code": "es",  "name": "Spain",                 "flag": "🇪🇸", "continent": "Europe"},
    {"code": "sa",  "name": "Saudi Arabia",          "flag": "🇸🇦", "continent": "Middle East"},
    {"code": "nl",  "name": "Netherlands",           "flag": "🇳🇱", "continent": "Europe"},
    {"code": "hk",  "name": "Hong Kong",             "flag": "🇭🇰", "continent": "Asia Pacific"},
    {"code": "ie",  "name": "Ireland",               "flag": "🇮🇪", "continent": "Europe"},
    {"code": "qa",  "name": "Qatar",                 "flag": "🇶🇦", "continent": "Middle East"},
    {"code": "za",  "name": "South Africa",          "flag": "🇿🇦", "continent": "Africa"},
    {"code": "jp",  "name": "Japan",                 "flag": "🇯🇵", "continent": "Asia Pacific"},
    {"code": "br",  "name": "Brazil",                "flag": "🇧🇷", "continent": "Americas"},
    {"code": "mx",  "name": "Mexico",                "flag": "🇲🇽", "continent": "Americas"},
    {"code": "kr",  "name": "South Korea",           "flag": "🇰🇷", "continent": "Asia Pacific"},
    {"code": "th",  "name": "Thailand",              "flag": "🇹🇭", "continent": "Asia Pacific"},
    {"code": "ng",  "name": "Nigeria",               "flag": "🇳🇬", "continent": "Africa"},
    {"code": "ca",  "name": "Canada",                "flag": "🇨🇦", "continent": "Americas"},
    {"code": "it",  "name": "Italy",                 "flag": "🇮🇹", "continent": "Europe"},
]

def match_country(obj, country_name):
    """Check if an article/item belongs to the given country."""
    haystack = " ".join([
        obj.get("country",""), obj.get("geo_country",""),
        obj.get("headline",""), obj.get("title",""),
        obj.get("description",""), obj.get("summary",""),
    ]).lower()
    patterns = [country_name.lower()]
    # Add common alternates
    alternates = {
        "united arab emirates": ["uae", "dubai", "abu dhabi", "sharjah"],
        "united kingdom": ["uk", "england", "britain", "british", "london", "scotland", "wales"],
        "united states": ["usa", "u.s.", "american", "new york", "los angeles", "chicago", "san francisco"],
        "germany": ["german", "berlin", "munich", "frankfurt", "hamburg"],
        "australia": ["australian", "sydney", "melbourne", "brisbane"],
        "india": ["indian", "mumbai", "bangalore", "delhi", "chennai"],
        "singapore": ["singaporean"],
        "france": ["french", "paris", "lyon"],
        "spain": ["spanish", "madrid", "barcelona"],
        "saudi arabia": ["ksa", "riyadh", "jeddah"],
        "netherlands": ["dutch", "amsterdam"],
        "hong kong": ["hk"],
        "ireland": ["irish", "dublin"],
        "qatar": ["qatari", "doha"],
        "south africa": ["cape town", "johannesburg"],
        "japan": ["japanese", "tokyo", "osaka", "yokohama", "kyoto"],
        "brazil": ["brazilian", "são paulo", "sao paulo", "rio de janeiro", "brasilia"],
        "mexico": ["mexican", "ciudad de mexico", "mexico city", "guadalajara", "monterrey"],
        "south korea": ["korean", "seoul", "busan", "incheon"],
        "thailand": ["thai", "bangkok", "phuket", "chiang mai"],
        "nigeria": ["nigerian", "lagos", "abuja"],
        "canada": ["canadian", "toronto", "vancouver", "montreal", "calgary"],
        "italy": ["italian", "milan", "rome", "milano", "florence", "turin"],
    }
    patterns += alternates.get(country_name.lower(), [])
    return any(p in haystack for p in patterns)


def load_data():
    news, pipeline, tenders = [], [], []
    nf = BASE / "news.json"
    if nf.exists():
        d = json.loads(nf.read_text(encoding="utf-8"))
        news = d.get("articles", [])
    pf = BASE / "pipeline.json"
    if pf.exists():
        d = json.loads(pf.read_text(encoding="utf-8"))
        pipeline = d.get("items", [])
    tf = BASE / "tenders.json"
    if tf.exists():
        d = json.loads(tf.read_text(encoding="utf-8"))
        tenders = d.get("tenders", [])
    return news, pipeline, tenders


def esc_html(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def build_page(country, news, pipeline, tenders):
    cn = country["name"]
    cf = country["flag"]
    cc = country["code"]

    c_news     = [a for a in news     if match_country(a, cn)][:30]
    c_pipeline = [a for a in pipeline if match_country(a, cn)][:30]
    c_tenders  = [a for a in tenders  if match_country(a, cn)][:20]

    total = len(c_news) + len(c_pipeline) + len(c_tenders)

    def news_card(a):
        headline = esc_html(a.get("headline") or a.get("title",""))
        url = esc_html(a.get("url","#"))
        src = esc_html(a.get("source",""))
        date = esc_html(a.get("date_display") or a.get("pub_date",""))
        return f'''<div class="item-card">
          <div class="item-meta"><span class="badge news">News</span>{f'<span class="item-date">{date}</span>' if date else ''}</div>
          <div class="item-headline"><a href="{url}" target="_blank" rel="noopener">{headline}</a></div>
          {f'<div class="item-source">{src}</div>' if src else ''}
        </div>'''

    def pipe_card(a):
        headline = esc_html(a.get("headline") or a.get("title",""))
        url = esc_html(a.get("url","#"))
        sector = esc_html(a.get("sector",""))
        date = esc_html(a.get("date_display") or a.get("pub_date",""))
        return f'''<div class="item-card">
          <div class="item-meta"><span class="badge pipeline">Pipeline</span>{f'<span class="item-sector">{sector}</span>' if sector else ''}{f'<span class="item-date">{date}</span>' if date else ''}</div>
          <div class="item-headline"><a href="{url}" target="_blank" rel="noopener">{headline}</a></div>
        </div>'''

    def tender_card(a):
        title = esc_html(a.get("title") or a.get("headline",""))
        url = esc_html(a.get("url","#"))
        deadline = esc_html(a.get("deadline",""))
        return f'''<div class="item-card">
          <div class="item-meta"><span class="badge tender">Tender</span>{f'<span class="item-date">Deadline: {deadline}</span>' if deadline else ''}</div>
          <div class="item-headline"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
        </div>'''

    news_html     = "\n".join(news_card(a)    for a in c_news)     or '<div class="no-data">No recent news found.</div>'
    pipeline_html = "\n".join(pipe_card(a)    for a in c_pipeline) or '<div class="no-data">No pipeline signals found.</div>'
    tenders_html  = "\n".join(tender_card(a)  for a in c_tenders)  or '<div class="no-data">No active tenders found.</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{cn} Fit-Out Intelligence — FitOut Post</title>
  <meta name="description" content="Fit-out industry intelligence for {cn}: news, pipeline projects and live tenders. Updated daily by FitOut Post." />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="FitOut Post" />
  <meta property="og:title" content="{cn} Fit-Out Intelligence — FitOut Post" />
  <meta property="og:description" content="News, pipeline projects and tenders for the {cn} fit-out market." />
  <meta property="og:url" content="https://fitoutpost.com/countries/{cc}.html" />
  <meta property="og:image" content="https://fitoutpost.com/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="canonical" href="https://fitoutpost.com/countries/{cc}.html" />
  <link rel="icon" type="image/svg+xml" href="../favicon.svg" />
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-9ECWT6671C"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-9ECWT6671C',{{anonymize_ip:true}});</script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=EB+Garamond:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
  :root{{--salmon:#FFF1E5;--black:#1a1a1a;--claret:#990033;--warm-gray:#8a7f72;--rule:#D8C9A8;
        --serif:'Playfair Display',Georgia,serif;--garamond:'EB Garamond',Georgia,serif;--sans:Inter,system-ui,sans-serif;}}
  body{{background:var(--salmon);color:var(--black);font-family:var(--garamond);line-height:1.6;}}
  a{{color:inherit;text-decoration:none;}}a:hover{{color:var(--claret);}}
  #masthead{{background:var(--black);border-bottom:3px solid var(--claret);}}
  #masthead-inner{{max-width:1200px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;min-height:52px;}}
  #masthead-logo{{font-family:var(--serif);font-size:22px;font-weight:800;color:#fff;text-decoration:none;}}
  #masthead-logo span{{color:var(--claret);}}
  .mh-link{{color:#c8beb2;font-family:var(--sans);font-size:12px;font-weight:500;letter-spacing:.5px;text-transform:uppercase;padding:14px 12px;display:inline-block;}}
  .mh-link:hover{{color:#fff;}}
  #hero{{background:var(--black);color:#fff;padding:32px 24px;}}
  #hero-inner{{max-width:1200px;margin:0 auto;}}
  .hero-flag{{font-size:48px;margin-bottom:12px;display:block;}}
  .hero-eyebrow{{font-family:var(--sans);font-size:10px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--claret);margin-bottom:8px;}}
  h1{{font-family:var(--serif);font-size:clamp(28px,4vw,44px);font-weight:800;line-height:1.1;margin-bottom:8px;}}
  .hero-sub{{font-family:var(--sans);font-size:13px;color:#B8A89A;}}
  .stats-row{{display:flex;gap:24px;margin-top:16px;}}
  .stat{{font-family:var(--sans);text-align:center;}}
  .stat-val{{font-size:24px;font-weight:700;color:#fff;display:block;}}
  .stat-label{{font-size:10px;color:#8a7f72;text-transform:uppercase;letter-spacing:.1em;}}
  #main{{max-width:1200px;margin:0 auto;padding:32px 24px 80px;}}
  .section-title{{font-family:var(--serif);font-size:22px;font-weight:700;border-bottom:2px solid var(--claret);padding-bottom:8px;margin:32px 0 16px;}}
  .items-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;}}
  .item-card{{background:#fff;border:1px solid var(--rule);border-radius:2px;padding:14px 16px;border-left:3px solid var(--claret);}}
  .item-meta{{display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;}}
  .badge{{font-family:var(--sans);font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;border-radius:10px;}}
  .badge.news{{background:#e8f0f8;color:#2a5f8f;}}
  .badge.pipeline{{background:#fdf0e0;color:#8a4a00;}}
  .badge.tender{{background:#f3e8f3;color:#7a3f6e;}}
  .item-date,.item-sector{{font-family:var(--sans);font-size:11px;color:var(--warm-gray);}}
  .item-headline{{font-family:var(--garamond);font-size:15px;line-height:1.35;}}
  .item-headline a{{color:var(--black);}}
  .item-headline a:hover{{color:var(--claret);}}
  .item-source{{font-family:var(--sans);font-size:11px;color:var(--warm-gray);margin-top:4px;}}
  .no-data{{font-family:var(--sans);font-size:13px;color:var(--warm-gray);padding:20px 0;font-style:italic;}}
  .country-nav{{background:#fff;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:12px 0;margin-bottom:0;}}
  .country-nav-inner{{max-width:1200px;margin:0 auto;padding:0 24px;display:flex;flex-wrap:wrap;gap:8px;}}
  .country-chip{{font-family:var(--sans);font-size:11px;padding:4px 12px;border:1px solid var(--rule);border-radius:20px;color:#555;transition:all .15s;}}
  .country-chip:hover{{border-color:var(--claret);color:var(--claret);}}
  #footer{{background:var(--black);color:#8a7f72;font-family:var(--sans);font-size:12px;padding:24px;text-align:center;border-top:2px solid var(--claret);}}
  #footer a{{color:#c8beb2;}}
  </style>
</head>
<body>
<header id="masthead">
  <div id="masthead-inner">
    <a href="../index.html" id="masthead-logo">FitOut<span>Post</span></a>
    <nav>
      <a href="../index.html" class="mh-link">News</a>
      <a href="../pipeline.html" class="mh-link">Pipeline</a>
      <a href="../tenders.html" class="mh-link">Tenders</a>
      <a href="../intelligence.html" class="mh-link">Intelligence</a>
    </nav>
  </div>
</header>

<div id="hero">
  <div id="hero-inner">
    <div class="hero-eyebrow">Country Dossier · {country['continent']}</div>
    <span class="hero-flag">{cf}</span>
    <h1>{cn}</h1>
    <div class="hero-sub">Fit-out industry intelligence for {cn} — news, pipeline and tenders</div>
    <div class="stats-row">
      <div class="stat"><span class="stat-val">{len(c_news)}</span><span class="stat-label">News</span></div>
      <div class="stat"><span class="stat-val">{len(c_pipeline)}</span><span class="stat-label">Pipeline</span></div>
      <div class="stat"><span class="stat-val">{len(c_tenders)}</span><span class="stat-label">Tenders</span></div>
    </div>
  </div>
</div>

<div class="country-nav">
  <div class="country-nav-inner">
    <span style="font-family:var(--sans);font-size:11px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.1em;">Other markets:</span>
    {"".join(f'<a class="country-chip" href="{c["code"]}.html">{c["flag"]} {c["name"]}</a>' for c in COUNTRIES if c["code"] != cc)}
  </div>
</div>

<div id="main">
  <div class="section-title">📰 Latest News</div>
  <div class="items-grid">{news_html}</div>

  <div class="section-title">🏗 Pipeline Projects</div>
  <div class="items-grid">{pipeline_html}</div>

  <div class="section-title">📋 Active Tenders</div>
  <div class="items-grid">{tenders_html}</div>
</div>

<footer id="footer">
  <p>© <span id="fy"></span> FitOut Post · {cn} market intelligence ·
    <a href="../index.html">Home</a> · <a href="../tenders.html">All Tenders</a> ·
    <a href="../contact.html">Contact</a> · <a href="../legal.html">Legal</a>
  </p>
</footer>
<script>document.getElementById("fy").textContent=new Date().getFullYear();</script>
<script src="../search.js"></script>
<script src="../cookie-consent.js"></script>
</body>
</html>"""
    out = OUT_DIR / f"{cc}.html"
    out.write_text(html, encoding="utf-8")
    return total


def build():
    print("Loading data…")
    news, pipeline, tenders = load_data()
    print(f"  News: {len(news)}, Pipeline: {len(pipeline)}, Tenders: {len(tenders)}")

    # Build index page
    build_index()

    for country in COUNTRIES:
        total = build_page(country, news, pipeline, tenders)
        kb = (OUT_DIR / f"{country['code']}.html").stat().st_size // 1024
        print(f"  ✅  {country['flag']} {country['name']} — {total} signals, {kb} KB")

    print(f"\nCountry pages in: countries/")
    print("Add 'countries/' to sitemap.xml and link from the nav or about page.")


def build_index():
    """Build countries/index.html — directory of all country pages."""
    cards = "\n".join(f'''<a class="ccard" href="{c["code"]}.html">
      <span class="ccard-flag">{c["flag"]}</span>
      <span class="ccard-name">{c["name"]}</span>
      <span class="ccard-cont">{c["continent"]}</span>
    </a>''' for c in COUNTRIES)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width,initial-scale=1.0" />
  <title>Country Intelligence — FitOut Post</title>
  <meta name="description" content="Per-country fit-out industry intelligence: news, pipeline and tenders for the world's top fit-out markets." />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://fitoutpost.com/countries/" />
  <meta property="og:title" content="Country Intelligence — FitOut Post" />
  <link rel="canonical" href="https://fitoutpost.com/countries/" />
  <link rel="icon" type="image/svg+xml" href="../favicon.svg" />
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-9ECWT6671C"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-9ECWT6671C',{{anonymize_ip:true}});</script>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  :root{{--salmon:#FFF1E5;--black:#1a1a1a;--claret:#990033;--rule:#D8C9A8;--serif:'Playfair Display',Georgia,serif;--sans:Inter,system-ui,sans-serif;}}
  body{{background:var(--salmon);color:var(--black);font-family:var(--sans);}}
  #masthead{{background:var(--black);border-bottom:3px solid var(--claret);}}
  #masthead-inner{{max-width:1200px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;min-height:52px;}}
  #masthead-logo{{font-family:var(--serif);font-size:22px;font-weight:800;color:#fff;text-decoration:none;}}
  #masthead-logo span{{color:var(--claret);}}
  #hero{{background:var(--black);color:#fff;padding:32px 24px;}}
  #hero-inner{{max-width:1200px;margin:0 auto;}}
  .eyebrow{{font-family:var(--sans);font-size:10px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--claret);margin-bottom:8px;}}
  h1{{font-family:var(--serif);font-size:36px;font-weight:800;line-height:1.1;margin-bottom:8px;}}
  .sub{{font-size:13px;color:#B8A89A;font-family:var(--sans);}}
  #main{{max-width:1200px;margin:0 auto;padding:32px 24px 80px;}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;}}
  .ccard{{background:#fff;border:1px solid var(--rule);border-radius:3px;padding:18px 16px;display:flex;flex-direction:column;gap:4px;text-decoration:none;color:inherit;transition:box-shadow .15s;border-left:3px solid var(--claret);}}
  .ccard:hover{{box-shadow:0 4px 16px rgba(0,0,0,.1);}}
  .ccard-flag{{font-size:32px;line-height:1;}}
  .ccard-name{{font-family:var(--serif);font-size:16px;font-weight:700;margin-top:4px;}}
  .ccard-cont{{font-size:11px;color:#8a7f72;font-family:var(--sans);}}
  #footer{{background:var(--black);color:#8a7f72;font-family:var(--sans);font-size:12px;padding:24px;text-align:center;border-top:2px solid var(--claret);}}
  #footer a{{color:#c8beb2;}}
  </style>
</head>
<body>
<header id="masthead"><div id="masthead-inner">
  <a href="../index.html" id="masthead-logo">FitOut<span>Post</span></a>
</div></header>
<div id="hero"><div id="hero-inner">
  <div class="eyebrow">Country Intelligence</div>
  <h1>Market Dossiers</h1>
  <div class="sub">{len(COUNTRIES)} markets · news, pipeline and tenders by country</div>
</div></div>
<div id="main"><div class="grid">{cards}</div></div>
<footer id="footer">
  <p>© <span id="fy"></span> FitOut Post · <a href="../index.html">Home</a> · <a href="../contact.html">Contact</a></p>
</footer>
<script>document.getElementById("fy").textContent=new Date().getFullYear();</script>
</body>
</html>"""
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"  ✅  countries/index.html ({len(COUNTRIES)} markets)")


if __name__ == "__main__":
    build()
