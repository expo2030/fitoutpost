#!/usr/bin/env python3
"""Patch build_country_pages.py: replace stale masthead/nav/footer with canonical versions.
Country pages are in countries/ subdirectory so links use ../ prefix."""
import re
from pathlib import Path

src = Path("build_country_pages.py").read_text(encoding="utf-8")

# ── 1. CANONICAL MASTHEAD CSS (replaces old masthead + search CSS block) ─────
OLD_MH_CSS = re.compile(
    r"  #masthead\{\{.*?\.mh-util-sep\{\{[^}]+\}\}\n",
    re.DOTALL
)
NEW_MH_CSS = """\
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
"""

n = len(OLD_MH_CSS.findall(src))
src = OLD_MH_CSS.sub(NEW_MH_CSS, src)
print(f"Masthead CSS: replaced {n} occurrence(s)")

# ── 2. CANONICAL FOOTER CSS (replaces minimal #footer / #footer a block) ─────
OLD_FOOTER_CSS = re.compile(
    r"  #footer\{\{background[^}]+\}\}\n  #footer a\{\{[^}]+\}\}\n",
    re.DOTALL
)
NEW_FOOTER_CSS = """\
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
"""
n = len(OLD_FOOTER_CSS.findall(src))
src = OLD_FOOTER_CSS.sub(NEW_FOOTER_CSS, src)
print(f"Footer CSS: replaced {n} occurrence(s)")

# ── 3. CANONICAL MASTHEAD HTML (replaces old header block with search) ────────
OLD_MASTHEAD_HTML = re.compile(
    r'<header id="masthead" role="banner">.*?</header>\n',
    re.DOTALL
)
NEW_MASTHEAD_HTML = """\
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
"""
n = len(OLD_MASTHEAD_HTML.findall(src))
src = OLD_MASTHEAD_HTML.sub(NEW_MASTHEAD_HTML, src)
print(f"Masthead HTML: replaced {n} occurrence(s)")

# ── 4. CANONICAL NAV HTML (canonical order, correct labels, ../ prefix) ──────
OLD_NAV_HTML = re.compile(
    r'<nav id="product-nav"[^>]*>.*?</nav>\n',
    re.DOTALL
)
NEW_NAV_HTML = """\
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
"""
n = len(OLD_NAV_HTML.findall(src))
src = OLD_NAV_HTML.sub(NEW_NAV_HTML, src)
print(f"Nav HTML: replaced {n} occurrence(s)")

# ── 5. CANONICAL FOOTER HTML (replaces minimal footer in both templates) ──────
OLD_FOOTER_HTML = re.compile(
    r'<footer id="footer">.*?</footer>\n',
    re.DOTALL
)
NEW_FOOTER_HTML = """\
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
"""
n = len(OLD_FOOTER_HTML.findall(src))
src = OLD_FOOTER_HTML.sub(NEW_FOOTER_HTML, src)
print(f"Footer HTML: replaced {n} occurrence(s)")

# ── 6. Replace old footer-year JS (fy span) with footer-year span ─────────────
src = src.replace(
    '<script>document.getElementById("fy").textContent=new Date().getFullYear();</script>',
    '<script>document.getElementById("footer-year").textContent=new Date().getFullYear();</script>'
)
src = src.replace(
    "document.getElementById('fy').textContent = new Date().getFullYear();",
    "document.getElementById('footer-year').textContent = new Date().getFullYear();"
)

# ── 7. Remove search.js script tags ──────────────────────────────────────────
src = src.replace('<script src="../search.js"></script>\n', '')
src = src.replace('<script src="../search.js"></script>', '')

# ── 8. Remove masthead-search-btn ────────────────────────────────────────────
src = re.sub(r'\n?<button id="masthead-search-btn"[^>]*>[^<]*</button>\n?', '\n', src)

Path("build_country_pages.py").write_text(src, encoding="utf-8")
print("\n✅  build_country_pages.py patched")
