#!/usr/bin/env python3
"""
FitOut Post — Algorithm Quality Audit Script
Runs all 201 feeds, saves partial results every 50 feeds,
then produces a quality/coverage report.

Differences from fetch_news.py:
- 0.2 s inter-feed delay (was 0.6 s) — acceptable for a one-off audit
- Saves partial news_audit.json every 50 feeds (survives timeout)
- Prints a detailed quality report at the end

Usage:
    python audit_fetch.py
"""

import json
import re
import time
import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, quote

import feedparser
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s")
log = logging.getLogger("audit")

# ─── Geo reference (same as fetch_news.py) ─────────────────────────────────

CONTINENTS: dict[str, list[str]] = {
    "Europe": [
        "United Kingdom", "England", "Scotland", "Wales", "Northern Ireland",
        "Germany", "France", "Spain", "Italy", "Netherlands", "Belgium",
        "Switzerland", "Austria", "Sweden", "Norway", "Denmark", "Finland",
        "Poland", "Czech Republic", "Portugal", "Ireland", "Greece", "Hungary",
        "Romania", "Bulgaria", "Croatia", "Serbia", "Slovakia", "Slovenia",
        "Luxembourg", "Malta", "Cyprus", "Estonia", "Latvia", "Lithuania",
        "Albania", "Bosnia", "Montenegro", "North Macedonia", "Kosovo",
        "Moldova", "Ukraine", "Russia",
    ],
    "Middle East": [
        "United Arab Emirates", "UAE", "Dubai", "Abu Dhabi", "Saudi Arabia",
        "Qatar", "Kuwait", "Bahrain", "Oman", "Israel", "Jordan", "Lebanon",
        "Egypt", "Iraq", "Iran", "Turkey",
    ],
    "Asia Pacific": [
        "China", "Japan", "South Korea", "India", "Singapore", "Hong Kong",
        "Taiwan", "Thailand", "Malaysia", "Indonesia", "Philippines", "Vietnam",
        "Bangladesh", "Pakistan", "Sri Lanka", "Myanmar", "Cambodia",
        "Mongolia", "Nepal", "Brunei",
    ],
    "Oceania": [
        "Australia", "New Zealand", "Papua New Guinea", "Fiji"],
    "Americas": [
        "United States", "Canada", "Mexico", "Brazil", "Argentina", "Chile",
        "Colombia", "Peru", "Venezuela", "Ecuador", "Bolivia", "Paraguay",
        "Uruguay", "Panama", "Costa Rica", "Guatemala",
        "Dominican Republic", "Jamaica", "Trinidad",
    ],
    "Africa": [
        "South Africa", "Nigeria", "Kenya", "Ghana", "Ethiopia", "Tanzania",
        "Uganda", "Zimbabwe", "Mozambique", "Zambia", "Angola", "Namibia",
        "Botswana", "Senegal", "Ivory Coast", "Cameroon", "Tunisia",
        "Morocco", "Algeria", "Libya", "Sudan",
    ],
}

COUNTRY_ALIASES: dict[str, str] = {
    "UK": "United Kingdom", "UAE": "United Arab Emirates",
    "US": "United States", "USA": "United States", "KSA": "Saudi Arabia",
    "HK": "Hong Kong", "NZ": "New Zealand", "Dubai": "United Arab Emirates",
    "Abu Dhabi": "United Arab Emirates", "England": "United Kingdom",
    "Scotland": "United Kingdom", "Wales": "United Kingdom",
    "Northern Ireland": "United Kingdom",
}

TLD_COUNTRY: dict[str, str] = {
    ".co.uk": "United Kingdom", ".ac.uk": "United Kingdom",
    ".org.uk": "United Kingdom", ".co.ae": "United Arab Emirates",
    ".com.au": "Australia", ".co.nz": "New Zealand", ".co.in": "India",
    ".co.za": "South Africa", ".com.sg": "Singapore", ".co.jp": "Japan",
    ".com.hk": "Hong Kong", ".co.ke": "Kenya", ".com.ng": "Nigeria",
    ".com.gh": "Ghana", ".de": "Germany", ".fr": "France", ".es": "Spain",
    ".it": "Italy", ".nl": "Netherlands", ".be": "Belgium",
    ".ch": "Switzerland", ".at": "Austria", ".se": "Sweden",
    ".no": "Norway", ".dk": "Denmark", ".fi": "Finland", ".pl": "Poland",
    ".pt": "Portugal", ".ie": "Ireland", ".gr": "Greece",
    ".sg": "Singapore", ".jp": "Japan", ".cn": "China",
    ".com.br": "Brazil", ".com.mx": "Mexico", ".ca": "Canada",
    ".qa": "Qatar", ".sa": "Saudi Arabia", ".bh": "Bahrain",
    ".kw": "Kuwait", ".om": "Oman", ".tr": "Turkey", ".il": "Israel",
    ".hk": "Hong Kong",
}

