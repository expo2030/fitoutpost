#!/usr/bin/env python3
"""
Build timeline.html — chronological industry milestones from pipeline + news data.
Extracts significant announcements, project starts, completions, and awards.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
TEMPLATE_PATH = BASE / "timeline.html"

MILESTONE_KEYWORDS = [
    "opens", "opened", "opening", "unveiled", "launched", "launch", "launches",
    "complete", "completed", "completion", "delivered", "handover",
    "breaks ground", "groundbreaking", "starts construction", "construction starts",
    "awarded", "award", "wins contract", "secured contract", "announced",
    "milestone", "record", "landmark", "first", "largest", "biggest",
    "new headquarters", "new office", "new hotel", "new retail",
    "major project", "flagship", "luxury", "expansion", "renovation",
    "refurbishment", "transformation",
]

def extract_year(date_str):
    if not date_str:
        return "Unknown"
    m = re.search(r'(202[0-9]|201[0-9])', str(date_str))
    return m.group(1) if m else "Unknown"

def classify_milestone(text):
    text_l = text.lower()
    if any(kw in text_l for kw in ["awarded", "award", "wins contract", "contract signed", "appointed"]):
        return "Award"
    if any(kw in text_l for kw in ["opens", "opened", "opening", "complete", "completed", "delivered", "handover"]):
        return "Completion"
    if any(kw in text_l for kw in ["breaks ground", "groundbreaking", "starts construction", "construction start"]):
        return "Groundbreaking"
    if any(kw in text_l for kw in ["announced", "launch", "launches", "new ", "unveiled", "planned"]):
        return "Announcement"
    return "News"

def load_milestones():
    milestones = []

    # From pipeline.json
    pf = BASE / "pipeline.json"
    if pf.exists():
        pl = json.loads(pf.read_text(encoding="utf-8"))
        for a in pl.get("items", []):
            headline = a.get("headline") or a.get("title") or ""
            text = (headline + " " + (a.get("description") or "")).lower()
            if any(kw in text for kw in MILESTONE_KEYWORDS):
                milestones.append({
                    "type":     classify_milestone(headline),
                    "headline": headline,
                    "url":      a.get("url", ""),
                    "source":   a.get("source", ""),
                    "date":     a.get("pub_date") or a.get("date_display", ""),
                    "year":     extract_year(a.get("pub_date") or a.get("date_display", "")),
                    "country":  a.get("country") or a.get("geo_country", ""),
                    "continent":a.get("continent") or a.get("geo_continent", ""),
                    "sector":   a.get("sector", ""),
                    "_src":     "pipeline",
                })

    # From news.json
    nf = BASE / "news.json"
    if nf.exists():
        news = json.loads(nf.read_text(encoding="utf-8"))
        for a in news.get("articles", []):
            headline = a.get("headline") or a.get("title") or ""
            text = (headline + " " + (a.get("description") or "")).lower()
            if any(kw in text for kw in MILESTONE_KEYWORDS):
                milestones.append({
                    "type":     classify_milestone(headline),
                    "headline": headline,
                    "url":      a.get("url", ""),
                    "source":   a.get("source", ""),
                    "date":     a.get("pub_date") or a.get("date_display", ""),
                    "year":     extract_year(a.get("pub_date") or a.get("date_display", "")),
                    "country":  a.get("country") or a.get("geo_country", ""),
                    "continent":a.get("continent") or a.get("geo_continent", ""),
                    "sector":   a.get("sector", ""),
                    "_src":     "news",
                })

    # Deduplicate by URL
    seen = set()
    unique = []
    for m in milestones:
        key = m.get("url") or m.get("headline", "")[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(m)

    unique.sort(key=lambda x: x.get("date", ""), reverse=True)
    return unique


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Timeline — FitOut Post</title>
  <meta name="description" content="Chronological timeline of global fit-out industry milestones: project announcements, groundbreakings, completions and contract awards." />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="FitOut Post" />
  <meta property="og:title" content="Industry Timeline — FitOut Post" />
  <meta property="og:description" content="Chronological timeline of global fit-out industry milestones: announcements, groundbreakings, completions and contract awards." />
  <meta property="og:url" content="https://fitoutpost.com/timeline.html" />
  <meta property="og:image" content="https://fitoutpost.com/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:site" content="@fitoutpost" />
  <link rel="canonical" href="https://fitoutpost.com/timeline.html" />
  <link rel="icon" type="image/svg+xml" href="https://fitoutpost.com/favicon.svg" />
  <!-- Google Analytics 4 — replace G-FITOUTPOST1 with your real Measurement ID -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-FITOUTPOST1"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-FITOUTPOST1',{{anonymize_ip:true}});</script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=EB+Garamond:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet" />
  <script type="application/json" id="timeline-data">
  {TIMELINE_JSON}
  </script>
  <style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --salmon:  #FFF1E5; --salmon-dk: #F2DFCE; --white: #FFFFFF;
    --black:   #1a1a1a; --claret: #990033; --claret-lt: #CC0044;
    --warm-gray: #8a7f72; --rule: #D8C9A8;
    --serif: 'Playfair Display', Georgia, serif;
    --garamond: 'EB Garamond', Georgia, serif;
    --sans: Inter, system-ui, sans-serif;
  }}
  body {{ background: var(--salmon); color: var(--black); font-family: var(--garamond); font-size: 17px; line-height: 1.6; }}
  a {{ color: inherit; text-decoration: none; }}
  a:hover {{ color: var(--claret); }}

  /* Masthead */
  #masthead {{ background: var(--black); border-bottom: 3px solid var(--claret); }}
  #masthead-inner {{ max-width:1320px; margin:0 auto; padding:0 24px; display:flex; align-items:center; justify-content:space-between; gap:16px; min-height:52px; }}
  #masthead-logo {{ font-family:var(--serif); font-size:22px; font-weight:800; color:#fff; text-decoration:none; letter-spacing:-.3px; }}
  #masthead-logo span {{ color: var(--claret); }}
  #masthead-nav {{ display:flex; gap:0; }}
  .mh-link {{ color:#c8beb2; font-family:var(--sans); font-size:12px; font-weight:500; letter-spacing:.5px; text-transform:uppercase; text-decoration:none; padding:16px 14px; display:block; transition:color .15s; }}
  .mh-link:hover, .mh-link.active {{ color:#fff; }}
  .mh-link.active {{ border-bottom:2px solid var(--claret); }}

  /* Hero */
  #page-hero {{ background:var(--black); color:#fff; padding:28px 0 24px; border-bottom:1px solid #333; }}
  #page-hero-inner {{ max-width:1320px; margin:0 auto; padding:0 24px; }}
  .hero-eyebrow {{ font-family:var(--sans); font-size:10px; font-weight:700; letter-spacing:.2em; text-transform:uppercase; color:var(--claret); margin-bottom:8px; }}
  #page-hero h1 {{ font-family:var(--serif); font-size:clamp(26px,3.5vw,42px); font-weight:800; line-height:1.1; margin-bottom:10px; }}
  .hero-sub {{ font-family:var(--sans); font-size:13px; color:#B8A89A; }}

  /* Filter bar */
  #filter-bar {{ background:#fff; border-bottom:1px solid var(--rule); position:sticky; top:0; z-index:40; }}
  #filter-inner {{ max-width:1320px; margin:0 auto; padding:0 24px; display:flex; align-items:center; gap:10px; min-height:48px; flex-wrap:wrap; }}
  .filter-label {{ font-family:var(--sans); font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.1em; color:#888; white-space:nowrap; }}
  .filter-tab {{ font-family:var(--sans); font-size:11px; font-weight:500; padding:3px 12px; border:1px solid var(--rule); border-radius:20px; cursor:pointer; background:#fff; color:#555; transition:all .15s; white-space:nowrap; }}
  .filter-tab:hover {{ border-color:var(--claret); color:var(--claret); }}
  .filter-tab.active {{ background:var(--claret); color:#fff; border-color:var(--claret); }}
  #tl-count {{ font-family:var(--sans); font-size:12px; color:var(--warm-gray); margin-left:auto; white-space:nowrap; }}
  #year-select {{ font-family:var(--sans); font-size:12px; padding:4px 10px; border:1px solid var(--rule); border-radius:3px; color:#333; background:#fff; cursor:pointer; }}

  /* Timeline */
  #main {{ max-width:860px; margin:0 auto; padding:32px 24px 80px; }}
  .year-group {{ margin-bottom:40px; }}
  .year-header {{ font-family:var(--serif); font-size:28px; font-weight:800; color:var(--black); border-bottom:3px solid var(--claret); padding-bottom:8px; margin-bottom:20px; }}
  .tl-line {{ position:relative; padding-left:28px; }}
  .tl-line::before {{ content:''; position:absolute; left:8px; top:0; bottom:0; width:2px; background:var(--rule); }}
  .tl-item {{ position:relative; margin-bottom:16px; }}
  .tl-dot {{ position:absolute; left:-24px; top:6px; width:12px; height:12px; border-radius:50%; border:2px solid #fff; box-shadow:0 0 0 2px var(--rule); }}
  .tl-dot.Completion    {{ background:#2d7a4f; box-shadow:0 0 0 2px #2d7a4f; }}
  .tl-dot.Award         {{ background:var(--claret); box-shadow:0 0 0 2px var(--claret); }}
  .tl-dot.Groundbreaking {{ background:#8a4a00; box-shadow:0 0 0 2px #8a4a00; }}
  .tl-dot.Announcement  {{ background:#2a5f8f; box-shadow:0 0 0 2px #2a5f8f; }}
  .tl-dot.News          {{ background:#888; box-shadow:0 0 0 2px #888; }}
  .tl-card {{ background:#fff; border:1px solid var(--rule); border-radius:2px; padding:14px 16px; transition:box-shadow .15s; }}
  .tl-card:hover {{ box-shadow:0 3px 12px rgba(0,0,0,.1); }}
  .tl-meta {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap; }}
  .tl-badge {{ font-family:var(--sans); font-size:9px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; padding:2px 8px; border-radius:10px; }}
  .tl-badge.Completion    {{ background:#e8f5ee; color:#2d7a4f; }}
  .tl-badge.Award         {{ background:#f2e8e8; color:var(--claret); }}
  .tl-badge.Groundbreaking {{ background:#fdf0e0; color:#8a4a00; }}
  .tl-badge.Announcement  {{ background:#e8f0f8; color:#2a5f8f; }}
  .tl-badge.News          {{ background:#f0f0f0; color:#555; }}
  .tl-geo {{ font-family:var(--sans); font-size:11px; color:var(--warm-gray); }}
  .tl-date {{ font-family:var(--sans); font-size:11px; color:var(--warm-gray); margin-left:auto; }}
  .tl-headline {{ font-family:var(--garamond); font-size:16px; line-height:1.35; color:var(--black); }}
  .tl-link {{ display:inline-block; font-family:var(--sans); font-size:11px; font-weight:600; color:var(--claret); margin-top:6px; }}
  .tl-link:hover {{ text-decoration:underline; }}

  /* Legend */
  .legend {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px; }}
  .legend-item {{ display:flex; align-items:center; gap:6px; font-family:var(--sans); font-size:11px; color:#555; }}
  .legend-dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}

  /* Empty */
  .empty {{ text-align:center; padding:60px 20px; font-family:var(--sans); font-size:14px; color:var(--warm-gray); }}

  /* Footer */
  #footer {{ background:var(--black); color:#8a7f72; font-family:var(--sans); font-size:12px; padding:24px; text-align:center; border-top:2px solid var(--claret); }}
  #footer a {{ color:#c8beb2; }}
  #footer a:hover {{ color:#fff; }}
  @media (max-width:600px) {{
    #filter-inner {{ gap:6px; }}
    .filter-tab {{ font-size:10px; padding:2px 8px; }}
  }}
  </style>
</head>
<body>

<!-- MASTHEAD -->
<header id="masthead" role="banner">
  <div id="masthead-inner">
    <a href="index.html" id="masthead-logo">FitOut<span>Post</span></a>
    <nav id="masthead-nav" role="navigation">
      <a href="index.html" class="mh-link">News</a>
      <a href="pipeline.html" class="mh-link">Pipeline</a>
      <a href="awards.html" class="mh-link">Awards</a>
      <a href="tenders.html" class="mh-link">Tenders</a>
      <a href="intelligence.html" class="mh-link">Intelligence</a>
      <a href="timeline.html" class="mh-link active">Timeline</a>
    </nav>
    <button id="masthead-search-btn" title="Search (/ or Ctrl+K)" aria-label="Search" style="background:none;border:none;color:#c8beb2;cursor:pointer;padding:0 12px;font-size:18px;line-height:1;transition:color .15s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='#c8beb2'">🔍</button>
  </div>
</header>

<!-- HERO -->
<div id="page-hero">
  <div id="page-hero-inner">
    <div class="hero-eyebrow">Industry Timeline · Global Intelligence</div>
    <h1>Milestones &amp; Events</h1>
    <div class="hero-sub" id="hero-count-sub">— milestones · chronological · all markets</div>
  </div>
</div>

<!-- FILTER BAR -->
<div id="filter-bar">
  <div id="filter-inner">
    <span class="filter-label">Type:</span>
    <div class="filter-tab active" data-type="All">All</div>
    <div class="filter-tab" data-type="Completion">Completion</div>
    <div class="filter-tab" data-type="Award">Award</div>
    <div class="filter-tab" data-type="Groundbreaking">Groundbreaking</div>
    <div class="filter-tab" data-type="Announcement">Announcement</div>
    <span class="filter-label" style="margin-left:8px;">Year:</span>
    <select id="year-select"><option value="All">All years</option></select>
    <span id="tl-count"></span>
  </div>
</div>

<!-- MAIN -->
<div id="main">
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#2d7a4f"></div>Completion</div>
    <div class="legend-item"><div class="legend-dot" style="background:#990033"></div>Contract Award</div>
    <div class="legend-item"><div class="legend-dot" style="background:#8a4a00"></div>Groundbreaking</div>
    <div class="legend-item"><div class="legend-dot" style="background:#2a5f8f"></div>Announcement</div>
    <div class="legend-item"><div class="legend-dot" style="background:#888"></div>News</div>
  </div>
  <div id="timeline-container"></div>
</div>

<!-- FOOTER -->
<footer id="footer">
  <p>© <span id="footer-year"></span> FitOut Post · Independent industry intelligence ·
    <a href="index.html">News</a> · <a href="awards.html">Awards</a> · <a href="pipeline.html">Pipeline</a> ·
    <a href="contact.html">Contact</a> · <a href="legal.html">Legal</a>
  </p>
</footer>

<script>
const slot = document.getElementById("timeline-data");
let DATA = [];
try {{ DATA = JSON.parse(slot.textContent).milestones || []; }} catch(e) {{}}

document.getElementById("footer-year").textContent = new Date().getFullYear();
document.getElementById("hero-count-sub").textContent =
  DATA.length + " milestones · chronological · all markets";

// Populate year dropdown
const years = [...new Set(DATA.map(m => m.year).filter(y => y !== "Unknown"))].sort((a,b)=>b-a);
const sel = document.getElementById("year-select");
years.forEach(y => {{ const o = document.createElement("option"); o.value=y; o.textContent=y; sel.appendChild(o); }});

let activeType = "All";
let activeYear = "All";

function esc(s) {{ return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }}

function filtered() {{
  return DATA.filter(m => {
    return (activeType==="All" || m.type===activeType) &&
           (activeYear==="All" || m.year===activeYear);
  });
}}

function render() {{
  const data = filtered();
  document.getElementById("tl-count").textContent = data.length + " milestone" + (data.length!==1?"s":"");

  const container = document.getElementById("timeline-container");
  if (!data.length) {{
    container.innerHTML = '<div class="empty">No milestones found for the selected filters.</div>';
    return;
  }}

  // Group by year
  const byYear = {{}};
  data.forEach(m => {{
    const y = m.year || "Unknown";
    if (!byYear[y]) byYear[y] = [];
    byYear[y].push(m);
  }});

  const sortedYears = Object.keys(byYear).sort((a,b) => b.localeCompare(a));
  container.innerHTML = sortedYears.map(year => {{
    const items = byYear[year].map(m => {{
      const geo = [m.country, m.continent].filter(Boolean).join(" · ");
      return `<div class="tl-item">
        <div class="tl-dot ${{m.type}}"></div>
        <div class="tl-card">
          <div class="tl-meta">
            <span class="tl-badge ${{m.type}}">${{m.type}}</span>
            ${{geo ? `<span class="tl-geo">${{esc(geo)}}</span>` : ""}}
            ${{m.date ? `<span class="tl-date">${{esc(m.date)}}</span>` : ""}}
          </div>
          <div class="tl-headline">${{esc(m.headline)}}</div>
          ${{m.url ? `<a class="tl-link" href="${{esc(m.url)}}" target="_blank" rel="noopener">Read story →</a>` : ""}}
        </div>
      </div>`;
    }}).join("");
    return `<div class="year-group"><div class="year-header">${{year}}</div><div class="tl-line">${{items}}</div></div>`;
  }}).join("");
}}

render();

document.querySelectorAll(".filter-tab").forEach(tab => {{
  tab.addEventListener("click", () => {{
    document.querySelectorAll(".filter-tab").forEach(t=>t.classList.remove("active"));
    tab.classList.add("active");
    activeType = tab.dataset.type;
    render();
  }});
}});
sel.addEventListener("change", () => {{ activeYear = sel.value; render(); }});
</script>
<script src="search.js"></script>
<script src="cookie-consent.js"></script>
</body>
</html>"""

def build():
    milestones = load_milestones()
    data = {
        "total":      len(milestones),
        "generated":  datetime.now(timezone.utc).isoformat(),
        "milestones": milestones,
    }
    j = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    j = j.replace("</", "<\\/")
    html = HTML.replace("{TIMELINE_JSON}", j)
    TEMPLATE_PATH.write_text(html, encoding="utf-8")
    print(f"✅  timeline.html — {len(milestones)} milestones, {TEMPLATE_PATH.stat().st_size//1024} KB")

if __name__ == "__main__":
    build()
