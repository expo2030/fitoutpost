#!/usr/bin/env python3
"""
FitOut Post — Weekly Newsletter Generator

Reads the latest week from weekly.json, calls Claude Haiku to write an
editorial summary, then renders a full HTML email saved to newsletter_latest.html.

Usage
-----
    python generate_newsletter.py              # generate from latest week
    python generate_newsletter.py --dry-run    # print prompt + skip API call

Requires
--------
    ANTHROPIC_API_KEY env var
"""

import json
import os
import sys
import textwrap
import requests
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent

SITE_URL      = "https://fitoutpost.com"
WEEKLY_URL    = f"{SITE_URL}/weekly.html"
UNSUBSCRIBE   = f"mailto:hello@fitoutpost.com?subject=Unsubscribe"
FROM_EMAIL    = "hello@fitoutpost.com"
BRAND_CLARET  = "#990033"
BRAND_BLACK   = "#1a1a1a"
BRAND_SALMON  = "#FFF1E5"
BRAND_WARMGRAY= "#66605A"

CLAUDE_MODEL  = "claude-haiku-4-5-20251001"
MAX_TOKENS    = 600

EDITORIAL_SYSTEM = """You are the editor of FitOut Post, a specialist intelligence service
covering the global interior fit-out industry. Your voice is authoritative, concise,
and market-facing — like the FT or Economist but for a niche B2B audience.
Write in British English. Avoid clichés. Never start sentences with "This week..."."""

EDITORIAL_PROMPT = """\
Write a 220–260 word editorial briefing for FitOut Post members. This is the opening
section of the Monday weekly newsletter for the week {label}.

Below is the week's signal data across four categories. Use it to identify the most
significant themes, geographical patterns, and market implications — but do NOT simply
list the items. Write as an editor who has read everything and is distilling what matters.

Structure:
- Para 1 (60–70 words): Lead with the dominant theme or geographical story of the week.
- Para 2 (70–80 words): Pipeline and development activity — where is money moving?
- Para 3 (60–70 words): Procurement signals (tenders + awards if any), plus any notable
  contract news from the news feed.
- Close (30–40 words): A forward-looking observation or question facing the industry.

--- SIGNAL DATA ---
NEWS ({news_total} articles):
{news_headlines}

PIPELINE ({pipeline_total} projects — top by region):
{pipeline_items}

TENDERS ({tenders_total} active):
{tender_items}

AWARDS ({awards_total} contract signals):
{award_items}
---

Return ONLY the editorial text — four paragraphs, no headers, no bullet points."""


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_latest_week() -> dict:
    path = BASE / "weekly.json"
    if not path.exists():
        sys.exit("❌  weekly.json not found — run fetch_weekly.py first")
    data = json.loads(path.read_text(encoding="utf-8"))
    weeks = data.get("weeks", [])
    if not weeks:
        sys.exit("❌  weekly.json has no weeks — run fetch_weekly.py first")
    return weeks[0]


def items_from_groups(groups, key="items", title_field="headline", max_per_group=4,
                       extra_fields=None):
    """Flatten group list to bullet lines for the prompt."""
    lines = []
    for g in groups:
        continent = g.get("continent", "")
        for item in g.get(key, g.get("articles", []))[:max_per_group]:
            title = item.get(title_field) or item.get("title") or item.get("headline") or ""
            country = item.get("country", "")
            extra = ""
            if extra_fields:
                parts = [str(item.get(f, "")) for f in extra_fields if item.get(f)]
                extra = f" [{', '.join(parts)}]" if parts else ""
            lines.append(f"  • [{country or continent}] {title[:90]}{extra}")
    return "\n".join(lines) if lines else "  (none)"


# ── Claude call ───────────────────────────────────────────────────────────────