COUNTRY_TO_CONTINENT: dict[str, str] = {}
COUNTRY_CANONICAL: dict[str, str] = {}

for _continent, _countries in CONTINENTS.items():
    for _c in _countries:
        _key = _c.lower()
        COUNTRY_TO_CONTINENT[_key] = _continent
        COUNTRY_CANONICAL[_key] = _c

for _alias, _canon in COUNTRY_ALIASES.items():
    _canon_lc = _canon.lower()
    if _canon_lc in COUNTRY_TO_CONTINENT:
        COUNTRY_TO_CONTINENT[_alias.lower()] = COUNTRY_TO_CONTINENT[_canon_lc]
        COUNTRY_CANONICAL[_alias.lower()] = _canon

ALL_MATCH_NAMES: list[str] = sorted(
    list(COUNTRY_TO_CONTINENT.keys()), key=lambda x: -len(x)
)

# ─── Feed list (identical to fetch_news.py) ────────────────────────────────

def _gnews(query: str, lang: str = "en", region: str = "US") -> str:
    return (
        f"https://news.google.com/rss/search?q={quote(query)}"
        f"&hl={lang}&gl={region}&ceid={region}:{lang}"
    )

RSS_FEEDS: list[str] = [
    # ── 1. Core
    _gnews("fitout construction"),
    _gnews('"fit-out" construction'),
    _gnews('"fit out" interior construction'),
    _gnews('"fitout contractor"'),
    _gnews('"fit-out contractor"'),
    _gnews('"fitout company"'),
    _gnews('"fitout project"'),
    _gnews('"fit-out project"'),
    _gnews('"fitout specialist"'),
    _gnews('"fit-out specialist"'),
    _gnews('"interior fit-out"'),
    _gnews('"office fit-out"'),
    _gnews('"office fitout"'),
    _gnews('"commercial fitout"'),
    _gnews('"retail fitout"'),
    _gnews('"hotel fitout"'),
    _gnews('"hotel fit-out"'),
    _gnews('"workplace fitout"'),
    _gnews('"fitout tender"'),
    _gnews('"fit-out tender"'),
    _gnews('"fitout contract award"'),
    # ── 2. Design & build
    _gnews('"design and build" interior'),
    _gnews('"design and build" "fit-out"'),
    _gnews('"design and build" workplace'),
    _gnews('"design and build" office'),
    _gnews('"design-build" interiors'),
    _gnews('"design build" interior fit-out'),
    _gnews('"turnkey fit-out"'),
    _gnews('"turnkey fitout"'),
    _gnews('"turnkey interiors"'),
    _gnews('"D&B fit-out"'),
    # ── 3. Technical / procurement
    _gnews('"Cat A fit-out"'),
    _gnews('"Cat B fit-out"'),
    _gnews('"Category A fit-out"'),
    _gnews('"Category B fit-out"'),
    _gnews('"tenant improvement" construction'),
    _gnews('"tenant fit-out"'),
    _gnews('"shell and core" fit-out'),
    _gnews('"shopfitting"'),
    _gnews('"shop fitting" contract'),
    _gnews('"interior contractor"'),
    _gnews('"commercial interiors" contract'),
    _gnews('"workplace transformation"'),
    _gnews('"workspace transformation"'),
    _gnews('"office refurbishment" commercial'),
    _gnews('"interior refurbishment" commercial'),
    _gnews('"landlord fit-out"'),
    # ── 4. Sector-specific
    _gnews('"data centre fitout"'),
    _gnews('"data center fit-out"'),
    _gnews('"laboratory fitout"'),
    _gnews('"lab fit-out"'),
    _gnews('"life sciences fit-out"'),
    _gnews('"hospital fit-out"'),
    _gnews('"healthcare fit-out"'),
    _gnews('"airport fit-out"'),
    _gnews('"airport terminal fitout"'),
    _gnews('"museum fit-out"'),
    _gnews('"exhibition fitout"'),
    _gnews('"restaurant fit-out"'),
    _gnews('"hospitality fit-out"'),
    _gnews('"hotel fit-out"'),
    _gnews('"F&B fit-out"'),
    _gnews('"bar fit-out"'),
    _gnews('"luxury residential fitout"'),
    _gnews('"yacht interior fit-out"'),
    _gnews('"cruise ship fitout"'),
    _gnews('"sports facility fitout"'),
    _gnews('"stadium fit-out" interior'),
    _gnews('"school fit-out"'),
    _gnews('"university fit-out"'),
    _gnews('"cultural fit-out"'),
    _gnews('"heritage fit-out"'),
    _gnews('"visitor attraction" fit-out'),
    _gnews('"science centre" fitout'),
    _gnews('"brand experience" fitout'),
    # ── 5. Regional languages
    _gnews("Innenausbau Büro",                 "de", "DE"),
    _gnews("Ladenausbau",                       "de", "DE"),
    _gnews("Büroausbau",                        "de", "DE"),
    _gnews("Innenausbau Gewerbe",               "de", "DE"),
    _gnews("aménagement intérieur bureau",       "fr", "FR"),
    _gnews("agencement commercial",              "fr", "FR"),
    _gnews("aménagement de bureaux",             "fr", "FR"),
    _gnews("interiorismo comercial",             "es", "ES"),
    _gnews("acondicionamiento de interiores",    "es", "ES"),
    _gnews("obra de acondicionamiento",          "es", "ES"),
    _gnews("kantoorinrichting",                  "nl", "NL"),
    _gnews("winkelinrichting",                   "nl", "NL"),
    _gnews("allestimento interni commerciali",   "it", "IT"),
    _gnews("ristrutturazione uffici",            "it", "IT"),
    _gnews("تشطيبات داخلية",                    "ar", "AE"),
    _gnews("تشطيب مكاتب",                       "ar", "AE"),
    # ── 6. Region-biased
    _gnews("fitout",                   "en", "GB"),
    _gnews('"fit-out"',                "en", "GB"),
    _gnews("fitout",                   "en", "AU"),
    _gnews("fitout",                   "en", "AE"),
    _gnews("fitout",                   "en", "SG"),
    _gnews("fitout",                   "en", "IN"),
    _gnews("fitout",                   "en", "ZA"),
    _gnews("fitout",                   "en", "IE"),
    _gnews("fitout",                   "en", "NZ"),
    _gnews("fitout",                   "en", "CA"),
    _gnews("fitout",                   "en", "NG"),
    _gnews("fitout",                   "en", "KE"),
    _gnews("fitout",                   "en", "US"),
    _gnews("fitout",                   "ar", "QA"),
    _gnews("fitout",                   "ar", "SA"),
    _gnews('"design and build" interior', "en", "US"),
    _gnews('"design and build" interior', "en", "GB"),
    _gnews("interiorismo comercial",   "es", "ES"),
    _gnews("interiorismo comercial",   "es", "MX"),
    _gnews('"fit-out"',                "zh", "HK"),
    _gnews('"fit-out" interior',       "pt", "BR"),
    _gnews("Innenausbau",              "de", "DE"),
    _gnews("aménagement intérieur bureau", "fr", "FR"),
    # ── 7. Company tracking — established
    _gnews('"Overbury" fitout'),
    _gnews('"Morgan Lovell" office'),
    _gnews('"BW Workplace" OR "BW Interiors" fitout'),
    _gnews('"Willmott Dixon Interiors"'),
    _gnews('"Parkeray" fitout'),
    _gnews('"Portview" fitout'),
    _gnews('"Oktra" fitout'),
    _gnews('"8Build" OR "8build" fitout'),
    _gnews('"Collins Construction" fitout'),
    _gnews('"Peldon Rose"'),
    _gnews('"Mace" fitout OR "Mace Group" fit-out'),
    _gnews('"Structure Tone" fitout'),
    _gnews('"Fit Out UK"'),
    _gnews('"Tétris" OR "Tetris design and build" OR "Tetris by JLL"'),
    _gnews('"Skanska" fitout OR "Skanska" interior'),
    _gnews('"Linesight" fitout'),
    _gnews('"Area" workplace fitout'),
    _gnews('"Wates Smartspace" OR "Wates" fitout'),
    _gnews('"Gilbert-Ash" construction OR fitout'),
    _gnews('"Studio Alliance" interior'),
    _gnews('"Red Space" fitout OR "Red Space" interior'),
    _gnews('"Wren Interiors" fitout'),
    _gnews('"Depa Group" OR "Depa Interiors"'),
    _gnews('"ALEC Fitout" OR "ALEC fit-out"'),
    _gnews('"Havelock One"'),
    _gnews('"A&T Group Interiors" OR "AT Group Interiors"'),
    _gnews('"AMAQ Interiors"'),
    _gnews('"MGM Interiors"'),
    _gnews('"Abra" fitout Dubai'),
    _gnews('"INC Group" fitout'),
    _gnews('"Summertown Interiors"'),
    _gnews('"STO Building Group"'),
    _gnews('"HITT Contracting"'),
    _gnews('"Turner Construction" fitout OR interior'),
    _gnews('"Gensler" fitout OR workplace'),
    _gnews('"HOK" fitout OR interior'),
    _gnews('"Perkins and Will" OR "Perkins+Will" interior'),
    _gnews('"Stantec" interior fit-out'),
    _gnews('"AECOM" fitout'),
    _gnews('"PCL Construction" fitout'),
    _gnews('"IA Interior Architects"'),
    _gnews('"CBRE" fitout OR "CBRE Project Management" interior'),
    _gnews('"Lendlease" fitout OR interior'),
    _gnews('"Schiavello" fitout'),
    _gnews('"Buildcorp" fitout'),
    _gnews('"Multiplex" fitout'),
    _gnews('"Greater Group" fitout'),
    _gnews('"Futurespace" fitout OR workplace'),
    _gnews('"Intermain" fitout OR commercial'),
    _gnews('"Legend Interiors" fitout'),
    _gnews('"LWK Partners" OR "LWK + Partners" interior'),
    _gnews('"Cushman & Wakefield" fitout'),
    _gnews('"JLL" fitout OR "Jones Lang LaSalle" fit-out'),
    _gnews('"Savills" fitout OR "Savills" interior'),
    _gnews('"Martínez Otero" OR "Martinez Otero" interior'),
    _gnews('"Empty" interior design Spain OR "Empty Studio" interiors'),
    _gnews('"Cador" fitout OR "Cador" interiors Belgium'),
    _gnews('"Beck Interiors" fitout'),
    _gnews('"The Hub" fitout OR "The Hub" exhibition'),
    _gnews('"Bond Interiors" fitout UAE'),
    _gnews('"Saudi Icon" fitout Riyadh'),
    _gnews('"GEM Interior Contracts" OR "GEM Interiors" fitout'),
    _gnews('"Marcon Fit-Out" OR "Marcon fitout"'),
    _gnews('"CCL Interiors" Belfast'),
    _gnews('"Bradagh Interiors"'),
    _gnews('"Bruns" museum exhibition interiors'),
    _gnews('"Hypsos" museum exhibition OR "Hypsos" brand experience'),
    _gnews('"Mivan" fitout OR "Mivan" joinery OR "Mivan" interiors'),
    _gnews('"Craft Group" Saudi Arabia OR "Craft Group" AlUla OR craft.group'),
    _gnews('"Saudi Icon" fitout OR "Saudi Icon" interiors'),
    # ── 8. Industry RSS — established
    "https://www.interiorsmonthly.co.uk/feed/",
    "https://www.buildingdesign.co.uk/rss",
    "https://www.architectsjournal.co.uk/feed",
    "https://www.bdonline.co.uk/rss",
    "https://contractormagazine.com.au/feed",
    "https://www.constructionworld.in/feed/",
    "https://www.meed.com/feeds/rss/all-articles",
    "https://www.dezeen.com/feed/",
    "https://www.workplaceinsight.net/feed/",
    # ── 8b. Industry RSS — new
    "https://www.contractjournal.com/feed/",
    "https://www.bdcnetwork.com/rss.xml",
    "https://www.interiorsandsources.com/feed/",
    "https://www.commercialdesign.in/feed/",
    "https://www.commercialinteriordesign.com/feed/",
    "https://officelovin.com/feed/",
]

