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
  :root{{
    --salmon:#FFF1E5;--salmon-dk:#F2DFCE;--salmon-md:#FAE8D6;
    --white:#FFFFFF;--black:#1a1a1a;--black-mid:#262626;
    --claret:#990033;--claret-lt:#CC0044;--teal:#0D7680;--amber:#E8820C;
    --warm-gray:#66605A;--mid-gray:#9A948E;--card-bg:#FFFFFF;--body-bg:#FAF5F0;
    --border:#D8C9A8;--border-dk:#BBA898;
    --serif:'Playfair Display','EB Garamond',Georgia,serif;
    --garamond:'EB Garamond',Georgia,serif;
    --sans:Inter,system-ui,sans-serif;
  }}
  body{{background:var(--salmon);color:var(--black);font-family:var(--garamond);line-height:1.6;-webkit-font-smoothing:antialiased;}}
  a{{color:inherit;text-decoration:none;}}a:hover{{color:var(--claret);}}
  #masthead{{background:var(--salmon);border-bottom:2px solid var(--black);position:sticky;top:0;z-index:200;}}
  #masthead-inner{{max-width:1320px;margin:0 auto;padding:0 24px;height:72px;display:flex;align-items:center;gap:24px;}}
  #fop-logo{{display:flex;align-items:center;gap:14px;flex-shrink:0;cursor:default;user-select:none;text-decoration:none;}}
  #fop-logo:hover{{color:inherit;}}
  #fop-box{{width:52px;height:52px;background:var(--black);display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
  #fop-box span{{font-family:var(--serif);font-weight:800;font-size:24px;letter-spacing:1px;color:#fff;line-height:1;}}
  #fop-wordmark{{display:flex;flex-direction:column;line-height:1.2;}}
  #fop-wordmark strong{{font-family:var(--serif);font-weight:700;font-size:20px;letter-spacing:0.2px;color:var(--black);}}
  #fop-wordmark em{{font-style:normal;font-size:10px;letter-spacing:1.4px;text-transform:uppercase;color:var(--warm-gray);font-weight:500;margin-top:2px;}}
  #masthead-right{{margin-left:auto;display:flex;align-items:center;gap:16px;flex-shrink:0;}}
  .masthead-nav-link{{font-size:12.5px;font-weight:500;color:var(--black);padding:6px 14px;border:1px solid var(--border-dk);transition:background .15s,border-color .15s,color .15s;white-space:nowrap;}}
  .masthead-nav-link:hover{{background:var(--black);border-color:var(--black);color:#fff;}}
  .masthead-nav-link--cta{{background:var(--claret);border-color:var(--claret);color:#fff;font-weight:600;padding:6px 18px;letter-spacing:0.2px;}}
  .masthead-nav-link--cta:hover{{background:var(--claret-lt);border-color:var(--claret-lt);color:#fff;}}
  .mh-util-link{{font-size:11px;color:var(--warm-gray);transition:color .15s;white-space:nowrap;}}
  .mh-util-link:hover{{color:var(--black);}}
  .mh-util-sep{{width:1px;height:14px;background:var(--border-dk);flex-shrink:0;}}
  #product-nav{{background:var(--black);position:sticky;top:72px;z-index:195;}}
  #product-nav-inner{{max-width:1320px;margin:0 auto;padding:0 24px;display:flex;gap:0;}}
  .pnav-link{{display:inline-block;padding:0 20px;height:38px;line-height:38px;font-size:12.5px;font-weight:500;color:rgba(255,255,255,.65);letter-spacing:.3px;border-right:1px solid rgba(255,255,255,.1);transition:color .15s,background .15s;white-space:nowrap;cursor:pointer;}}
  .pnav-link:first-child{{border-left:1px solid rgba(255,255,255,.1);}}
  .pnav-link:hover{{color:#fff;background:rgba(255,255,255,.08);}}
  .pnav-link.active{{color:#fff;background:var(--claret);border-color:var(--claret);}}
  .pnav-link.active+.pnav-link{{border-left-color:var(--claret);}}
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
  #footer{{background:var(--black);color:#A09890;margin-top:80px;}}
  #footer-main{{max-width:1320px;margin:0 auto;padding:48px 24px 40px;display:grid;grid-template-columns:2fr 1.2fr;gap:48px;border-bottom:1px solid #2e2e2e;}}
  #footer-brand .footer-logo-wrap{{display:flex;align-items:center;gap:12px;margin-bottom:16px;}}
  #footer-fop-box{{width:40px;height:40px;background:#fff;display:flex;align-items:center;justify-content:center;}}
  #footer-fop-box span{{font-family:var(--serif);font-weight:800;font-size:18px;color:var(--black);line-height:1;}}
  #footer-fop-wordmark{{display:flex;flex-direction:column;}}
  #footer-fop-name{{font-family:var(--serif);font-weight:700;font-size:16px;color:#fff;}}
  #footer-fop-tagline{{font-size:9px;letter-spacing:1.2px;text-transform:uppercase;color:#7a706a;margin-top:2px;}}
  #footer-brand p{{font-size:12px;line-height:1.6;color:#7a706a;margin-bottom:10px;}}
  .footer-disclaimer{{font-size:10px;line-height:1.55;color:#5a5050;}}
  #footer-ad-box{{background:#1e1e1e;border:1px solid #2e2e2e;padding:24px;}}
  #footer-ad-badge{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#5a5050;margin-bottom:10px;}}
  #footer-ad-headline{{font-family:var(--serif);font-size:17px;color:#D4C4BA;margin-bottom:8px;line-height:1.35;}}
  #footer-ad-sub{{font-size:12px;color:#7a706a;margin-bottom:14px;line-height:1.5;}}
  #footer-ad-cta{{display:inline-block;font-size:12px;color:var(--amber);border-bottom:1px solid currentColor;padding-bottom:1px;}}
  #footer-bottom{{max-width:1320px;margin:0 auto;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;}}
  #footer-copyright{{font-size:11.5px;color:#7a706a;}}
  #footer-legal-links{{display:flex;gap:20px;}}
  #footer-legal-links a{{font-size:11.5px;color:#7a706a;transition:color .15s;}}
  #footer-legal-links a:hover{{color:#9A8A80;}}
  @media(max-width:768px){{#footer-main{{grid-template-columns:1fr;gap:24px;}}#footer-bottom{{flex-direction:column;align-items:flex-start;}}}}
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
      <a href="../contact.html" class="mh-util-link">Contact</a>
      <div class="mh-util-sep"></div>
      <a class="masthead-nav-link masthead-nav-link--cta" href="../register.html">Register free →</a>
    </div>
  </div>
</header>

<nav id="product-nav" role="navigation" aria-label="Sections">
  <div id="product-nav-inner">
    <a class="pnav-link" href="../index.html">Home</a>
    <a class="pnav-link" href="../news.html">News</a>
    <a class="pnav-link" href="../weekly.html">Roundup</a>
    <a class="pnav-link" href="../tenders.html">Tenders</a>
    <a class="pnav-link" href="../pipeline.html">Pipeline</a>
    <a class="pnav-link" href="../awards.html">Awards</a>
    <a class="pnav-link" href="../intelligence.html">Intelligence</a>
    <a class="pnav-link" href="../companies_site.html">Companies</a>
    <a class="pnav-link active" href="index.html">Countries</a>
    <a class="pnav-link" href="../events.html">Events</a>
  </div>
</nav>

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

<footer id="footer" role="contentinfo">
  <div id="footer-main">
    <div id="footer-brand">
      <div class="footer-logo-wrap">
        <div id="footer-fop-box"><span>FO</span><span style="color:var(--claret)">P</span></div>
        <div id="footer-fop-wordmark">
          <div id="footer-fop-name">Fit&nbsp;Out <span style="color:var(--claret)">Post</span></div>
          <div id="footer-fop-tagline">Global Industry Intelligence</div>
        </div>
      </div>
      <p>An independent aggregator of global fit-out and interior construction news.
         Articles are drawn from industry publications, company announcements, and
         newswires across more than 50 countries. Updated daily.</p>
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
    <div id="footer-copyright">© <span id="footer-year"></span> FitOut Post. An independent publication. All rights reserved.</div>
    <div id="footer-legal-links">
      <a href="../legal.html#terms">Terms of use</a>
      <a href="../legal.html#privacy">Privacy policy</a>
      <a href="../legal.html#cookies">Cookie policy</a>
      <a href="../contact.html">Contact</a>
    </div>
  </div>
</footer>
<script>document.getElementById("footer-year").textContent=new Date().getFullYear();</script>
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
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
  :root{{
    --salmon:#FFF1E5;--salmon-dk:#F2DFCE;--white:#FFFFFF;--black:#1a1a1a;--black-mid:#262626;
    --claret:#990033;--claret-lt:#CC0044;--warm-gray:#66605A;--mid-gray:#9A948E;
    --border:#D8C9A8;--border-dk:#BBA898;
    --serif:'Playfair Display','EB Garamond',Georgia,serif;--sans:Inter,system-ui,sans-serif;
  }}
  body{{background:var(--salmon);color:var(--black);font-family:var(--sans);-webkit-font-smoothing:antialiased;}}
  a{{color:inherit;text-decoration:none;}}a:hover{{color:var(--claret);}}
  #masthead{{background:var(--salmon);border-bottom:2px solid var(--black);position:sticky;top:0;z-index:200;}}
  #masthead-inner{{max-width:1320px;margin:0 auto;padding:0 24px;height:72px;display:flex;align-items:center;gap:24px;}}
  #fop-logo{{display:flex;align-items:center;gap:14px;flex-shrink:0;cursor:default;user-select:none;text-decoration:none;}}
  #fop-logo:hover{{color:inherit;}}
  #fop-box{{width:52px;height:52px;background:var(--black);display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
  #fop-box span{{font-family:var(--serif);font-weight:800;font-size:24px;letter-spacing:1px;color:#fff;line-height:1;}}
  #fop-wordmark{{display:flex;flex-direction:column;line-height:1.2;}}
  #fop-wordmark strong{{font-family:var(--serif);font-weight:700;font-size:20px;letter-spacing:0.2px;color:var(--black);}}
  #fop-wordmark em{{font-style:normal;font-size:10px;letter-spacing:1.4px;text-transform:uppercase;color:var(--warm-gray);font-weight:500;margin-top:2px;}}
  #masthead-right{{margin-left:auto;display:flex;align-items:center;gap:16px;flex-shrink:0;}}
  .masthead-nav-link{{font-size:12.5px;font-weight:500;color:var(--black);padding:6px 14px;border:1px solid var(--border-dk);transition:background .15s,border-color .15s,color .15s;white-space:nowrap;}}
  .masthead-nav-link:hover{{background:var(--black);border-color:var(--black);color:#fff;}}
  .masthead-nav-link--cta{{background:var(--claret);border-color:var(--claret);color:#fff;font-weight:600;padding:6px 18px;letter-spacing:0.2px;}}
  .masthead-nav-link--cta:hover{{background:var(--claret-lt);border-color:var(--claret-lt);color:#fff;}}
  .mh-util-link{{font-size:11px;color:var(--warm-gray);transition:color .15s;white-space:nowrap;}}
  .mh-util-link:hover{{color:var(--black);}}
  .mh-util-sep{{width:1px;height:14px;background:var(--border-dk);flex-shrink:0;}}
  #product-nav{{background:var(--black);position:sticky;top:72px;z-index:195;}}
  #product-nav-inner{{max-width:1320px;margin:0 auto;padding:0 24px;display:flex;gap:0;}}
  .pnav-link{{display:inline-block;padding:0 20px;height:38px;line-height:38px;font-size:12.5px;font-weight:500;color:rgba(255,255,255,.65);letter-spacing:.3px;border-right:1px solid rgba(255,255,255,.1);transition:color .15s,background .15s;white-space:nowrap;}}
  .pnav-link:first-child{{border-left:1px solid rgba(255,255,255,.1);}}
  .pnav-link:hover{{color:#fff;background:rgba(255,255,255,.08);}}
  .pnav-link.active{{color:#fff;background:var(--claret);border-color:var(--claret);}}
  #hero{{background:var(--black);color:#fff;padding:32px 24px;}}
  #hero-inner{{max-width:1320px;margin:0 auto;}}
  .eyebrow{{font-family:var(--sans);font-size:10px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--claret);margin-bottom:8px;}}
  h1{{font-family:var(--serif);font-size:36px;font-weight:800;line-height:1.1;margin-bottom:8px;}}
  .sub{{font-size:13px;color:#B8A89A;font-family:var(--sans);}}
  #main{{max-width:1320px;margin:0 auto;padding:32px 24px 80px;}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;}}
  .ccard{{background:#fff;border:1px solid var(--border);border-radius:3px;padding:18px 16px;display:flex;flex-direction:column;gap:4px;text-decoration:none;color:inherit;transition:box-shadow .15s;border-left:3px solid var(--claret);}}
  .ccard:hover{{box-shadow:0 4px 16px rgba(0,0,0,.1);}}
  .ccard-flag{{font-size:32px;line-height:1;}}
  .ccard-name{{font-family:var(--serif);font-size:16px;font-weight:700;margin-top:4px;}}
  .ccard-cont{{font-size:11px;color:var(--warm-gray);font-family:var(--sans);}}
  #footer{{background:var(--black);color:#A09890;margin-top:80px;}}
  #footer-main{{max-width:1320px;margin:0 auto;padding:48px 24px 40px;display:grid;grid-template-columns:2fr 1.2fr;gap:48px;border-bottom:1px solid #2e2e2e;}}
  #footer-brand .footer-logo-wrap{{display:flex;align-items:center;gap:12px;margin-bottom:16px;}}
  #footer-fop-box{{width:40px;height:40px;background:#fff;display:flex;align-items:center;justify-content:center;}}
  #footer-fop-box span{{font-family:var(--serif);font-weight:800;font-size:18px;color:var(--black);line-height:1;}}
  #footer-fop-wordmark{{display:flex;flex-direction:column;}}
  #footer-fop-name{{font-family:var(--serif);font-weight:700;font-size:16px;color:#fff;}}
  #footer-fop-tagline{{font-size:9px;letter-spacing:1.2px;text-transform:uppercase;color:#7a706a;margin-top:2px;}}
  #footer-brand p{{font-size:12px;line-height:1.6;color:#7a706a;margin-bottom:10px;}}
  .footer-disclaimer{{font-size:10px;line-height:1.55;color:#5a5050;}}
  #footer-ad-box{{background:#1e1e1e;border:1px solid #2e2e2e;padding:24px;}}
  #footer-ad-badge{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#5a5050;margin-bottom:10px;}}
  #footer-ad-headline{{font-family:var(--serif);font-size:17px;color:#D4C4BA;margin-bottom:8px;line-height:1.35;}}
  #footer-ad-sub{{font-size:12px;color:#7a706a;margin-bottom:14px;line-height:1.5;}}
  #footer-ad-cta{{display:inline-block;font-size:12px;color:var(--amber);border-bottom:1px solid currentColor;padding-bottom:1px;}}
  #footer-bottom{{max-width:1320px;margin:0 auto;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;}}
  #footer-copyright{{font-size:11.5px;color:#7a706a;}}
  #footer-legal-links{{display:flex;gap:20px;}}
  #footer-legal-links a{{font-size:11.5px;color:#7a706a;transition:color .15s;}}
  #footer-legal-links a:hover{{color:#9A8A80;}}
  @media(max-width:768px){{#footer-main{{grid-template-columns:1fr;gap:24px;}}#footer-bottom{{flex-direction:column;align-items:flex-start;}}}}
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
      <a href="../contact.html" class="mh-util-link">Contact</a>
      <div class="mh-util-sep"></div>
      <a class="masthead-nav-link masthead-nav-link--cta" href="../register.html">Register free →</a>
    </div>
  </div>
</header>
<nav id="product-nav" role="navigation" aria-label="Sections">
  <div id="product-nav-inner">
    <a class="pnav-link" href="../index.html">Home</a>
    <a class="pnav-link" href="../news.html">News</a>
    <a class="pnav-link" href="../weekly.html">Roundup</a>
    <a class="pnav-link" href="../tenders.html">Tenders</a>
    <a class="pnav-link" href="../pipeline.html">Pipeline</a>
    <a class="pnav-link" href="../awards.html">Awards</a>
    <a class="pnav-link" href="../intelligence.html">Intelligence</a>
    <a class="pnav-link" href="../companies_site.html">Companies</a>
    <a class="pnav-link active" href="index.html">Countries</a>
    <a class="pnav-link" href="../events.html">Events</a>
  </div>
</nav>
<div id="hero"><div id="hero-inner">
  <div class="eyebrow">Country Intelligence</div>
  <h1>Market Dossiers</h1>
  <div class="sub">{len(COUNTRIES)} markets · news, pipeline and tenders by country</div>
</div></div>
<div id="main"><div class="grid">{cards}</div></div>
<footer id="footer" role="contentinfo">
  <div id="footer-main">
    <div id="footer-brand">
      <div class="footer-logo-wrap">
        <div id="footer-fop-box"><span>FO</span><span style="color:var(--claret)">P</span></div>
        <div id="footer-fop-wordmark">
          <div id="footer-fop-name">Fit&nbsp;Out <span style="color:var(--claret)">Post</span></div>
          <div id="footer-fop-tagline">Global Industry Intelligence</div>
        </div>
      </div>
      <p>An independent aggregator of global fit-out and interior construction news.
         Articles are drawn from industry publications, company announcements, and
         newswires across more than 50 countries. Updated daily.</p>
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
    <div id="footer-copyright">© <span id="footer-year"></span> FitOut Post. An independent publication. All rights reserved.</div>
    <div id="footer-legal-links">
      <a href="../legal.html#terms">Terms of use</a>
      <a href="../legal.html#privacy">Privacy policy</a>
      <a href="../legal.html#cookies">Cookie policy</a>
      <a href="../contact.html">Contact</a>
    </div>
  </div>
</footer>
<script>document.getElementById("footer-year").textContent=new Date().getFullYear();</script>
</body>
</html>"""
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"  ✅  countries/index.html ({len(COUNTRIES)} markets)")


if __name__ == "__main__":
    build()
