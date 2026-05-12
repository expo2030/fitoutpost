#!/usr/bin/env python3
"""
One-time script: replace hardcoded masthead, product-nav, and footer blocks
in every template with <!--PARTIAL:X--> slot comments.

Safe to re-run — if slots are already present it skips that file.
"""
import re, sys
from pathlib import Path

BASE = Path(__file__).parent

TEMPLATES = [
    "_template.html",
    "_static_template.html",
    "_awards_template.html",
    "_intelligence_template.html",
    "_pipeline_template.html",
    "_tenders_template.html",
    "_weekly_template.html",
]

# Regex patterns to match the three shared blocks regardless of minor whitespace/attr differences.
# Each pattern anchors on the stable outer tag + id.

MASTHEAD_RE = re.compile(
    r'<header id="masthead"[^>]*>.*?</header>',
    re.DOTALL
)

# Product nav only (id="product-nav") — not the continent/region nav
PRODUCT_NAV_RE = re.compile(
    r'<!-- [╔═]+ PRODUCT NAV[^\n]*\n<nav id="product-nav"[^>]*>.*?</nav>',
    re.DOTALL
)
PRODUCT_NAV_FALLBACK_RE = re.compile(
    r'<nav id="product-nav"[^>]*>.*?</nav>',
    re.DOTALL
)

FOOTER_RE = re.compile(
    r'<footer id="footer"[^>]*>.*?</footer>',
    re.DOTALL
)

changed = []
skipped = []

for name in TEMPLATES:
    path = BASE / name
    if not path.exists():
        print(f"⚠  Not found: {name}")
        continue

    html = path.read_text(encoding="utf-8")

    # Skip if already slotted
    if "<!--PARTIAL:MASTHEAD-->" in html:
        skipped.append(name)
        continue

    original = html

    # 1. Masthead
    html, n = MASTHEAD_RE.subn("<!--PARTIAL:MASTHEAD-->", html, count=1)
    if n == 0:
        print(f"⚠  {name}: masthead not matched")

    # 2. Product nav (try comment-prefixed first, fall back to bare tag)
    html, n = PRODUCT_NAV_RE.subn("<!--PARTIAL:NAV-->", html, count=1)
    if n == 0:
        html, n = PRODUCT_NAV_FALLBACK_RE.subn("<!--PARTIAL:NAV-->", html, count=1)
    if n == 0:
        print(f"⚠  {name}: product-nav not matched")

    # 3. Footer
    html, n = FOOTER_RE.subn("<!--PARTIAL:FOOTER-->", html, count=1)
    if n == 0:
        print(f"⚠  {name}: footer not matched")

    if html != original:
        path.write_text(html, encoding="utf-8")
        changed.append(name)
        print(f"✅  {name} — slots injected")
    else:
        print(f"—  {name} — no changes")

if skipped:
    print(f"\nAlready slotted (skipped): {', '.join(skipped)}")
print(f"\nDone. {len(changed)} file(s) updated.")