FEED_LABELS = (
    ["Core"] * 21 +
    ["Design&Build"] * 10 +
    ["Technical/Procurement"] * 16 +
    ["Sector"] * 25 +
    ["Regional/Language"] * 16 +
    ["Region-biased"] * 23 +
    ["CompanyTracking"] * 71 +
    ["IndustryRSS"] * 15
)

# Pad if lengths don't match
while len(FEED_LABELS) < len(RSS_FEEDS):
    FEED_LABELS.append("Other")

# ─── Relevance filter ────────────────────────────────────────────────────────

MUST_HAVE = re.compile(
    r"fit.?out|"
    r"interior\s+construction|interior\s+refurb|interior\s+renovation|"
    r"office\s+(space|interior|refurb|renovation)|"
    r"workspace\s+design|workspace\s+transformation|"
    r"workplace\s+design|workplace\s+transformation|"
    r"commercial\s+interior|retail\s+interior|"
    r"design.and.build\s+(interior|workplace|office)|"
    r"design.build\s+interior|"
    r"turnkey\s+(fit.?out|interior)|"
    r"tenant\s+(fit.?out|improvement)|"
    r"cat\s*[ab]\s+fit.?out|category\s+[ab]\s+fit.?out|"
    r"shopfit|shopfitting|shop\s+fitting|"
    r"interior\s+contractor|"
    r"innenausbau|büroausbau|ladenausbau|"
    r"aménagement\s+intérieur|aménagement\s+de\s+bureaux|agencement\s+commercial|"
    r"interiorismo\s+comercial|acondicionamiento\s+de\s+interiores|"
    r"kantoorinrichting|winkelinrichting|"
    r"allestimento\s+interni|ristrutturazione\s+uffici|"
    r"تشطيبات\s+داخلية|تشطيب\s+مكاتب",
    re.IGNORECASE,
)