def call_claude(prompt: str, system: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        sys.exit("❌  ANTHROPIC_API_KEY not set")

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()


# ── HTML email builder ────────────────────────────────────────────────────────

def html_email(week: dict, editorial: str) -> str:
    label       = week.get("label", "")
    news_total  = week.get("news_total", 0)
    pl_total    = week.get("pipeline_total", 0)
    td_total    = week.get("tenders_total", 0)
    aw_total    = week.get("awards_total", 0)
    grand_total = week.get("total", 0)
    generated   = week.get("generated", "")
    gen_date    = ""
    if generated:
        try:
            gen_date = datetime.fromisoformat(generated.replace("Z","+00:00")) \
                               .strftime("%-d %B %Y")
        except Exception:
            gen_date = generated[:10]

    # Format editorial paragraphs as <p> tags
    paras = [p.strip() for p in editorial.split("\n\n") if p.strip()]
    editorial_html = "\n".join(f'<p style="margin:0 0 16px 0;line-height:1.65;">{p}</p>'
                                for p in paras)

    # Top news items for the "this week" quick-scan block
    news_rows = ""
    for g in week.get("groups", []):
        for a in g.get("items", g.get("articles", []))[:3]:
            headline = a.get("headline") or a.get("title") or ""
            country  = a.get("country") or g.get("continent") or ""
            url      = a.get("url", "#")
            news_rows += f"""
        <tr>
          <td style="padding:7px 12px;border-bottom:1px solid #EDE3DA;font-size:11px;
                     color:{BRAND_WARMGRAY};white-space:nowrap;vertical-align:top;">{country}</td>
          <td style="padding:7px 12px;border-bottom:1px solid #EDE3DA;font-size:13px;
                     vertical-align:top;">
            <a href="{url}" style="color:{BRAND_BLACK};text-decoration:none;"
               target="_blank">{headline[:95]}{'…' if len(headline)>95 else ''}</a>
          </td>
        </tr>"""

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>FitOut Post Weekly — {label}</title>
</head>
<body style="margin:0;padding:0;background:#F5EDE4;font-family:Georgia,'Times New Roman',serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#F5EDE4;">
<tr><td align="center" style="padding:32px 16px;">

  <table width="600" cellpadding="0" cellspacing="0"
         style="max-width:600px;width:100%;background:#ffffff;border:1px solid #DDD0C4;">

    <!-- ── MASTHEAD ── -->
    <tr>
      <td style="background:{BRAND_BLACK};padding:24px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td>
              <div style="display:inline-block;background:{BRAND_CLARET};
                          padding:6px 10px;font-size:18px;font-weight:700;
                          color:#fff;letter-spacing:1px;font-family:Georgia,serif;">FOP</div>
              <span style="font-size:20px;font-weight:700;color:#fff;
                           font-family:Georgia,serif;vertical-align:middle;
                           margin-left:10px;">FitOut Post</span>
            </td>
            <td align="right" style="font-size:10px;color:rgba(255,255,255,.45);
                                      letter-spacing:1.5px;text-transform:uppercase;
                                      vertical-align:middle;">Weekly Roundup</td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- ── EDITION HEADER ── -->
    <tr>
      <td style="background:{BRAND_CLARET};padding:14px 32px;">
        <span style="font-size:11px;letter-spacing:2px;text-transform:uppercase;
                     color:rgba(255,255,255,.7);">Edition</span><br>
        <span style="font-size:22px;font-weight:700;color:#fff;
                     font-family:Georgia,serif;">{label}</span>
        <span style="font-size:11px;color:rgba(255,255,255,.6);
                     margin-left:12px;">{gen_date}</span>
      </td>
    </tr>

    <!-- ── SIGNAL SUMMARY STRIP ── -->
    <tr>
      <td style="background:#FAF5F0;border-bottom:1px solid #DDD0C4;padding:12px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td align="center" style="font-size:11px;color:{BRAND_WARMGRAY};">
              <strong style="color:{BRAND_BLACK};font-size:16px;">{grand_total}</strong><br>
              signals this week
            </td>
            <td align="center" style="font-size:11px;color:{BRAND_WARMGRAY};">
              <strong style="color:{BRAND_BLACK};font-size:16px;">{news_total}</strong><br>
              news articles
            </td>
            <td align="center" style="font-size:11px;color:{BRAND_WARMGRAY};">
              <strong style="color:{BRAND_BLACK};font-size:16px;">{pl_total}</strong><br>
              pipeline projects
            </td>
            <td align="center" style="font-size:11px;color:{BRAND_WARMGRAY};">
              <strong style="color:{BRAND_BLACK};font-size:16px;">{td_total}</strong><br>
              tenders
            </td>
            <td align="center" style="font-size:11px;color:{BRAND_WARMGRAY};">
              <strong style="color:{BRAND_BLACK};font-size:16px;">{aw_total}</strong><br>
              awards
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- ── EDITORIAL ── -->
    <tr>
      <td style="padding:32px 32px 8px 32px;">
        <p style="margin:0 0 20px 0;font-size:10px;letter-spacing:2px;
                   text-transform:uppercase;color:{BRAND_WARMGRAY};">Editor's Brief</p>
        <div style="font-size:15px;color:{BRAND_BLACK};line-height:1.65;">
          {editorial_html}
        </div>
      </td>
    </tr>

    <!-- ── NEWS DIGEST ── -->
    <tr>
      <td style="padding:0 32px 8px 32px;">
        <p style="margin:24px 0 12px 0;font-size:10px;letter-spacing:2px;
                   text-transform:uppercase;color:{BRAND_WARMGRAY};
                   border-top:1px solid #EDE3DA;padding-top:16px;">
          News headlines this week</p>
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border:1px solid #EDE3DA;">
          {news_rows}
        </table>
      </td>
    </tr>

    <!-- ── CTA ── -->
    <tr>
      <td style="padding:28px 32px 32px 32px;text-align:center;">
        <a href="{WEEKLY_URL}"
           style="display:inline-block;background:{BRAND_BLACK};color:#fff;
                  padding:12px 32px;font-size:13px;font-weight:600;
                  text-decoration:none;letter-spacing:.4px;">
          Read the full roundup →
        </a>
        <p style="margin:16px 0 0 0;font-size:11px;color:{BRAND_WARMGRAY};">
          Pipeline, tenders, and contract awards are available in the members area.
        </p>
      </td>
    </tr>

    <!-- ── FOOTER ── -->
    <tr>
      <td style="background:{BRAND_BLACK};padding:20px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="font-size:11px;color:rgba(255,255,255,.4);">
              © {datetime.now(timezone.utc).year} FitOut Post · {SITE_URL}<br>
              You receive this because you are a FitOut Post member.
            </td>
            <td align="right" style="font-size:11px;">
              <a href="{UNSUBSCRIBE}" style="color:rgba(255,255,255,.4);">Unsubscribe</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>

  </table>
</td></tr>
</table>

</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    week    = load_latest_week()

    news_text     = items_from_groups(week.get("groups", []),
                                      title_field="headline", max_per_group=5)
    pipeline_text = items_from_groups(week.get("pipeline_groups", []),
                                      title_field="title", max_per_group=3,
                                      extra_fields=["sector"])
    tender_text   = items_from_groups(week.get("tenders_groups", []),
                                      title_field="title", max_per_group=4,
                                      extra_fields=["issuer","deadline"])
    award_text    = items_from_groups(week.get("awards_groups", []),
                                      title_field="headline", max_per_group=4)

    prompt = EDITORIAL_PROMPT.format(
        label         = week["label"],
        news_total    = week.get("news_total", 0),
        news_headlines= news_text,
        pipeline_total= week.get("pipeline_total", 0),
        pipeline_items= pipeline_text,
        tenders_total = week.get("tenders_total", 0),
        tender_items  = tender_text,
        awards_total  = week.get("awards_total", 0),
        award_items   = award_text,
    )

    if dry_run:
        print("─── PROMPT ─────────────────────────────────────────────────────────")
        print(prompt)
        print("\n─── DRY RUN — skipping Claude API call ─────────────────────────────")
        editorial = "[Editorial would be written here by Claude Haiku]"
    else:
        print(f"✍️   Calling {CLAUDE_MODEL} to write editorial…")
        editorial = call_claude(prompt, EDITORIAL_SYSTEM)
        print(f"✅  Editorial written ({len(editorial.split())} words)")

    html = html_email(week, editorial)
    out  = BASE / "newsletter_latest.html"
    out.write_text(html, encoding="utf-8")
    print(f"📧  Newsletter saved → {out.name}")
    if not dry_run:
        print(f"    Week:    {week['label']}")
        print(f"    Signals: {week.get('total',0)}")


if __name__ == "__main__":
    main()
