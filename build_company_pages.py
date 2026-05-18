#!/usr/bin/env python3
"""
Build per-company profile pages for FitOut Post.
Generates companies/[id].html for each company in companies.json.
"""
import json, re
from pathlib import Path
from datetime import datetime, timezone

BASE    = Path(__file__).parent
OUT_DIR = BASE / "companies"
OUT_DIR.mkdir(exist_ok=True)

def esc(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def load_data():
    companies = json.loads((BASE / "companies.json").read_text(encoding="utf-8"))["companies"]
    news_raw  = json.loads((BASE / "news.json").read_text(encoding="utf-8"))["articles"]
    return companies, news_raw


def matched_articles(company_id, news):
    """Return articles that matched this company at build time."""
    out = []
    for a in news:
        mc = a.get("matched_companies") or []
        if any(m.get("id") == company_id for m in mc):
            out.append(a)
    return out


def slug_name_articles(company_name, news, limit=10):
    """Fallback: substring search in title for companies with no matched articles."""
    words = [w for w in re.split(r"\W+", company_name) if len(w) > 3]
    if not words:
        return []
    pat = re.compile("|".join(re.escape(w) for w in words[:3]), re.IGNORECASE)
    return [a for a in news if pat.search(a.get("title",""))][:limit]


def fmt_revenue(r):
    if not r:
        return None
    if r >= 1000:
        return f"£{r/1000:.1f}bn"
    return f"£{r:.0f}m"


def build_page(company, news):
    cid  = company["id"]
    name = company["name"]
    ctype = company.get("type","")
    hq    = company.get("hq","")
    country = company.get("country","")
    continent = company.get("continent","")
    founded = company.get("founded","")
    parent  = company.get("parent","")
    revenue = fmt_revenue(company.get("revenue_gbp_m"))
    rev_year = company.get("revenue_year","")
    employees = company.get("employees","")
    website  = company.get("website","")
    _contact_raw = company.get("contact") or {}
    contact = _contact_raw if isinstance(_contact_raw, dict) else {"email": _contact_raw}
    description = company.get("description","")
    notable  = company.get("notable_projects") or []
    services = company.get("services") or []
    sectors  = company.get("sectors") or []
    locations = company.get("locations") or []
    tags     = company.get("tags") or []
    listed   = company.get("listed", False)

    # Matched news
    articles = matched_articles(cid, news)
    if not articles:
        articles = slug_name_articles(name, news)

    # ── Structured data ─────────────────────────────────────────────────────
    org_ld = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": name,
        "description": description,
        "url": website or f"https://fitoutpost.com/companies/{cid}.html",
    }
    if founded:
        org_ld["foundingDate"] = str(founded)
    if hq:
        org_ld["location"] = {"@type": "PostalAddress", "addressLocality": hq}
    if employees:
        org_ld["numberOfEmployees"] = {"@type": "QuantitativeValue", "description": employees}
    if parent:
        org_ld["parentOrganization"] = {"@type": "Organization", "name": parent}

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type":"ListItem","position":1,"name":"FitOut Post","item":"https://fitoutpost.com/"},
            {"@type":"ListItem","position":2,"name":"Companies","item":"https://fitoutpost.com/companies_site.html"},
            {"@type":"ListItem","position":3,"name":name,"item":f"https://fitoutpost.com/companies/{cid}.html"},
        ]
    }

    # ── Stat chips ───────────────────────────────────────────────────────────
    stats = []
    if revenue:
        stats.append(("Revenue", f"{revenue} ({rev_year})" if rev_year else revenue))
    if employees:
        stats.append(("Employees", employees))
    if founded:
        stats.append(("Founded", str(founded)))
    if listed:
        stats.append(("Listed", "Public company"))

    stats_html = "".join(
        f'<div class="stat"><span class="stat-val">{esc(v)}</span><span class="stat-label">{esc(k)}</span></div>'
        for k, v in stats
    )

    # ── Chips ────────────────────────────────────────────────────────────────
    def chips(items, cls):
        return "".join(f'<span class="{cls}">{esc(i)}</span>' for i in items)

    # ── News cards ──────────────────────────────────────────────────────────
    def news_card(a):
        title = esc(a.get("title",""))
        url   = esc(a.get("url","#"))
        src   = esc(a.get("source",""))
        date  = esc((a.get("published","") or "")[:10])
        sig   = esc(a.get("signal_type",""))
        return f'''<div class="item-card">
          <div class="item-meta">{f'<span class="badge sig">{sig}</span>' if sig else ''}{f'<span class="item-date">{date}</span>' if date else ''}</div>
          <div class="item-headline"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
          {f'<div class="item-source">{src}</div>' if src else ''}
        </div>'''

    news_html = "\n".join(news_card(a) for a in articles[:20]) \
             or '<div class="no-data">No recent news matched — check back soon.</div>'

    # ── Notable projects ─────────────────────────────────────────────────────
    notables_html = ""
    if notable:
        items = "".join(f"<li>{esc(p)}</li>" for p in notable)
        notables_html = f'<div class="section-title">Notable Projects</div><ul class="notables">{items}</ul>'

    # ── Contact block ────────────────────────────────────────────────────────
    contact_items = []
    if website:
        contact_items.append(f'<a href="{esc(website)}" target="_blank" rel="noopener nofollow" class="contact-link ext">{esc(website.replace("https://","").replace("http://","").rstrip("/"))}</a>')
    if contact.get("linkedin"):
        contact_items.append(f'<a href="{esc(contact["linkedin"])}" target="_blank" rel="noopener nofollow" class="contact-link linkedin">LinkedIn</a>')
    if contact.get("email"):
        contact_items.append(f'<a href="mailto:{esc(contact["email"])}" class="contact-link email">{esc(contact["email"])}</a>')
    if contact.get("phone"):
        contact_items.append(f'<span class="contact-link phone">{esc(contact["phone"])}</span>')
    contact_html = f'<div class="section-title">Contact</div><div class="contact-row">{"".join(contact_items)}</div>' if contact_items else ""

    # ── Parent note ─────────────────────────────────────────────────────────
    parent_html = f'<div class="parent-note">Part of <strong>{esc(parent)}</strong></div>' if parent else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(name)} — Fit-Out Company Profile | FitOut Post</title>
  <meta name="description" content="{esc(description[:160]) if description else esc(f'{name} is a {ctype} based in {hq}. Fit-out industry profile, news and projects on FitOut Post.')}" />
  <meta property="og:type" content="profile" />
  <meta property="og:site_name" content="FitOut Post" />
  <meta property="og:title" content="{esc(name)} — Fit-Out Company Profile" />
  <meta property="og:description" content="{esc((description or '')[:160])}" />
  <meta property="og:url" content="https://fitoutpost.com/companies/{cid}.html" />
  <meta property="og:image" content="https://fitoutpost.com/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="canonical" href="https://fitoutpost.com/companies/{cid}.html" />
  <link rel="icon" type="image/svg+xml" href="../favicon.svg" />
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-9ECWT6671C"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-9ECWT6671C',{{anonymize_ip:true}});</script>
  <script type="application/ld+json">{json.dumps(org_ld, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(breadcrumb_ld, ensure_ascii=False)}</script>
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
  h1{{font-family:var(--serif);font-size:clamp(28px,4vw,44px);font-weight:800;line-height:1.1;margin-bottom:6px;}}
  .hero-type{{font-family:var(--sans);font-size:13px;color:#B8A89A;margin-bottom:4px;}}
  .hero-hq{{font-family:var(--sans);font-size:13px;color:#8a7f72;}}
  .stats-row{{display:flex;gap:24px;flex-wrap:wrap;margin-top:20px;}}
  .stat{{font-family:var(--sans);text-align:center;min-width:80px;}}
  .stat-val{{font-size:20px;font-weight:700;color:#fff;display:block;}}
  .stat-label{{font-size:10px;color:#8a7f72;text-transform:uppercase;letter-spacing:.1em;}}
  #main{{max-width:1200px;margin:0 auto;padding:36px 24px 80px;}}
  .section-title{{font-family:var(--serif);font-size:20px;font-weight:700;border-bottom:2px solid var(--claret);padding-bottom:8px;margin:32px 0 14px;}}
  .description{{font-size:16px;line-height:1.7;color:var(--black-mid);max-width:740px;margin-bottom:24px;}}
  .parent-note{{font-family:var(--sans);font-size:13px;color:var(--warm-gray);margin-bottom:16px;}}
  .chips{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;}}
  .chip{{font-family:var(--sans);font-size:11px;padding:4px 12px;border-radius:20px;}}
  .chip-service{{background:#f0f4ff;color:#2a4f8f;border:1px solid #c8d6f8;}}
  .chip-sector{{background:#fff4e0;color:#7a3f00;border:1px solid #f5d89a;}}
  .chip-location{{background:#f0faf4;color:#1a5a30;border:1px solid #a8d8bc;}}
  .chip-tag{{background:#f8f0f8;color:#6a2a6a;border:1px solid #e0b8e0;}}
  .notables{{font-family:var(--sans);font-size:13px;line-height:1.8;padding-left:20px;color:var(--black-mid);}}
  .items-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;}}
  .item-card{{background:#fff;border:1px solid var(--border);border-radius:2px;padding:14px 16px;border-left:3px solid var(--claret);}}
  .item-meta{{display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;}}
  .badge.sig{{font-family:var(--sans);font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;border-radius:10px;background:#e8f0f8;color:#2a5f8f;}}
  .item-date{{font-family:var(--sans);font-size:11px;color:var(--warm-gray);}}
  .item-headline{{font-family:var(--garamond);font-size:15px;line-height:1.35;}}
  .item-headline a{{color:var(--black);}}
  .item-headline a:hover{{color:var(--claret);}}
  .item-source{{font-family:var(--sans);font-size:11px;color:var(--warm-gray);margin-top:4px;}}
  .no-data{{font-family:var(--sans);font-size:13px;color:var(--warm-gray);padding:20px 0;font-style:italic;}}
  .contact-row{{display:flex;flex-wrap:wrap;gap:12px;align-items:center;}}
  .contact-link{{font-family:var(--sans);font-size:13px;padding:6px 16px;border:1px solid var(--border-dk);color:var(--black);transition:all .15s;}}
  .contact-link:hover{{background:var(--black);color:#fff;border-color:var(--black);}}
  .contact-link.linkedin{{border-color:#0077b5;color:#0077b5;}}
  .contact-link.linkedin:hover{{background:#0077b5;color:#fff;}}
  .back-link{{font-family:var(--sans);font-size:13px;color:var(--warm-gray);margin-bottom:24px;display:inline-block;}}
  .back-link:hover{{color:var(--claret);}}
  @media(prefers-color-scheme:dark){{
    :root{{--salmon:#1e1912;--black:#f0ede8;--black-mid:#d8d2cc;--warm-gray:#9a948e;--border:#3a3530;--border-dk:#4a4540;--card-bg:#252018;}}
    body{{background:var(--salmon);color:var(--black);}}
    #hero{{background:#0d0b08;}}
    .item-card{{background:#252018;border-color:var(--border);}}
    .chip-service{{background:#1a2540;color:#8ab0e8;border-color:#2a3a60;}}
    .chip-sector{{background:#2a1e00;color:#d4a050;border-color:#4a3800;}}
    .chip-location{{background:#0a2015;color:#5ab87a;border-color:#1a4030;}}
    .chip-tag{{background:#2a1a2a;color:#c880c8;border-color:#4a2a4a;}}
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
      <a href="mailto:hello@fitoutpost.com" class="masthead-nav-link" style="border:none;padding:0;font-size:11px;color:var(--warm-gray);">Contact</a>
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
    <a class="pnav-link active" href="../companies_site.html">Companies</a>
    <a class="pnav-link" href="../countries/index.html">Countries</a>
    <a class="pnav-link" href="../sectors/index.html">Sectors</a>
  </div>
</nav>

<div id="hero">
  <div id="hero-inner">
    <div class="hero-eyebrow">{esc(continent)} · {esc(ctype)}</div>
    <h1>{esc(name)}</h1>
    <div class="hero-type">{esc(hq)}</div>
    {parent_html}
    <div class="stats-row">{stats_html}</div>
  </div>
</div>

<div id="main">
  <a class="back-link" href="../companies_site.html">← All companies</a>

  {f'<p class="description">{esc(description)}</p>' if description else ''}

  {f'<div class="section-title">Sectors</div><div class="chips">{chips(sectors, "chip chip-sector")}</div>' if sectors else ''}
  {f'<div class="section-title">Services</div><div class="chips">{chips(services, "chip chip-service")}</div>' if services else ''}
  {f'<div class="section-title">Locations</div><div class="chips">{chips(locations, "chip chip-location")}</div>' if locations else ''}
  {f'<div class="section-title">Tags</div><div class="chips">{chips(tags, "chip chip-tag")}</div>' if tags else ''}

  {notables_html}

  <div class="section-title">Latest News</div>
  <div class="items-grid">{news_html}</div>
  <p style="font-family:var(--sans);font-size:13px;margin-top:16px;">
    <a href="../news.html" style="color:var(--claret);border-bottom:1px solid currentColor;padding-bottom:1px;">→ All fit-out industry news on FitOut Post</a>
  </p>

  {contact_html}
</div>

<script src="../cookie-consent.js"></script>
</body>
</html>"""
    out = OUT_DIR / f"{cid}.html"
    out.write_text(html, encoding="utf-8")
    return len(articles)


def build_index(companies):
    """Build companies/index.html — redirect to companies_site.html."""
    html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<meta http-equiv="refresh" content="0;url=../companies_site.html"/>
<title>Companies — FitOut Post</title>
<link rel="canonical" href="https://fitoutpost.com/companies_site.html"/>
</head><body><a href="../companies_site.html">View all companies →</a></body></html>"""
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")


def build():
    print("Loading data…")
    companies, news = load_data()
    print(f"  Companies: {len(companies)}, News articles: {len(news)}")

    build_index(companies)

    total_news = 0
    for company in companies:
        n = build_page(company, news)
        total_news += n
        kb = (OUT_DIR / f"{company['id']}.html").stat().st_size // 1024
        print(f"  ✅  {company['name']} — {n} news articles, {kb} KB")

    print(f"\n✅  {len(companies)} company pages in: companies/")
    print(f"    {total_news} total news links across all pages")


if __name__ == "__main__":
    build()