def is_relevant(title: str, description: str) -> bool:
    return bool(MUST_HAVE.search(title + " " + description))

# ─── Geo helpers ─────────────────────────────────────────────────────────────

def detect_country_from_text(text: str) -> str | None:
    text_l = text.lower()
    for name in ALL_MATCH_NAMES:
        pattern = r"(?<![a-z])" + re.escape(name) + r"(?![a-z])"
        if re.search(pattern, text_l):
            return COUNTRY_CANONICAL.get(name)
    return None

def detect_country_from_url(url: str) -> str | None:
    try:
        domain = urlparse(url).netloc.lower()
        for tld, country in sorted(TLD_COUNTRY.items(), key=lambda x: -len(x[0])):
            if domain.endswith(tld):
                return country
    except Exception:
        pass
    return None

def resolve_geo(title: str, description: str, url: str, source: str) -> tuple[str, str]:
    combined = f"{title}  {description}  {source}"
    country = detect_country_from_text(combined) or detect_country_from_url(url)
    if country:
        continent = COUNTRY_TO_CONTINENT.get(country.lower(), "Global")
        return country, continent
    return "Global", "Global"

# ─── Feed parsing ─────────────────────────────────────────────────────────────

def _clean_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)

def _parse_date(entry) -> str:
    if getattr(entry, "published_parsed", None):
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()

