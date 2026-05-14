#!/usr/bin/env python3
"""
FitOut Post — Newsletter Dispatcher

Reads newsletter_latest.html and sends it to every member in
newsletter_members.json via the Resend API.

Usage
-----
    python send_newsletter.py              # send to all members
    python send_newsletter.py --dry-run    # list recipients, don't send

Requires
--------
    RESEND_API_KEY env var (https://resend.com — free: 3000 emails/month)

To set up:
  1. Create an account at resend.com
  2. Verify your sending domain (fitoutpost.com) in Resend's DNS settings
  3. Generate an API key and add it as RESEND_API_KEY in GitHub Secrets
"""

import json
import os
import sys
import requests
from pathlib import Path

BASE = Path(__file__).parent

RESEND_URL   = "https://api.resend.com/emails"
FROM_ADDRESS = "FitOut Post <hello@fitoutpost.com>"
REPLY_TO     = "hello@fitoutpost.com"


def load_members() -> list[dict]:
    path = BASE / "newsletter_members.json"
    if not path.exists():
        sys.exit("❌  newsletter_members.json not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    members = [m for m in data.get("members", []) if m.get("email")]
    if not members:
        sys.exit("❌  No members in newsletter_members.json")
    return members


def load_html() -> str:
    path = BASE / "newsletter_latest.html"
    if not path.exists():
        sys.exit("❌  newsletter_latest.html not found — run generate_newsletter.py first")
    return path.read_text(encoding="utf-8")


def extract_subject(html: str) -> str:
    """Pull the edition label from the <title> tag for the email subject."""
    import re
    m = re.search(r"<title>FitOut Post Weekly.*?—\s*(.+?)</title>", html)
    if m:
        return f"FitOut Post Weekly — {m.group(1).strip()}"
    return "FitOut Post — Weekly Roundup"


def send_one(api_key: str, to_email: str, to_name: str,
             subject: str, html: str) -> bool:
    personalised = html.replace(
        "You receive this because you are a FitOut Post member.",
        f"You receive this at {to_email} because you are a FitOut Post member."
    )
    resp = requests.post(
        RESEND_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from":    FROM_ADDRESS,
            "to":      [to_email],
            "reply_to": REPLY_TO,
            "subject": subject,
            "html":    personalised,
        },
        timeout=30,
    )
    if resp.ok:
        return True
    print(f"   ⚠️  {to_email} — HTTP {resp.status_code}: {resp.text[:120]}")
    return False


def main():
    dry_run = "--dry-run" in sys.argv
    api_key = os.environ.get("RESEND_API_KEY", "")

    members = load_members()
    html    = load_html()
    subject = extract_subject(html)

    print(f"📬  Subject: {subject}")
    print(f"👥  Recipients: {len(members)} member(s)")

    if dry_run:
        print("\n─── DRY RUN — no emails sent ───────────────────────────────────────")
        for m in members:
            print(f"   → {m['email']} ({m.get('name','—')})")
        return

    if not api_key:
        sys.exit("❌  RESEND_API_KEY not set — cannot send emails")

    sent = failed = 0
    for m in members:
        to_email = m["email"]
        to_name  = m.get("name", "")
        print(f"   Sending → {to_email} …", end=" ", flush=True)
        ok = send_one(api_key, to_email, to_name, subject, html)
        if ok:
            print("✓")
            sent += 1
        else:
            failed += 1

    print(f"\n✅  Sent: {sent}  |  Failed: {failed}")


if __name__ == "__main__":
    main()
