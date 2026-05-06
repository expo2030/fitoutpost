#!/usr/bin/env python3
"""
FitOut Post — Keyword Alert Digest Generator (P3-5)
----------------------------------------------------
Runs after the daily fetch pipeline.
Reads members.json (keyword_alerts saved queries) and today's news/tenders/pipeline.
Generates per-member HTML digest emails and writes them to alerts_outbox/

Usage:
    python3 alert_digest.py
    python3 alert_digest.py --dry-run       # Preview matches without writing files
    python3 alert_digest.py --member EMAIL  # Single member only

Output:
    alerts_outbox/YYYY-MM-DD/  — one HTML file per member with matches
    alert_log.json             — run log with match counts
"""

import json, re, sys, argparse, html
from pathlib import Path
from datetime import datetime, timezone

BASE      = Path(__file__).parent
DATA_DIR  = BASE
OUTBOX    = BASE / "alerts_outbox"
LOG_FILE  = BASE / "alert_log.json"

def load_json(path, default=None):
    try:
        return json.loads(path.read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []

def match_keywords(keywords: list[str], text: str) -> list[str]:
    """Return list of matched keywords (case-insensitive)."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]

def item_text(item: dict) -> str:
    """Flatten all text fields of a news/tender/pipeline item for matching."""
    return " ".join(str(v) for v in item.values() if isinstance(v, str))

def signal_label(item: dict) -> str:
    s = item.get("signal", item.get("stage", ""))
    labels = {
        "award": "Award", "tender": "Tender", "pipeline": "Pipeline",
        "progress": "Progress", "news": "News",
        "planning": "Planning", "design": "Design",
        "pre-tender": "Pre-Tender", "construction": "Construction"
    }
    return labels.get(s, s.capitalize() if s else "Article")

def render_item_html(item: dict, source_type: str, matched_kws: list[str]) -> str:
    title = html.escape(item.get("title", "(No title)"))
    link  = item.get("link") or item.get("source_url", "#")
    country   = html.escape(item.get("country", ""))
    continent = html.escape(item.get("continent", ""))
    geo_str   = f"{country} · {continent}" if country else continent
    pub_date  = item.get("pubDate", item.get("published", ""))[:10]
    signal    = signal_label(item)
    kw_html   = " ".join(
        f'<span style="background:#B8860B;color:#fff;font-size:10px;padding:1px 7px;font-weight:700;">'
        f'{html.escape(kw)}</span>' for kw in matched_kws
    )

    return f"""
    <tr>
      <td style="padding:14px 16px;border-bottom:1px solid #EDE3DA;vertical-align:top;">
        <div style="font-size:10px;color:#990033;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">
          {source_type} · {signal} · {geo_str} · {pub_date}
        </div>
        <div style="font-size:15px;font-weight:600;margin-bottom:6px;">
          <a href="{link}" style="color:#1a1a1a;text-decoration:none;">{title}</a>
        </div>
        <div>{kw_html}</div>
      </td>
    </tr>"""

def render_email_html(member: dict, sections: dict, today_str: str) -> str:
    name    = html.escape(member.get("name", "Member"))
    email   = html.escape(member.get("email", ""))
    alerts  = member.get("keyword_alerts", [])
    kw_list = ", ".join(html.escape(kw) for kw in alerts)
    total   = sum(len(rows) for rows in sections.values())

    section_html = ""
    for label, rows in sections.items():
        if not rows:
            continue
        section_html += f"""
        <tr><td style="background:#F2DFCE;padding:10px 16px 6px;">
          <span style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;color:#66605A;">{html.escape(label)}</span>
        </td></tr>"""
        section_html += "".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width"><title>FitOut Post Alert — {today_str}</title></head>
<body style="margin:0;padding:0;background:#FFF1E5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;margin:0 auto;">

  <!-- Header -->
  <tr><td style="background:#1a1a1a;padding:24px 32px;border-bottom:4px solid #990033;">
    <span style="font-family:Georgia,serif;font-size:22px;font-weight:700;color:#fff;letter-spacing:0.5px;">FitOut Post</span>
    <span style="display:block;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#9A8A80;margin-top:4px;">Keyword Alert · {today_str}</span>
  </td></tr>

  <!-- Summary bar -->
  <tr><td style="background:#990033;padding:12px 32px;">
    <span style="font-size:13px;color:#fff;font-weight:600;">{total} match{'es' if total != 1 else ''} today</span>
    <span style="font-size:12px;color:rgba(255,255,255,.7);margin-left:12px;">for: {kw_list}</span>
  </td></tr>

  <!-- Intro -->
  <tr><td style="padding:20px 32px 10px;background:#fff;">
    <p style="margin:0;font-size:14px;color:#66605A;line-height:1.6;">
      Hi {name}, here are today's FitOut Post articles, tenders and pipeline items matching your saved keywords.
    </p>
  </td></tr>

  <!-- Results table -->
  <tr><td style="background:#fff;padding:0 16px 24px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      {section_html if section_html else '<tr><td style="padding:24px 16px;color:#9A948E;font-size:14px;">No matches found today for your saved keywords.</td></tr>'}
    </table>
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#1a1a1a;padding:20px 32px;border-top:1px solid #333;">
    <p style="margin:0;font-size:11px;color:#6A6060;line-height:1.7;">
      You're receiving this because you saved keyword alerts on FitOut Post.<br>
      <a href="https://fitoutpost.com/register.html" style="color:#9A8A80;">Manage your alerts</a> &nbsp;·&nbsp;
      <a href="https://fitoutpost.com/register.html?unsubscribe=alerts" style="color:#9A8A80;">Unsubscribe from alerts</a><br>
      © {datetime.now(timezone.utc).year} FitOut Post · intelligence@fitoutpost.com
    </p>
  </td></tr>

</table>
</body>
</html>"""

def run(dry_run: bool = False, target_email: str = None):
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")

    # Load data sources
    news     = load_json(DATA_DIR / "news.json")
    tenders  = load_json(DATA_DIR / "tenders.json")
    pipeline = load_json(DATA_DIR / "pipeline.json")
    members  = load_json(DATA_DIR / "members.json")

    if not members:
        print("⚠  No members.json or empty — nothing to do.")
        return

    outbox_day = OUTBOX / today_str
    if not dry_run:
        outbox_day.mkdir(parents=True, exist_ok=True)

    log_entries = []
    total_digests = 0

    for member in members:
        email = member.get("email", "")
        if target_email and email != target_email:
            continue

        alerts = member.get("keyword_alerts", [])
        if not alerts:
            continue

        # Match across all three data sources
        news_rows     = []
        tender_rows   = []
        pipeline_rows = []

        for item in news:
            matched = match_keywords(alerts, item_text(item))
            if matched:
                news_rows.append(render_item_html(item, "News", matched))

        for item in tenders:
            matched = match_keywords(alerts, item_text(item))
            if matched:
                tender_rows.append(render_item_html(item, "Tender", matched))

        for item in pipeline:
            matched = match_keywords(alerts, item_text(item))
            if matched:
                pipeline_rows.append(render_item_html(item, "Pipeline", matched))

        total_matches = len(news_rows) + len(tender_rows) + len(pipeline_rows)

        log_entries.append({
            "email": email,
            "date": today_str,
            "alerts": alerts,
            "matches": {"news": len(news_rows), "tenders": len(tender_rows), "pipeline": len(pipeline_rows)},
            "total": total_matches
        })

        if dry_run:
            print(f"  [dry-run] {email}: {total_matches} matches "
                  f"(news={len(news_rows)}, tenders={len(tender_rows)}, pipeline={len(pipeline_rows)})")
            continue

        # Skip if zero matches (don't send empty digest)
        if total_matches == 0:
            print(f"  ⟳  {email}: 0 matches — digest skipped")
            continue

        # Render and write
        sections = {
            "News": news_rows,
            "Tenders": tender_rows,
            "Pipeline": pipeline_rows
        }
        html_content = render_email_html(member, sections, today_str)
        safe_email = re.sub(r"[^a-zA-Z0-9._-]", "_", email)
        out_path = outbox_day / f"{safe_email}.html"
        out_path.write_text(html_content, "utf-8")
        total_digests += 1
        print(f"  ✅  {email}: {total_matches} matches → {out_path.name}")

    # Write log
    if not dry_run:
        existing_log = load_json(LOG_FILE, [])
        existing_log.append({
            "run_at": today.isoformat(),
            "dry_run": dry_run,
            "members_processed": len(log_entries),
            "digests_written": total_digests,
            "entries": log_entries
        })
        LOG_FILE.write_text(json.dumps(existing_log, ensure_ascii=False, indent=2), "utf-8")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done — {total_digests} digest(s) written to {outbox_day}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FitOut Post keyword alert digest generator")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without writing files")
    parser.add_argument("--member", metavar="EMAIL", help="Process a single member only")
    args = parser.parse_args()
    run(dry_run=args.dry_run, target_email=args.member)