def _entry_source(entry, feed_title: str) -> tuple[str, str]:
    src = entry.get("source", {})
    name = src.get("title") or feed_title
    href = src.get("href", "")
    return name, href

def fetch_feed(url: str, seen: set[str], label: str) -> tuple[list[dict], int, int]:
    """Returns (articles_found, total_entries, passed_filter)."""
    articles = []
    total_entries = 0
    passed_filter = 0

    for attempt in range(1, 3):
        try:
            feed = feedparser.parse(
                url,
                request_headers={"User-Agent": "FitOutPost/2.0 (news aggregator; +fitoutpost.com)"},
            )
            feed_title = (
                feed.feed.get("title", urlparse(url).netloc) if feed.feed else urlparse(url).netloc
            )
            total_entries = len(feed.entries)

            for entry in feed.entries:
                link = entry.get("link", "").strip()
                if not link or link in seen:
                    continue
                title = _clean_html(entry.get("title", ""))
                desc  = _clean_html(entry.get("summary", entry.get("description", "")))
                if not title:
                    continue
                passed_filter += 1 if is_relevant(title, desc) else 0
                if not is_relevant(title, desc):
                    continue

                source_name, publisher_url = _entry_source(entry, feed_title)
                geo_url = publisher_url or link
                country, continent = resolve_geo(title, desc, geo_url, source_name)
                seen.add(link)

                articles.append({
                    "id":          hashlib.md5(link.encode()).hexdigest()[:10],
                    "title":       title,
                    "url":         link,
                    "source":      source_name,
                    "published":   _parse_date(entry),
                    "description": (desc[:350] + "…") if len(desc) > 350 else desc,
                    "country":     country,
                    "continent":   continent,
                    "_feed_label": label,
                })

            break
        except Exception as exc:
            log.warning("Attempt %d failed for %s: %s", attempt, url[:60], exc)
            if attempt < 2:
                time.sleep(2)

    return articles, total_entries, passed_filter

