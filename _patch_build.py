#!/usr/bin/env python3
"""Patch build.py: insert inject_partials() calls after each _inject_site_updated() call,
and add _load_partials() call at the start of each top-level build invocation."""
from pathlib import Path

bp = Path("build.py")
txt = bp.read_text(encoding="utf-8")

# Map of active_nav value per site_updated call site
# We identify each by the unique surrounding context
replacements = [
    # News (builds news.html / site.html)
    (
        "    built = _inject_site_updated(built, _compute_site_updated())\n    for out in NEWS_OUTPUTS:",
        "    built = inject_partials(built, \"News\")\n    built = _inject_site_updated(built, _compute_site_updated())\n    for out in NEWS_OUTPUTS:"
    ),
    # Intelligence
    (
        "    built = _inject_site_updated(built, _compute_site_updated())\n    IN_OUTPUT.write_text",
        "    built = inject_partials(built, \"Intelligence\")\n    built = _inject_site_updated(built, _compute_site_updated())\n    IN_OUTPUT.write_text"
    ),
    # Weekly
    (
        "    built = _inject_site_updated(built, _compute_site_updated())\n    WR_OUTPUT.write_text",
        "    built = inject_partials(built, \"Roundup\")\n    built = _inject_site_updated(built, _compute_site_updated())\n    WR_OUTPUT.write_text"
    ),
    # Tenders
    (
        "    built = _inject_site_updated(built, _compute_site_updated())\n    TD_OUTPUT.write_text",
        "    built = inject_partials(built, \"Tenders\")\n    built = _inject_site_updated(built, _compute_site_updated())\n    TD_OUTPUT.write_text"
    ),
    # Pipeline (no _embed_json, has its own inline build)
    (
        "    built = _inject_site_updated(built, _compute_site_updated())\n    PL_OUTPUT.write_text",
        "    built = inject_partials(built, \"Pipeline\")\n    built = _inject_site_updated(built, _compute_site_updated())\n    PL_OUTPUT.write_text"
    ),
    # Awards
    (
        "    built = _inject_site_updated(built, _compute_site_updated())\n    AW_OUTPUT.write_text",
        "    built = inject_partials(built, \"Awards\")\n    built = _inject_site_updated(built, _compute_site_updated())\n    AW_OUTPUT.write_text"
    ),
]

for old, new in replacements:
    if old in txt:
        txt = txt.replace(old, new, 1)
        print(f"✅  Patched: {old[:60].strip()!r}")
    else:
        print(f"⚠  NOT FOUND: {old[:60].strip()!r}")

bp.write_text(txt, encoding="utf-8")
print("\nDone.")