# ─── Save partial results ─────────────────────────────────────────────────────

def save_partial(articles: list[dict], path: str = "news_audit.json") -> None:
    payload = {
        "last_updated":   datetime.now(timezone.utc).isoformat(),
        "total_articles": len(articles),
        "articles":       articles,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

# ─── Quality report ───────────────────────────────────────────────────────────

def quality_report(feed_stats: list[dict], all_articles: list[dict]) -> None:
    print("\n" + "="*70)
    print("  FitOut Post — Algorithm Quality Audit Report")
    print("="*70)

    # Feed yield by category
    by_label: dict[str, dict] = defaultdict(lambda: {"feeds": 0, "entries": 0, "matched": 0, "accepted": 0})
    zero_yield = []

    for fs in feed_stats:
        label = fs["label"]
        by_label[label]["feeds"] += 1
        by_label[label]["entries"] += fs["entries"]
        by_label[label]["matched"] += fs["matched"]
        by_label[label]["accepted"] += fs["accepted"]
        if fs["accepted"] == 0:
            zero_yield.append(fs)

    print(f"\n{'FEED CATEGORY':<28} {'FEEDS':>5} {'ENTRIES':>8} {'MATCHED':>8} {'ACCEPTED':>9} {'YIELD%':>7}")
    print("-"*70)
    for label, d in by_label.items():
        pct = (d["accepted"] / d["entries"] * 100) if d["entries"] else 0
        print(f"{label:<28} {d['feeds']:>5} {d['entries']:>8} {d['matched']:>8} {d['accepted']:>9} {pct:>6.1f}%")

    total_entries  = sum(d["entries"]  for d in by_label.values())
    total_accepted = sum(d["accepted"] for d in by_label.values())
    total_pct = (total_accepted / total_entries * 100) if total_entries else 0
    print("-"*70)
    print(f"{'TOTAL':<28} {len(feed_stats):>5} {total_entries:>8} {'':>8} {total_accepted:>9} {total_pct:>6.1f}%")

    # Zero-yield feeds
    print(f"\n── ZERO-YIELD FEEDS ({len(zero_yield)}) ──────────────────────────────────")
    for fs in zero_yield[:30]:
        url_short = fs["url"][:80]
        print(f"  [{fs['label']}] {url_short}")

    # Geo coverage
    by_continent: dict[str, int] = defaultdict(int)
    by_country: dict[str, int] = defaultdict(int)
    for a in all_articles:
        by_continent[a["continent"]] += 1
        by_country[a["country"]] += 1

    print("\n── GEO COVERAGE — by continent ──────────────────────────────────────")
    for cont, cnt in sorted(by_continent.items(), key=lambda x: -x[1]):
        pct = cnt / len(all_articles) * 100 if all_articles else 0
        bar = "█" * int(pct / 2)
        print(f"  {cont:<20} {cnt:>4} articles  ({pct:4.1f}%) {bar}")

    print("\n── GEO COVERAGE — top 20 countries ─────────────────────────────────")
    for country, cnt in sorted(by_country.items(), key=lambda x: -x[1])[:20]:
        print(f"  {country:<30} {cnt:>4}")

    # Freshness
    now = datetime.now(timezone.utc)
    ages = {1: 0, 3: 0, 7: 0, 14: 0, 30: 0}
    for a in all_articles:
        try:
            pub = datetime.fromisoformat(a["published"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            age_days = (now - pub).days
            for threshold in [1, 3, 7, 14, 30]:
                if age_days <= threshold:
                    ages[threshold] += 1
        except Exception:
            pass

    print("\n── FRESHNESS ────────────────────────────────────────────────────────")
    for days, cnt in ages.items():
        pct = cnt / len(all_articles) * 100 if all_articles else 0
        print(f"  Last {days:>2} day(s): {cnt:>4} articles ({pct:.1f}%)")

    # Top sources
    sources: dict[str, int] = defaultdict(int)
    for a in all_articles:
        sources[a["source"]] += 1

    print("\n── TOP 15 SOURCES ───────────────────────────────────────────────────")
    for src, cnt in sorted(sources.items(), key=lambda x: -x[1])[:15]:
        print(f"  {src:<45} {cnt:>4}")

    # Sample Global articles (geo unknown — potential issue)
    global_arts = [a for a in all_articles if a["country"] == "Global"]
    print(f"\n── GLOBAL (unresolved geo): {len(global_arts)} articles ({len(global_arts)/len(all_articles)*100:.1f}% of total) ──")
    print("  Sample titles:")
    for a in global_arts[:5]:
        print(f"    • {a['title'][:75]}")

    print("\n" + "="*70)
    print(f"  SUMMARY: {len(all_articles)} new articles from {len(feed_stats)} feeds")
    print("="*70 + "\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Load prior news.json to pre-populate seen set (deduplication)
    seen: set[str] = set()
    prior_path = Path("news.json")
    prior_articles: list[dict] = []
    if prior_path.exists():
        try:
            payload = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_articles = payload.get("articles", [])
            seen = {a["url"] for a in prior_articles}
            log.info("Loaded %d prior URLs from news.json", len(seen))
        except Exception as exc:
            log.warning("Could not load prior news.json: %s", exc)

    all_articles: list[dict] = []
    feed_stats: list[dict] = []
    n = len(RSS_FEEDS)

    for i, (url, label) in enumerate(zip(RSS_FEEDS, FEED_LABELS), 1):
        t0 = time.time()
        arts, entries, matched = fetch_feed(url, seen, label)
        elapsed = time.time() - t0

        feed_stats.append({
            "index":    i,
            "url":      url,
            "label":    label,
            "entries":  entries,
            "matched":  matched,
            "accepted": len(arts),
            "elapsed":  round(elapsed, 2),
        })

        all_articles.extend(arts)
        log.info(
            "[%3d/%d] %s | entries=%d matched=%d accepted=%d (%.1fs)",
            i, n, label, entries, matched, len(arts), elapsed
        )

        # Save partial results every 50 feeds
        if i % 50 == 0 or i == n:
            log.info("Saving partial results (%d articles so far)...", len(all_articles))
            save_partial(all_articles)

        # 0.2 s delay — faster than production for audit purposes
        time.sleep(0.2)

    # Save final audit JSON (new articles only — not merged with prior)
    save_partial(all_articles, "news_audit.json")

    # Also merge with prior and save as news.json (replace prior run)
    merged = all_articles + prior_articles
    # Deduplicate by URL
    seen_final: set[str] = set()
    deduped: list[dict] = []
    for a in merged:
        if a["url"] not in seen_final:
            seen_final.add(a["url"])
            deduped.append(a)
    # Trim to 30-day window
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    deduped = [a for a in deduped if a.get("published", "") >= cutoff]
    deduped.sort(key=lambda x: x.get("published", ""), reverse=True)

    with open("news.json", "w", encoding="utf-8") as fh:
        json.dump({
            "last_updated":   datetime.now(timezone.utc).isoformat(),
            "total_articles": len(deduped),
            "articles":       deduped,
        }, fh, ensure_ascii=False, indent=2)
    log.info("Saved merged news.json: %d articles total", len(deduped))

    # Quality report
    quality_report(feed_stats, all_articles)


if __name__ == "__main__":
    main()
