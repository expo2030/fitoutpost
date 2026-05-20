#!/usr/bin/env python3
"""
FitOut Post — News Aggregator Fetcher  (v2)
Pulls fitout/fit-out/fit out news from multiple RSS sources,
geo-detects each article, and saves to news.json.

Changes in v2:
  - Expanded MUST_HAVE regex: design and build (interiors), tenant improvement,
    shopfitting, Cat A/B fit-out, turnkey, workspace/workplace transformation
  - Full design-and-build track (Google News queries)
  - Technical / procurement queries
  - New sector coverage: healthcare, F&B, sports, education
  - Extended region-biased feeds: US, QA, SA, HK, JP, ES, MX, BR
  - 12 new company tracking feeds
  - 7 additional trade publication RSS feeds
  - Retry logic (up to 3 attempts with back-off)
  - Cross-run deduplication: loads existing news.json and preserves prior articles
  - Delay increased to 0.6 s (below Google News aggressive rate-limit threshold)

Usage:
    pip install feedparser requests beautifulsoup4
    python fetch_news.py
"""

import json
import re
import time
import hashlib
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, quote

import feedparser
import requests
from bs4 import BeautifulSoup

# Hard cap: any RSS connection that doesn't respond within 10 s is dropped.
# Prevents a single hanging feed from blocking the entire run.
socket.setdefaulttimeout(10)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s")
log = logging.getLogger("fitoutpost")

# ─────────────────────────────────────────────────────────────────────────────
#  Geographic reference data
# ─────────────────────────────────────────────────────────────────────────────

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
        "Australia", "New Zealand", "Papua New Guinea", "Fiji",
    ],
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

# Short-name / abbreviation → canonical country name
COUNTRY_ALIASES: dict[str, str] = {
    "UK":             "United Kingdom",
    "UAE":            "United Arab Emirates",
    "US":             "United States",
    "USA":            "United States",
    "KSA":            "Saudi Arabia",
    "HK":             "Hong Kong",
    "NZ":             "New Zealand",
    "Dubai":          "United Arab Emirates",
    "Abu Dhabi":      "United Arab Emirates",
    "England":        "United Kingdom",
    "Scotland":       "United Kingdom",
    "Wales":          "United Kingdom",
    "Northern Ireland": "United Kingdom",
    # UK cities
    "London":         "United Kingdom",
    "Manchester":     "United Kingdom",
    "Birmingham":     "United Kingdom",
    "Liverpool":      "United Kingdom",
    "Leeds":          "United Kingdom",
    "Sheffield":      "United Kingdom",
    "Bristol":        "United Kingdom",
    "Newcastle":      "United Kingdom",
    "Nottingham":     "United Kingdom",
    "Glasgow":        "United Kingdom",
    "Edinburgh":      "United Kingdom",
    "Belfast":        "United Kingdom",
    "Cardiff":        "United Kingdom",
    "Oxford":         "United Kingdom",
    "Cambridge":      "United Kingdom",
    "Antrim":         "United Kingdom",
    "Derry":          "United Kingdom",
    # German cities
    "Berlin":         "Germany",
    "Munich":         "Germany",
    "Frankfurt":      "Germany",
    "Hamburg":        "Germany",
    "Düsseldorf":     "Germany",
    "Cologne":        "Germany",
    "Stuttgart":      "Germany",
    "Köln":           "Germany",
    # French cities
    "Paris":          "France",
    "Lyon":           "France",
    # Australian cities
    "Sydney":         "Australia",
    "Melbourne":      "Australia",
    "Brisbane":       "Australia",
    "Perth":          "Australia",
    "Adelaide":       "Australia",
    # US cities
    "New York":       "United States",
    "Chicago":        "United States",
    "Los Angeles":    "United States",
    "Houston":        "United States",
    "Atlanta":        "United States",
    "Dallas":         "United States",
    "San Francisco":  "United States",
    "Boston":         "United States",
    # Saudi cities / regions
    "Riyadh":         "Saudi Arabia",
    "Jeddah":         "Saudi Arabia",
    "AlUla":          "Saudi Arabia",
    "NEOM":           "Saudi Arabia",
    # Other
    "Doha":           "Qatar",
    "Muscat":         "Oman",
    "Manama":         "Bahrain",
    "Kuwait City":    "Kuwait",
    "Toronto":        "Canada",
    "Vancouver":      "Canada",
    "Toronto":        "Canada",
    "Tokyo":          "Japan",
    "Seoul":          "South Korea",
    "Amsterdam":      "Netherlands",
    "Brussels":       "Belgium",
    "Milan":          "Italy",
    "Madrid":         "Spain",
    "Barcelona":      "Spain",
    "Seville":        "Spain",
    "Valencia":       "Spain",
    "Lisbon":         "Portugal",
    "Porto":          "Portugal",
    "Dublin":         "Ireland",
    "Johannesburg":   "South Africa",
    "Cape Town":      "South Africa",
    "Lagos":          "Nigeria",
    "Nairobi":        "Kenya",
    "Mombasa":        "Kenya",
    "Auckland":       "New Zealand",
    "Wellington":     "New Zealand",
    "Mumbai":         "India",
    "Delhi":          "India",
    "Bangalore":      "India",
    "Singapore":      "Singapore",
    "Arnstorf":       "Germany",
    "Dusseldorf":     "Germany",
    # More UK cities
    "Chelsea":        "United Kingdom",
    "Canary Wharf":   "United Kingdom",
    "Mayfair":        "United Kingdom",
    "Shoreditch":     "United Kingdom",
    "Westminster":    "United Kingdom",
    "Southwark":      "United Kingdom",
    "Hammersmith":    "United Kingdom",
    # More US cities
    "Indianapolis":   "United States",
    "Phoenix":        "United States",
    "Miami":          "United States",
    "Seattle":        "United States",
    "Denver":         "United States",
    "Nashville":      "United States",
    "Charlotte":      "United States",
    "Austin":         "United States",
    "Minneapolis":    "United States",
    "San Diego":      "United States",
    "Portland":       "United States",
    "Pittsburgh":     "United States",
    "Columbus":       "United States",
    # More European cities
    "Zurich":         "Switzerland",
    "Zürich":         "Switzerland",
    "Geneva":         "Switzerland",
    "Vienna":         "Austria",
    "Wien":           "Austria",
    "Warsaw":         "Poland",
    "Prague":         "Czech Republic",
    "Budapest":       "Hungary",
    "Copenhagen":     "Denmark",
    "Stockholm":      "Sweden",
    "Oslo":           "Norway",
    "Helsinki":       "Finland",
    "Athens":         "Greece",
    "Rome":           "Italy",
    "Florence":       "Italy",
    "Venice":         "Italy",
    "Antwerp":        "Belgium",
    "Rotterdam":      "Netherlands",
    "The Hague":      "Netherlands",
    # More Asia Pacific cities
    "Kuala Lumpur":   "Malaysia",
    "KL":             "Malaysia",
    "Bangkok":        "Thailand",
    "Ho Chi Minh":    "Vietnam",
    "Hanoi":          "Vietnam",
    "Jakarta":        "Indonesia",
    "Manila":         "Philippines",
    "Shanghai":       "China",
    "Beijing":        "China",
    "Shenzhen":       "China",
    "Guangzhou":      "China",
    "Taipei":         "Taiwan",
    "Osaka":          "Japan",
    "Chennai":        "India",
    "Hyderabad":      "India",
    "Pune":           "India",
    "Kolkata":        "India",
    # More Middle East cities
    "Sharjah":        "United Arab Emirates",
    "Ajman":          "United Arab Emirates",
    "Ras Al Khaimah": "United Arab Emirates",
    "Bahrain":        "Bahrain",
    # More Africa cities
    "Casablanca":     "Morocco",
    "Marrakech":      "Morocco",
    "Rabat":          "Morocco",
    "Cairo":          "Egypt",
    "Alexandria":     "Egypt",
    "Accra":          "Ghana",
    "Dar es Salaam":  "Tanzania",
    "Addis Ababa":    "Ethiopia",
    "Tunis":          "Tunisia",
    # Americas
    "São Paulo":      "Brazil",
    "Rio de Janeiro": "Brazil",
    "Buenos Aires":   "Argentina",
    "Bogotá":         "Colombia",
    "Lima":           "Peru",
    "Santiago":       "Chile",
    "Mexico City":    "Mexico",
    "Montreal":       "Canada",
    "Calgary":        "Canada",
    "Ottawa":         "Canada",
}

# Domain TLD suffix → country
TLD_COUNTRY: dict[str, str] = {
    ".co.uk":   "United Kingdom",
    ".ac.uk":   "United Kingdom",
    ".org.uk":  "United Kingdom",
    ".co.ae":   "United Arab Emirates",
    ".com.au":  "Australia",
    ".co.nz":   "New Zealand",
    ".co.in":   "India",
    ".co.za":   "South Africa",
    ".com.sg":  "Singapore",
    ".co.jp":   "Japan",
    ".com.hk":  "Hong Kong",
    ".co.ke":   "Kenya",
    ".com.ng":  "Nigeria",
    ".com.gh":  "Ghana",
    ".de":      "Germany",
    ".fr":      "France",
    ".es":      "Spain",
    ".it":      "Italy",
    ".nl":      "Netherlands",
    ".be":      "Belgium",
    ".ch":      "Switzerland",
    ".at":      "Austria",
    ".se":      "Sweden",
    ".no":      "Norway",
    ".dk":      "Denmark",
    ".fi":      "Finland",
    ".pl":      "Poland",
    ".pt":      "Portugal",
    ".ie":      "Ireland",
    ".gr":      "Greece",
    ".sg":      "Singapore",
    ".jp":      "Japan",
    ".cn":      "China",
    ".com.br":  "Brazil",
    ".com.mx":  "Mexico",
    ".ca":      "Canada",
    ".qa":      "Qatar",
    ".sa":      "Saudi Arabia",
    ".bh":      "Bahrain",
    ".kw":      "Kuwait",
    ".om":      "Oman",
    ".tr":      "Turkey",
    ".il":      "Israel",
    ".hk":      "Hong Kong",
    ".my":      "Malaysia",
    ".id":      "Indonesia",
    ".ph":      "Philippines",
    ".th":      "Thailand",
    ".vn":      "Vietnam",
    ".ro":      "Romania",
    ".cz":      "Czech Republic",
    ".hu":      "Hungary",
    ".sk":      "Slovakia",
    ".hr":      "Croatia",
    ".rs":      "Serbia",
    ".cl":      "Chile",
    ".ar":      "Argentina",
    ".pe":      "Peru",
    ".ma":      "Morocco",
    ".eg":      "Egypt",
    ".ng":      "Nigeria",
    ".tz":      "Tanzania",
    ".et":      "Ethiopia",
    ".nz":      "New Zealand",
    ".in":      "India",
}

# Build fast lookup: lowercase name → continent
COUNTRY_TO_CONTINENT: dict[str, str] = {}
COUNTRY_CANONICAL: dict[str, str] = {}   # lowercase → display name

for _continent, _countries in CONTINENTS.items():
    for _c in _countries:
        _key = _c.lower()
        COUNTRY_TO_CONTINENT[_key] = _continent
        COUNTRY_CANONICAL[_key] = _c

# Register aliases
for _alias, _canon in COUNTRY_ALIASES.items():
    _canon_lc = _canon.lower()
    if _canon_lc in COUNTRY_TO_CONTINENT:
        COUNTRY_TO_CONTINENT[_alias.lower()] = COUNTRY_TO_CONTINENT[_canon_lc]
        COUNTRY_CANONICAL[_alias.lower()] = _canon

# Sorted longest-first for greedy text matching
ALL_MATCH_NAMES: list[str] = sorted(
    list(COUNTRY_TO_CONTINENT.keys()),
    key=lambda x: -len(x),
)

# ─────────────────────────────────────────────────────────────────────────────
#  RSS feed list
# ─────────────────────────────────────────────────────────────────────────────

def _gnews(query: str, lang: str = "en", region: str = "US", period: str = "y") -> str:
    """Build a Google News RSS URL.

    period: 'd' = last day, 'w' = last week, 'm' = last month (default), 'y' = last year
    """
    tbs = f"&tbs=qdr:{period}" if period else ""
    return (
        f"https://news.google.com/rss/search?q={quote(query)}"
        f"&hl={lang}&gl={region}&ceid={region}:{lang}{tbs}"
    )

# Trusted RSS domains: specialist fit-out / commercial construction publications only.
# These domains bypass the MUST_HAVE relevance filter because they are narrowly focused
# on commercial interiors / construction and don't require "fit-out" in every headline.
# NOTE: Do NOT add broad design publications (e.g. Dezeen) or soft-content workplace
# sites (e.g. workplaceinsight.net) — they produce too many false positives.
TRUSTED_RSS_DOMAINS = {
    # Only narrowly-focused commercial fit-out/interiors trade publications.
    # Removed interiorsmonthly.co.uk — too many furniture/trade-show articles.
    # Removed bdonline.co.uk — general architecture, not fit-out.
    "contractormagazine.com.au", # AU trade: construction/fit-out
    "contractjournal.com",       # UK trade: contracts + fit-out
    "commercialdesign.in",       # IN trade: commercial interiors
    "commercialinteriordesign.com",  # US/ME trade: commercial interiors
    "meed.com",                  # ME trade: construction + projects
    "bdcnetwork.com",            # US trade: building design + construction
    "interiorsandsources.com",   # US trade: contract interiors
}

# Article URLs from these domains are always rejected, even if they appear in Google News
# results for fitout queries (they generate too many false positives).
BLOCKED_ARTICLE_DOMAINS: set[str] = {
    "architectsjournal.co.uk",  # General architecture, not fit-out
    "bdonline.co.uk",           # General architecture / Building Design
    # dezeen.com unblocked — now tracked via RSS with relevance filter applied
    "workplaceinsight.net",     # Soft-HR / workplace trends, not fit-out works
    "officelovin.com",          # Office inspiration, not industry news
}

RSS_FEEDS: list[str] = [

    # ── 1. Core fit-out identifiers ──────────────────────────────────────────
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

    # ── 2. Design and build (interiors) ─────────────────────────────────────
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

    # ── 3. Technical / procurement ───────────────────────────────────────────
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

    # ── 4. Sector-specific ───────────────────────────────────────────────────
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

    # ── 5. Regional language searches ────────────────────────────────────────
    # German (DE/AT/CH)
    _gnews("Innenausbau Büro",              "de", "DE"),
    _gnews("Ladenausbau",                   "de", "DE"),
    _gnews("Büroausbau",                    "de", "DE"),
    _gnews("Innenausbau Gewerbe",           "de", "DE"),
    _gnews("Hotelausbau",                   "de", "DE"),
    _gnews("Innenausbau Auftrag",           "de", "DE"),
    _gnews("Ausbauarbeiten Büro",           "de", "DE"),
    _gnews("gewerblicher Innenausbau",      "de", "DE"),
    _gnews("Innenausbau Österreich",        "de", "AT"),
    _gnews("Innenausbau Schweiz",           "de", "CH"),

    # French (FR/BE/CH)
    _gnews("aménagement intérieur bureau",  "fr", "FR"),
    _gnews("agencement commercial",         "fr", "FR"),
    _gnews("aménagement de bureaux",        "fr", "FR"),
    _gnews("agencement intérieur hôtel",    "fr", "FR"),
    _gnews("travaux aménagement intérieur", "fr", "FR"),
    _gnews("second œuvre bureau",           "fr", "FR"),
    _gnews("cloisonnement bureaux",         "fr", "FR"),
    _gnews("aménagement intérieur marché",  "fr", "BE"),

    # Spanish (ES/MX/CO/PE/AR)
    _gnews("interiorismo comercial",        "es", "ES"),
    _gnews("acondicionamiento de interiores","es", "ES"),
    _gnews("obra de acondicionamiento",     "es", "ES"),
    _gnews("reforma de oficinas",           "es", "ES"),
    _gnews("habilitación de espacios",      "es", "ES"),
    _gnews("acondicionamiento oficinas",    "es", "MX"),
    _gnews("remodelación oficinas",         "es", "MX"),
    _gnews("adecuación de espacios",        "es", "CO"),

    # Brazilian Portuguese
    _gnews("retrofit escritório",           "pt", "BR"),
    _gnews("reforma de escritório",         "pt", "BR"),
    _gnews("interiores comerciais",         "pt", "BR"),
    _gnews("obra interior comercial",       "pt", "BR"),

    # Italian
    _gnews("allestimento interni commerciali","it", "IT"),
    _gnews("ristrutturazione uffici",       "it", "IT"),
    _gnews("progettazione interni",         "it", "IT"),
    _gnews("allestimento hotel interior",   "it", "IT"),
    _gnews("lavori allestimento uffici",    "it", "IT"),

    # Dutch / Flemish
    _gnews("kantoorinrichting",             "nl", "NL"),
    _gnews("winkelinrichting",              "nl", "NL"),
    _gnews("afbouw kantoor",               "nl", "NL"),
    _gnews("interieurinrichting opdracht",  "nl", "NL"),
    _gnews("kantoorinrichting project",     "nl", "BE"),

    # Nordic — Swedish / Danish / Norwegian / Finnish
    _gnews("kontorsanpassning",             "sv", "SE"),
    _gnews("inredning kontor",              "sv", "SE"),
    _gnews("inredningsentreprenad",         "sv", "SE"),
    _gnews("indretning kontor",             "da", "DK"),
    _gnews("kontorindretning projekt",      "da", "DK"),
    _gnews("kontortilpasning",              "no", "NO"),
    _gnews("sisustusrakentaminen",          "fi", "FI"),

    # Japanese
    _gnews("内装工事",                       "ja", "JP"),
    _gnews("内装工事 オフィス",               "ja", "JP"),
    _gnews("店舗内装工事",                   "ja", "JP"),
    _gnews("テナント工事",                   "ja", "JP"),
    _gnews("内装仕上げ工事",                 "ja", "JP"),

    # Chinese (Simplified / Traditional)
    _gnews("室内装修工程",                   "zh-CN", "CN"),
    _gnews("装饰装修工程",                   "zh-CN", "CN"),
    _gnews("办公室装修",                     "zh-CN", "CN"),
    _gnews("商业内装",                       "zh-TW", "TW"),
    _gnews("室內裝修工程",                   "zh-TW", "HK"),

    # Arabic (AE/SA/QA/EG)
    _gnews("تشطيبات داخلية",               "ar", "AE"),
    _gnews("تشطيب مكاتب",                 "ar", "AE"),
    _gnews("أعمال التشطيب",               "ar", "SA"),
    _gnews("تشطيب فنادق",                 "ar", "SA"),
    _gnews("مقاول تشطيبات",               "ar", "QA"),
    _gnews("تجهيز مكاتب عقد",             "ar", "AE"),

    # US — tenant improvement / build-out (English but distinct terminology)
    _gnews('"tenant improvement" construction',    "en", "US"),
    _gnews('"tenant improvement" fitout',          "en", "US"),
    _gnews('"interior build-out"',                 "en", "US"),
    _gnews('"build-out" office construction',      "en", "US"),
    _gnews('"leasehold improvement" construction', "en", "US"),
    _gnews('"commercial interior" construction',   "en", "US"),
    _gnews('"office renovation" commercial',       "en", "US"),
    _gnews('"TI allowance" construction',          "en", "US"),
    _gnews('"tenant build-out"',                   "en", "US"),
    _gnews('"interior construction" commercial',   "en", "CA"),

    # ── 6. Region-biased Google News ────────────────────────────────────────
    _gnews("fitout",                "en", "GB"),
    _gnews('"fit-out"',             "en", "GB"),
    _gnews("fitout",                "en", "AU"),
    _gnews("fitout",                "en", "AE"),
    _gnews("fitout",                "en", "SG"),
    _gnews("fitout",                "en", "IN"),
    _gnews("fitout",                "en", "ZA"),
    _gnews("fitout",                "en", "IE"),
    _gnews("fitout",                "en", "NZ"),
    _gnews("fitout",                "en", "CA"),
    _gnews("fitout",                "en", "NG"),
    _gnews("fitout",                "en", "KE"),
    _gnews("fitout",                "en", "US"),
    _gnews("fitout",                "ar", "QA"),
    _gnews("fitout",                "ar", "SA"),
    _gnews('"design and build" interior', "en", "US"),
    _gnews('"design and build" interior', "en", "GB"),
    _gnews("interiorismo comercial",    "es", "ES"),
    _gnews("interiorismo comercial",    "es", "MX"),
    _gnews('"fit-out"',             "zh", "HK"),
    _gnews('"fit-out" interior',    "pt", "BR"),
    _gnews("Innenausbau",           "de", "DE"),
    _gnews("aménagement intérieur bureau", "fr", "FR"),

    # ── 7. Company tracking — established ────────────────────────────────────
    # UK / Europe leaders
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
    # Middle East
    _gnews('"Depa Group" OR "Depa Interiors"'),
    _gnews('"ALEC Fitout" OR "ALEC fit-out"'),
    _gnews('"Havelock One"'),
    _gnews('"A&T Group Interiors" OR "AT Group Interiors"'),
    _gnews('"AMAQ Interiors"'),
    _gnews('"MGM Interiors"'),
    _gnews('"Abra" fitout Dubai'),
    _gnews('"INC Group" fitout'),
    _gnews('"Summertown Interiors"'),
    # Americas
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
    # Oceania
    _gnews('"Lendlease" fitout OR interior'),
    _gnews('"Schiavello" fitout'),
    _gnews('"Buildcorp" fitout'),
    _gnews('"Multiplex" fitout'),
    _gnews('"Greater Group" fitout'),
    _gnews('"Futurespace" fitout OR workplace'),
    _gnews('"Intermain" fitout OR commercial'),
    # Asia
    _gnews('"Legend Interiors" fitout'),
    _gnews('"LWK Partners" OR "LWK + Partners" interior'),
    # Advisory / cost / real estate
    _gnews('"Cushman & Wakefield" fitout'),
    _gnews('"JLL" fitout OR "Jones Lang LaSalle" fit-out'),
    _gnews('"Savills" fitout OR "Savills" interior'),
    # Spain / Europe boutique
    _gnews('"Martínez Otero" OR "Martinez Otero" interior'),
    _gnews('"Empty" interior design Spain OR "Empty Studio" interiors'),
    _gnews('"Cador" fitout OR "Cador" interiors Belgium'),
    # UK additional
    _gnews('"Beck Interiors" fitout'),
    _gnews('"The Hub" fitout OR "The Hub" exhibition'),
    # Middle East additional
    _gnews('"Bond Interiors" fitout UAE'),
    _gnews('"Saudi Icon" fitout Riyadh'),
    # Northern Ireland cluster
    _gnews('"GEM Interior Contracts" OR "GEM Interiors" fitout'),
    _gnews('"Marcon Fit-Out" OR "Marcon fitout"'),
    _gnews('"CCL Interiors" Belfast'),
    _gnews('"Bradagh Interiors"'),
    # Netherlands / exhibitions
    _gnews('"Bruns" museum exhibition interiors'),
    _gnews('"Hypsos" museum exhibition OR "Hypsos" brand experience'),
    # Northern Ireland cluster — additional
    _gnews('"Mivan" fitout OR "Mivan" joinery OR "Mivan" interiors'),
    # KSA cultural / leisure
    _gnews('"Craft Group" Saudi Arabia OR "Craft Group" AlUla OR craft.group'),
    _gnews('"Saudi Icon" fitout OR "Saudi Icon" interiors'),
    # Spain / Portugal cluster
    _gnews('"Sutega" fitout OR "Sutega" interior OR "Sutega" obras'),
    _gnews('"STGGroup" fitout OR "STG Group" interior'),
    _gnews('"Transfor Interiores" OR "Transfor" fitout Portugal'),
    _gnews('"TDGI" SpaceUp OR "TDGI" interior OR "Teixeira Duarte" fitout'),
    _gnews('"FOX Fitout" hotel OR "FOX Fitout" hospitality OR "FOX Fitout" Portugal'),
    _gnews('"Fitout Icon" Portugal OR "Fitout Icon" Lisbon interior'),
    _gnews('"Muhtaseb Ferreira" OR "Muhtaseb & Ferreira" interior Porto'),
    # Qatar / MENA
    _gnews('"Elegancia Fit-Out" OR "Elegancia" Estithmar interior'),
    _gnews('"Domopan" fitout OR "Domopan" Qatar interior'),
    # Germany / Europe
    _gnews('"Lindner Group" fitout OR "Lindner" interior fit-out'),
    _gnews('"Apleona" fitout OR "Apleona R&M" interior fit-out'),
    # Italy luxury
    _gnews('"Italian Fit Out" OR "IFO" luxury hotel interior fitout'),
    # UAE growing contractors
    _gnews('"Motif Interiors" fitout Dubai'),
    _gnews('"Eire Gulf" fitout OR "Eire Gulf" interior Dubai'),
    _gnews('"Cubics Design" fitout OR "Cubics" interior Dubai'),
    # Africa
    _gnews('"Trend Group" fitout Africa OR "Trend Group" Johannesburg interior'),
    _gnews('"Planning Interiors" Nairobi fitout OR "Planning Interiors" Kenya'),
    _gnews('"Storeplay" shopfitting OR "Storeplay" fitout Africa'),
    _gnews('"Creation Ltd" Nairobi fitout OR "Creation" Kenya interior design'),
    # Southeast Asia
    _gnews('"DB&B" fitout Singapore OR "Design Build" fitout Singapore office'),
    _gnews('"DSG" Singapore fitout OR "DS Group" interior Singapore'),

    # ── 8. Industry RSS feeds ────────────────────────────────────────────────
    # 8a. Specialist fit-out / commercial construction trade publications
    # (added to TRUSTED_RSS_DOMAINS — relevance filter bypassed).
    "https://www.interiorsmonthly.co.uk/feed/",      # UK contract interiors trade
    # bdonline.co.uk removed — general architecture, too many false positives
    "https://contractormagazine.com.au/feed",        # AU fit-out/construction
    "https://www.meed.com/feeds/rss/all-articles",   # ME projects
    "https://www.contractjournal.com/feed/",         # UK contracts
    "https://www.bdcnetwork.com/rss.xml",            # US building design + construction
    "https://www.interiorsandsources.com/feed/",     # US contract interiors
    "https://www.commercialdesign.in/feed/",         # IN commercial interiors
    "https://www.commercialinteriordesign.com/feed/",# ME/GCC commercial interiors
    "https://www.constructionworld.in/feed/",        # IN construction
    "https://www.cnbcafrica.com/feed/",              # Africa: construction/commercial
    "https://www.buildingdesignandconstruction.com/feed/", # US: building design

    # 8b. Prestige architecture & interior design publications
    # These are broad consumer/design titles — NOT in TRUSTED_RSS_DOMAINS.
    # The standard relevance filter applies: only articles that contain fit-out
    # keywords (fitout, fit-out, interior contractor, shopfitting, etc.) will pass.
    # Domus, Frame, Gray and World of Interiors have no accessible RSS feed.
    "https://feeds.feedburner.com/dezeen",           # Dezeen — global design/architecture
    "https://www.designboom.com/feed/",              # Designboom — design & interiors
    "https://www.wallpaper.com/rss",                 # Wallpaper* — design & interiors
    "https://www.interiordesign.net/rss/",           # Interior Design (US contract market)
    "https://www.elledecor.com/rss/all.xml/",        # Elle Decor — luxury interiors
    "https://www.architecturaldigest.com/feed/rss",  # Architectural Digest (US)
    "https://www.architecturaldigest.in/feed/rss",   # Architectural Digest India
    "https://www.ad-magazin.de/feed/rss",            # AD Germany (DACH market)
    "https://sleeper.media/feed/",                   # Sleeper — hotel design
    "https://www.surfacemag.com/feed/",              # Surface — design/culture
    "https://www.azuremagazine.com/feed/",           # Azure — architecture & design (CA)
    "https://www.iconeye.com/feed/",                 # Icon Magazine — design & architecture
    "https://metropolismag.com/feed/",               # Metropolis — design & architecture
    "https://www.designweek.co.uk/feed/",            # Design Week UK — commercial design
    "https://hospitalitydesign.com/feed/",           # Hospitality Design — hotel interiors
    "https://www.indesignlive.com/feed",             # Indesign Live — AU/NZ commercial interiors
    "https://www.livingetc.com/feeds.xml",           # Livingetc — interiors (UK)
    "https://www.housebeautiful.com/rss/all.xml/",   # House Beautiful — residential interiors
    "https://feeds.feedburner.com/DesignMilk",       # Design Milk — design & interiors

    # ── 9. Intelligence sources — major RE/consulting firms ──────────────────
    # These are tracked for fit-out news AND cost-intelligence reports.

    # Global Big 5 RE advisory firms
    _gnews('"Cushman & Wakefield" fit-out OR "Cushman" interior construction'),
    _gnews('"Knight Frank" fit-out OR "Knight Frank" interior construction'),
    _gnews('"Savills" fit-out construction'),
    _gnews('"Colliers" fit-out OR "Colliers" interior'),
    _gnews('"Newmark" fit-out OR "Newmark" interior'),
    _gnews('"Avison Young" fit-out OR "Avison Young" interior'),
    _gnews('"BNP Paribas Real Estate" fit-out OR interior construction'),
    _gnews('"Marcus & Millichap" fit-out OR construction'),
    _gnews('"Eastdil Secured" fit-out OR real estate'),
    _gnews('"Walker & Dunlop" construction OR fit-out'),
    _gnews('"Berkadia" construction OR fit-out'),

    # Cost consultants / project management
    _gnews('"Turner & Townsend" fit-out OR "Turner Townsend" construction cost'),
    _gnews('"AECOM" fit-out OR interior construction'),
    _gnews('"Arcadis" fit-out OR interior construction cost'),
    _gnews('"Arup" fit-out OR interior construction'),
    _gnews('"Buro Happold" fit-out OR interior'),
    _gnews('"Linesight" fit-out OR construction cost'),
    _gnews('"BCQS International" fit-out OR construction'),
    _gnews('"RLB" fit-out OR "Rider Levett Bucknall" construction'),
    _gnews('"Drees & Sommer" fit-out OR interior construction'),
    _gnews('"KEO" fit-out OR interior construction'),

    # Middle East specialists
    _gnews('"ValuStrat" fit-out OR construction cost'),
    _gnews('"MPM Properties" fit-out OR construction UAE'),
    _gnews('"Cavendish Maxwell" fit-out OR construction'),
    _gnews('"Mirage" fitout OR interior Dubai'),
    _gnews('"Compass" fit-out OR interior construction'),

    # Global architecture / design-build
    _gnews('"Gensler" fit-out OR interior construction cost'),
    _gnews('"HOK" fit-out OR interior construction'),
    _gnews('"Hines" fit-out OR interior construction'),

    # Consulting / advisory (global)
    _gnews('"Deloitte" fit-out real estate OR "Deloitte" construction cost'),
    _gnews('"KPMG" fit-out real estate OR "KPMG" construction cost'),
    _gnews('"PwC" fit-out real estate OR "PwC" construction cost'),
    _gnews('"McKinsey" fit-out OR workplace construction'),
    _gnews('"Boston Consulting Group" fit-out OR BCG workplace construction'),
    _gnews('"Roland Berger" fit-out OR construction cost'),
    _gnews('"EY" Ernst Young fit-out real estate'),
    _gnews('"CohnReznick" fit-out OR construction cost'),
    _gnews('"RCLCO" fit-out OR construction'),

    # Americas — developers / REITs
    _gnews('"Tishman Speyer" fit-out OR interior construction'),
    _gnews('"Brookfield Properties" fit-out OR construction'),
    _gnews('"Prologis" fit-out OR industrial construction'),
    _gnews('"Greystar" fit-out OR interior construction'),
    _gnews('"Trammell Crow" fit-out OR interior'),
    _gnews('"Lincoln Property" fit-out OR interior'),
    _gnews('"Related Companies" fit-out OR interior'),
    _gnews('"Simon Property Group" fit-out OR retail construction'),
    _gnews('"Equinix" data centre fit-out OR data center fitout'),
    _gnews('"American Tower" fit-out OR construction'),
    _gnews('"Welltower" fit-out OR interior'),
    _gnews('"Public Storage" fit-out OR construction'),
    _gnews('"Lennar" fit-out OR residential construction'),
    _gnews('"D.R. Horton" fit-out OR construction'),

    # Americas — Latin America
    _gnews('"Cyrela Brazil Realty" fit-out OR construction'),
    _gnews('"MRV Engenharia" fit-out OR construction'),
    _gnews('"Pactia" fitout OR interiorismo Colombia'),
    _gnews('"Habi" fit-out OR interior Colombia'),
    _gnews('"La Haus" fit-out OR interior'),
    _gnews('"Fibra Prologis" fit-out OR construction Mexico'),
    _gnews('"Corporación Inmobiliaria Vesta" fit-out OR construction'),
    _gnews('"Empresas ICA" fit-out OR construction Mexico'),
    _gnews('"Andrade Gutierrez" fit-out OR construction Brazil'),

    # Asia Pacific — developers / REITs
    _gnews('"CapitaLand" fit-out OR interior construction'),
    _gnews('"Mitsubishi Estate" fit-out OR interior construction Japan'),
    _gnews('"Mitsui Fudosan" fit-out OR interior Japan'),
    _gnews('"Frasers Property" fit-out OR interior construction'),
    _gnews('"Keppel REIT" fit-out OR interior Singapore'),
    _gnews('"Henderson Land" fit-out OR interior Hong Kong'),
    _gnews('"Sun Hung Kai" fit-out OR interior Hong Kong'),
    _gnews('"New World Development" fit-out OR interior'),
    _gnews('"DLF" fit-out OR interior India'),
    _gnews('"Tata Realty" fit-out OR interior India'),
    _gnews('"City Developments" CDL fit-out OR interior Singapore'),
    _gnews('"PropNex" fit-out OR interior Singapore'),
    _gnews('"Juwai IQI" fit-out OR interior Malaysia'),
    _gnews('"ANAROCK" fit-out OR interior India'),
    _gnews('"Dat Xanh" fit-out OR interior Vietnam'),
    _gnews('"Country Garden" fit-out OR interior construction'),

    # Australia / New Zealand
    _gnews('"Lendlease" fit-out OR interior construction'),
    _gnews('"Mirvac" fit-out OR interior construction'),
    _gnews('"Stockland" fit-out OR interior construction'),
    _gnews('"Dexus" fit-out OR interior construction'),
    _gnews('"Scentre Group" fit-out OR retail construction'),
    _gnews('"GPT Group" fit-out OR interior construction'),
    _gnews('"Vicinity Centres" fit-out OR retail construction'),
    _gnews('"Ray White" fit-out OR construction'),
    _gnews('"Bayleys" fit-out OR construction New Zealand'),
    _gnews('"Barfoot Thompson" fit-out OR interior New Zealand'),
    _gnews('"Harcourts" fit-out OR construction'),
    _gnews('"Cbus Property" fit-out OR construction'),
    _gnews('"Metricon" fit-out OR residential construction'),
    _gnews('"Multiplex" fit-out OR construction Australia'),
    _gnews('"Billbergia" fit-out OR construction Australia'),

    # Africa
    _gnews('"Logan" fit-out OR construction Africa'),

    # ── 10. New companies added 2026-05 ──────────────────────────────────────
    # Switzerland / Exhibition specialists
    _gnews('"NUSSLI" exhibition OR museum OR fit-out'),
    _gnews('"Nussli Group" construction OR exhibition'),

    # Germany / Event technology
    _gnews('"Neumann Müller" exhibition OR event technology'),
    _gnews('"Neumann & Müller" fit-out OR exhibition'),

    # Spain / Cultural fit-out
    _gnews('"ACCIONA Cultura" museum OR fit-out OR exhibition'),
    _gnews('"Acciona Cultura" construction OR cultural'),

    # Montenegro / Global PM
    _gnews('"DPM Global" fit-out OR hotel construction'),

    # UAE — Middle East power list firms
    _gnews('"Khansaheb Interiors" fit-out OR construction'),
    _gnews('"Khansaheb" interior fit-out Dubai'),
    _gnews('"HTS Interiors" fit-out OR interior Dubai'),
    _gnews('"Mouhajer International" fit-out OR interior'),
    _gnews('"MIDC" luxury interior Dubai fit-out'),
    _gnews('"i2D Interior" fit-out OR i2D interiors Dubai'),
    _gnews('"Pinnacle Interiors" fit-out Dubai'),
    _gnews('"Group IMAR" fit-out OR interior UAE'),

    # Additional globally significant fit-out firms
    _gnews('"Khansaheb" fit-out award'),
    _gnews('"Acciona" museum fit-out OR cultural construction'),

    # Spain — Hotel fit-out specialists
    _gnews('"Proffetional" hotel fit-out OR interior'),
    _gnews('"Proffetional Finishing Design" hotel'),
    _gnews('"FLULLE" fit-out OR installation Spain'),
    _gnews('"Flulle" interior construction Spain'),

    # Italy — Engineering & construction
    _gnews('"RIMOND" construction OR fit-out OR engineering'),
    _gnews('"Rimond" interior Milan OR Italy'),

    # ── 11. D&P and RIB Contracts ────────────────────────────────────────────
    _gnews('"Design and Production Incorporated" museum OR exhibit OR fit-out'),
    _gnews('"D&P" museum fabrication OR exhibit install'),
    _gnews('"RIB Contracts" fit-out OR joinery OR interior'),
    _gnews('"RIB Contracts Limited" hotel OR museum OR residential'),

    # ── 12. Major contractors batch (2026-05) ─────────────────────────────────
    # UK & Ireland
    _gnews('"Laing O\'Rourke" fit-out OR interiors'),
    _gnews('"Balfour Beatty" fit-out OR interiors OR workplace'),
    _gnews('"Kier Group" fit-out OR interiors'),
    _gnews('"Galliford Try" fit-out OR building'),
    _gnews('"John Sisk" fit-out OR interiors OR data centre'),
    _gnews('"Morgan Sindall" fit-out OR interiors'),
    _gnews('"GRAHAM" construction fit-out OR interiors'),
    _gnews('"McAleer & Rushe" hotel fit-out OR construction'),
    _gnews('"Bowmer Kirkland" fit-out OR interiors'),
    _gnews('"Claremont" office fit-out OR workplace'),
    # Continental Europe
    _gnews('"STRABAG" fit-out OR interior construction'),
    _gnews('"PORR" fit-out OR interiors'),
    _gnews('"Implenia" fit-out OR interiors'),
    _gnews('"Eiffage" fit-out OR interiors'),
    _gnews('"BESIX" fit-out OR interiors'),
    _gnews('"Heijmans" fit-out OR interiors'),
    _gnews('"Royal BAM" fit-out OR interiors'),
    _gnews('"NCC AB" fit-out OR interiors'),
    _gnews('"Peab" fit-out OR interiors'),
    _gnews('"Veidekke" fit-out OR interiors'),
    _gnews('"YIT" fit-out OR interiors'),
    _gnews('"Budimex" fit-out OR interiors'),
    # Turkey
    _gnews('"TAV Construction" fit-out OR airport'),
    _gnews('"Tekfen" fit-out OR construction'),
    _gnews('"Rönesans" fit-out OR construction'),
    _gnews('"Enka" fit-out OR construction'),
    # Middle East
    _gnews('"Saudi Binladin" fit-out OR interiors'),
    _gnews('"El Seif" fit-out OR interiors'),
    _gnews('"Al Habtoor" hotel fit-out OR construction'),
    _gnews('"Al Shafar Interiors" fit-out Dubai'),
    _gnews('"Consolidated Contractors" CCC fit-out OR building'),
    _gnews('"Eversendai" fit-out OR steel works'),
    # India
    _gnews('"Larsen Toubro" fit-out OR interiors'),
    _gnews('"Shapoorji Pallonji" fit-out OR interiors'),
    _gnews('"Tata Projects" fit-out OR interiors'),
    # Japan
    _gnews('"Obayashi" fit-out OR interiors Japan'),
    _gnews('"Kajima" fit-out OR interiors Japan'),
    _gnews('"Shimizu Corporation" fit-out OR interiors'),
    _gnews('"Taisei" fit-out OR interiors'),
    _gnews('"Takenaka" fit-out OR interiors'),
    # Korea
    _gnews('"Samsung C&T" fit-out OR construction'),
    _gnews('"Hyundai E&C" fit-out OR construction'),
    # Australia / NZ
    _gnews('"Built" construction fit-out Australia'),
    _gnews('"John Holland" fit-out OR interiors'),
    _gnews('"Kane Constructions" fit-out OR interiors'),
    _gnews('"Hickory Group" fit-out OR modular'),
    _gnews('"Warren Mahoney" fit-out OR interiors'),
    # Global Interiors & Workplace
    _gnews('"M Moser" fit-out OR workspace'),
    _gnews('"Unispace" fit-out OR workspace'),
    _gnews('"CallisonRTKL" fit-out OR interiors'),
    _gnews('"Woods Bagot" fit-out OR interiors'),
    _gnews('"ChapmanTaylor" fit-out OR interiors'),
    _gnews('"Aedas" fit-out OR interiors'),
    _gnews('"Nelson Worldwide" fit-out OR interiors'),
    _gnews('"Broadway Malyan" fit-out OR interiors'),
    # QS / PM
    _gnews('"Gleeds" fit-out OR cost'),
    _gnews('"Currie Brown" fit-out OR cost'),
    _gnews('"Rider Levett Bucknall" fit-out OR cost'),
    _gnews('"Turner Townsend" fit-out OR cost'),
    _gnews('"Faithful Gould" fit-out OR cost'),
    # US contractors
    _gnews('"DPR Construction" fit-out OR interiors'),
    _gnews('"Swinerton" fit-out OR tenant improvement'),
    _gnews('"Clark Construction" fit-out OR interiors'),
    _gnews('"McCarthy Building" fit-out OR interiors'),
    _gnews('"Gilbane" fit-out OR interiors'),
    _gnews('"Suffolk Construction" fit-out OR interiors'),
    # US — city-level market queries (high-volume markets)
    _gnews('"office fit-out" OR "office fitout" "New York"',        "en", "US"),
    _gnews('"office fit-out" OR "office fitout" Chicago',           "en", "US"),
    _gnews('"office fit-out" OR "office fitout" "Los Angeles"',     "en", "US"),
    _gnews('"tenant improvement" "New York" commercial',            "en", "US"),
    _gnews('"tenant improvement" Chicago commercial',               "en", "US"),
    _gnews('"tenant improvement" "San Francisco" commercial',       "en", "US"),
    _gnews('"spec suite" commercial construction',                  "en", "US"),
    _gnews('"vanilla box" OR "grey box" commercial interior',       "en", "US"),
    _gnews('"white box" commercial interior construction',          "en", "US"),
    _gnews('"office build-out" OR "office buildout" commercial',    "en", "US"),
    _gnews('"commercial interior" construction "United States"',    "en", "US"),
    _gnews('"leasehold improvement" construction commercial',       "en", "US"),
    _gnews('"workplace design" "New York" OR Chicago OR "San Francisco"', "en", "US"),
    _gnews('"interior construction" commercial office',             "en", "US"),
    _gnews('"office restack" OR "office consolidation" commercial', "en", "US"),
    _gnews('"workplace transformation" United States',              "en", "US"),
    _gnews('"design-build" interior commercial United States',      "en", "US"),
    # Canada
    _gnews('"fit-out" OR "fitout" Toronto commercial',              "en", "CA"),
    _gnews('"fit-out" OR "fitout" Vancouver commercial',            "en", "CA"),
    _gnews('"tenant improvement" Toronto OR Vancouver OR Calgary',  "en", "CA"),
    _gnews('"commercial interior" construction Canada',             "en", "CA"),
    # Brazil
    _gnews('"fit out" OR "fitout" corporativo Brazil',             "pt", "BR"),
    _gnews('reforma escritório comercial "São Paulo"',             "pt", "BR"),
    _gnews('"interiores comerciais" construção',                   "pt", "BR"),
    _gnews('"escritório corporativo" reforma OR construção',       "pt", "BR"),
    # Mexico
    _gnews('"fit out" OR "fitout" oficinas Mexico',               "es", "MX"),
    _gnews('"interiores comerciales" construcción Mexico',        "es", "MX"),
    _gnews('"remodelación de oficinas" comercial Mexico',         "es", "MX"),
    # Japan
    _gnews('"オフィス内装" OR "フィットアウト" 工事',             "ja", "JP"),
    _gnews('"内装工事" オフィス 商業',                            "ja", "JP"),
    # South Korea
    _gnews('"인테리어" "피트아웃" OR "사무실 인테리어" 공사',      "ko", "KR"),
    # Singapore / Hong Kong
    _gnews('"DP Architects" fit-out OR interiors'),
    _gnews('"Surbana Jurong" fit-out OR interiors'),
    _gnews('"Hip Hing" fit-out OR construction'),
    _gnews('"fit-out" OR "fitout" Singapore commercial',            "en", "SG"),
    _gnews('"interior fit-out" Hong Kong commercial',               "en", "HK"),
    _gnews('"fit-out" "data centre" OR "data center" Singapore OR Asia'),
]

# ─────────────────────────────────────────────────────────────────────────────
#  Relevance filter  (expanded in v2)
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
#  Source quality scoring
# ─────────────────────────────────────────────────────────────────────────────
# Tier-1 sources get a recency boost so they surface above same-age noise.
# Scores are added to a virtual "quality hours" offset when sorting.
# A score of 24 means a tier-1 article sorts as if it were 24 hours more recent.

SOURCE_QUALITY: dict[str, int] = {
    # Global advisory / research firms
    "jll":                          36,
    "cbre":                         36,
    "cushman & wakefield":          36,
    "savills":                      36,
    "knight frank":                 36,
    "colliers":                     30,
    "jones lang lasalle":           36,
    # Industry-specific trade press (high signal)
    "construction news":            24,
    "architects' journal":          24,
    "dezeen":                       20,
    "architectural record":         20,
    "interior design":              20,
    "interiors monthly":            20,
    "fit out magazine":             24,
    "mixinteriors":                 20,
    "workplace insight":            18,
    "bdcnetwork":                   18,
    "engineering news-record":      18,
    "meed":                         24,
    "construction week":            18,
    "arabian business":             16,
    "commercial interior design":   18,
    "design middle east":           18,
    "indesign live":                16,
    "architecture & design":        16,
    # Mainstream business / financial press
    "financial times":              30,
    "bloomberg":                    30,
    "reuters":                      28,
    "the guardian":                 20,
    "the times":                    20,
    "the telegraph":                18,
    "wall street journal":          28,
    "business insider":             16,
    "forbes":                       16,
    "connect cre":                  16,
    "rebusinessonline":             16,
}

def source_quality_score(source: str) -> int:
    """Return quality boost in virtual hours for a given source name."""
    src_l = source.lower()
    for key, score in SOURCE_QUALITY.items():
        if key in src_l:
            return score
    return 0


# ─────────────────────────────────────────────────────────────────────────────
#  Geo-detection helpers
# ─────────────────────────────────────────────────────────────────────────────

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


# Source-name → country fallback (for publications without geo in headlines)
SOURCE_COUNTRY_DEFAULTS: dict[str, str] = {
    # UK trade press
    "architects' journal":           "United Kingdom",
    "the architects' journal":       "United Kingdom",
    "interiors monthly":             "United Kingdom",
    "construction enquirer":         "United Kingdom",
    "construction news":             "United Kingdom",
    "building.co.uk":                "United Kingdom",
    "building design":               "United Kingdom",
    "contract journal":              "United Kingdom",
    "insider media":                 "United Kingdom",
    "thebusinessdesk":               "United Kingdom",
    "belfast telegraph":             "United Kingdom",
    "scottish construction now":     "United Kingdom",
    "construction index":            "United Kingdom",
    "fit out magazine":              "United Kingdom",
    "building better healthcare":    "United Kingdom",
    "hospital design":               "United Kingdom",
    "workplace insight":             "United Kingdom",
    "facilitiesnet":                 "United Kingdom",
    "furniture news":                "United Kingdom",
    "mixinteriors":                  "United Kingdom",
    "mixdesign":                     "United Kingdom",
    "officelovin":                   "United Kingdom",
    "officeinteriors":               "United Kingdom",
    # US publications
    "bdcnetwork":                    "United States",
    "enr":                           "United States",
    "engineering news-record":       "United States",
    "interiors and sources":         "United States",
    "connect cre":                   "United States",
    "rebusinessonline":              "United States",
    "costar":                        "United States",
    "bisnow":                        "United States",
    "globest":                       "United States",
    "commercialsearch":              "United States",
    "commercial observer":           "United States",
    "workdesign":                    "United States",
    "officedesign":                  "United States",
    # Middle East
    "commercial interior design":    "United Arab Emirates",
    "design middle east":            "United Arab Emirates",
    "construction week online":      "United Arab Emirates",
    "construction week":             "United Arab Emirates",
    "construction business news middle east": "United Arab Emirates",
    "meed":                          "United Arab Emirates",
    "arabian business":              "United Arab Emirates",
    "gulf business":                 "United Arab Emirates",
    "zawya":                         "United Arab Emirates",
    "trade arabia":                  "United Arab Emirates",
    "hospitality net":               "United Arab Emirates",
    # Australia
    "contractor magazine":           "Australia",
    "architecture & design":         "Australia",
    "indesign live":                 "Australia",
    "indesignlive":                  "Australia",
    "australiandesignreview":        "Australia",
    "sourceable":                    "Australia",
    "theurbandeveloper":             "Australia",
    # India
    "commercial design":             "India",
    "construction world":            "India",
    "design fabric":                 "India",
    "acrex":                         "India",
    # Malaysia / Southeast Asia
    "klse screener":                 "Malaysia",
    "the edge":                      "Malaysia",
    "edge markets":                  "Malaysia",
    "digital news asia":             "Malaysia",
    # Singapore
    "the business times":            "Singapore",
    "straitstimes":                  "Singapore",
    "propertyguru":                  "Singapore",
    # Hong Kong
    "scmp":                          "Hong Kong",
    "south china morning post":      "Hong Kong",
    # Germany
    "marketscreener schweiz":        "Switzerland",
    "marktscreener":                 "Germany",
    "bauzeitung":                    "Germany",
    "baunetz":                       "Germany",
    "derwirtschaftsführer":          "Germany",
    "noticierotextil":               "Spain",
    "le journal des entreprises":    "France",
    "batiactu":                      "France",
    "lemoniteur":                    "France",
    "batirama":                      "France",
}

# Continent-level text signals: if these phrases appear in title/desc/source,
# and we still have no country match, assign the continent directly.
# Order matters — check more specific first.
CONTINENT_TEXT_SIGNALS: list[tuple[str, str]] = [
    ("asia pacific",         "Asia Pacific"),
    ("asia-pacific",         "Asia Pacific"),
    ("apac",                 "Asia Pacific"),
    ("southeast asia",       "Asia Pacific"),
    ("south-east asia",      "Asia Pacific"),
    ("cfotech asia",         "Asia Pacific"),
    ("techasia",             "Asia Pacific"),
    ("middle east",          "Middle East"),
    ("mena region",          "Middle East"),
    ("gulf region",          "Middle East"),
    ("gcc region",           "Middle East"),
    ("sub-saharan africa",   "Africa"),
    ("subsaharan africa",    "Africa"),
    ("techafric",            "Africa"),
    ("africa news",          "Africa"),
    ("latin america",        "Americas"),
    ("latin-america",        "Americas"),
    ("south america",        "Americas"),
    ("north america",        "Americas"),
    ("central america",      "Americas"),
    ("nordics",              "Europe"),
    ("scandinavia",          "Europe"),
    ("eastern europe",       "Europe"),
    ("western europe",       "Europe"),
]

# Non-English geo terms that translate to a country
FOREIGN_GEO_TERMS: dict[str, str] = {
    # German
    "deutschen":     "Germany",
    "deutschen markt": "Germany",
    "deutschen":     "Germany",
    "schweiz":       "Switzerland",
    "österreich":    "Austria",
    "niederlande":   "Netherlands",
    # Spanish
    "alemán":        "Germany",
    "alemana":       "Germany",
    "españa":        "Spain",
    "reino unido":   "United Kingdom",
    "emiratos":      "United Arab Emirates",
    # French
    "bretonne":      "France",
    "bretagne":      "France",
    "française":     "France",
    "français":      "France",
    "belge":         "Belgium",
    # Italian
    "italiana":      "Italy",
    "italiano":      "Italy",
}


def detect_country_from_foreign_terms(text: str) -> str | None:
    text_l = text.lower()
    for term, country in FOREIGN_GEO_TERMS.items():
        if term in text_l:
            return country
    return None


def resolve_geo(title: str, description: str, url: str, source: str) -> tuple[str, str]:
    """Return (country, continent) for an article.

    Detection priority:
    1. Geographic name in title + description + source (English)
    2. TLD of publisher URL
    3. Known source → country mapping
    4. Non-English geo terms in combined text
    5. Continent-level text signals (Asia Pacific, Middle East, etc.)
    6. Falls back to "Global"
    """
    combined = f"{title}  {description}  {source}"
    country = detect_country_from_text(combined) or detect_country_from_url(url)
    if not country:
        # Try source-name lookup (case-insensitive partial match)
        src_l = source.lower()
        for key, default_country in SOURCE_COUNTRY_DEFAULTS.items():
            if key in src_l:
                country = default_country
                break
    if not country:
        country = detect_country_from_foreign_terms(combined)
    if country:
        continent = COUNTRY_TO_CONTINENT.get(country.lower(), "Global")
        return country, continent
    # Try continent-level signals before falling back to Global
    combined_l = combined.lower()
    for signal, continent in CONTINENT_TEXT_SIGNALS:
        if signal in combined_l:
            return "", continent
    return "Global", "Global"


# ─────────────────────────────────────────────────────────────────────────────
#  Feed parsing  (with retry)
# ─────────────────────────────────────────────────────────────────────────────

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
    """Return (display_name, publisher_url) for a feed entry.

    For Google News RSS each entry carries a <source> element with the
    actual publisher's title and href — far more useful than the feed title.
    """
    src = entry.get("source", {})
    name = src.get("title") or feed_title
    href = src.get("href", "")
    return name, href


def fetch_feed(url: str, seen: set[str], max_retries: int = 1) -> list[dict]:
    articles = []
    # Trusted industry RSS domains bypass the MUST_HAVE relevance filter
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    trusted = domain in TRUSTED_RSS_DOMAINS

    for attempt in range(1, max_retries + 1):
        try:
            log.info("Fetching %s  (attempt %d)", url[:90], attempt)
            feed = feedparser.parse(
                url,
                request_headers={"User-Agent": "FitOutPost/2.0 (news aggregator; +fitoutpost.com)"},
            )
            feed_title = (
                feed.feed.get("title", urlparse(url).netloc) if feed.feed else urlparse(url).netloc
            )

            for entry in feed.entries:
                link = entry.get("link", "").strip()
                if not link or link in seen:
                    continue

                # Block articles from known noisy domains regardless of which feed surfaced them
                article_domain = urlparse(link).netloc.lower().removeprefix("www.")
                if article_domain in BLOCKED_ARTICLE_DOMAINS:
                    continue

                title = _clean_html(entry.get("title", ""))
                desc  = _clean_html(entry.get("summary", entry.get("description", "")))
                if not title:
                    continue
                # Trusted industry RSS feeds are accepted without MUST_HAVE check
                if not trusted and not is_relevant(title, desc):
                    continue

                source_name, publisher_url = _entry_source(entry, feed_title)
                geo_url = publisher_url or link
                country, continent = resolve_geo(title, desc, geo_url, source_name)
                seen.add(link)

                clean_desc = _clean_description(title, desc, source_name)
                if clean_desc and len(clean_desc) > 350:
                    clean_desc = clean_desc[:350] + "…"

                articles.append({
                    "id":           hashlib.md5(link.encode()).hexdigest()[:10],
                    "title":        title,
                    "url":          link,
                    "source":       source_name,
                    "published":    _parse_date(entry),
                    "description":  clean_desc,
                    "country":      country,
                    "continent":    continent,
                    "signal_type":  classify_signal(title, clean_desc),
                    "quality":      source_quality_score(source_name),
                })

            break  # success

        except Exception as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, max_retries, url[:60], exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)   # exponential back-off: 2 s, 4 s

    return articles


# ─────────────────────────────────────────────────────────────────────────────
#  Signal type classification
# ─────────────────────────────────────────────────────────────────────────────

_SIGNAL_RULES: list[tuple[str, list[str]]] = [
    ("Contract Win", [
        "awarded contract", "wins contract", "won contract", "win contract",
        "secures contract", "secured contract", "bags contract", "lands contract",
        "clinches contract", "appointed contractor", "appoints contractor",
        "signs contract", "signed contract", "contract win", "fitout contract",
        "fit-out contract", "appointed to deliver", "appointed to fit",
        "appointed to refurbish", "contractor appointed", "contractor selected",
        "main contractor", "selected as contractor", "awarded fit-out",
        "awarded the contract", "interior contract", "contract awarded",
        # broader patterns: "[company] wins fit-out", "wins fit out contract"
        "wins fit", "win fit", "won fit", "secures fit", "secured fit",
        "bags fit", "lands fit", "awarded fit", "clinches fit",
    ]),
    ("Project Announcement", [
        "breaks ground", "groundbreaking", "construction begins", "construction starts",
        "work begins", "work starts", "fit-out begins", "fit-out starts",
        "fitout begins", "opening soon", "set to open", "due to open",
        "will open", "announced plans", "announces plans", "unveiled",
        "new hotel", "new office", "new store", "new branch", "new location",
        "new flagship", "expansion plans", "to be built", "under construction",
        "planning application", "planning permission", "planning consent",
        "development approved", "project announced",
    ]),
    ("Market Data", [
        "cost guide", "cost index", "cost report", "market report",
        "market forecast", "market size", "market growth", "market value",
        "market data", "benchmark", "survey reveals", "research finds",
        "study shows", "statistics", "per square", "per sq", "$/m²",
        "per sqm", "cost per", "billion", "million sqft", "index 2025",
        "index 2026", "outlook 2025", "outlook 2026", "forecast 2025",
        "forecast 2026", "trend report", "annual report", "white paper",
        "industry report", "q1 ", "q2 ", "q3 ", "q4 ",
    ]),
    ("Company News", [
        "appoints", "appointed ceo", "appointed director", "promoted to",
        "joins as", "named as", "acquires", "acquisition", "merger",
        "partnership", "joint venture", "strategic alliance", "expands into",
        "opens office", "new office in", "expands to", "launches in",
        "rebrands", "rebrand", "new identity", "new brand",
        "raises funding", "secures funding", "investment round",
        "ipo", "listed on", "goes public",
    ]),
    ("Tender", [
        "tender", "rfp ", "request for proposal", "request for tender",
        "procurement", "bidding process", "bid invitation", "pre-qualification",
        "expression of interest", "eoi ", "competitive tender",
    ]),
    ("Regulation", [
        "regulation", "building code", "building standard", "fire safety",
        "planning law", "legislation", "compliance requirement",
        "environmental standard", "green building", "breeam", "leed",
        "wellbeing standard", "fitwell", "net zero", "embodied carbon",
    ]),
]

def classify_signal(title: str, description: str) -> str:
    """Return the signal type label for an article."""
    combined = (title + " " + description).lower()
    for label, keywords in _SIGNAL_RULES:
        if any(kw in combined for kw in keywords):
            return label
    return "Industry News"


# ─────────────────────────────────────────────────────────────────────────────
#  Description scrubber — strip Google News RSS garbage
# ─────────────────────────────────────────────────────────────────────────────

def _clean_description(title: str, desc: str, source: str) -> str:
    """Remove RSS boilerplate that's not actually useful content.

    Google News RSS summaries often contain:
      - The article title repeated verbatim
      - Just the source name
      - "Title  Source" with no real body text
    We detect these patterns and return an empty string so the template
    can fall back to a clean truncated title instead.
    """
    if not desc:
        return ""

    # Strip excessive whitespace
    d = re.sub(r"\s+", " ", desc).strip()

    # Pattern 1: description IS the source name (possibly with whitespace)
    if d.lower() == source.lower():
        return ""

    # Pattern 2: description is just the title (RSS quirk)
    title_norm = re.sub(r"\s+", " ", title).strip().lower()
    if d.lower() == title_norm:
        return ""

    # Pattern 3: description contains the full title — common in Google News
    # where the summary is "{title}  {source}" or "{source}  {title}  {source}"
    # Heuristic: title appears in desc AND desc is < title + 80 chars → garbage
    if title_norm in d.lower() and len(d) < len(title) + 80:
        return ""

    # Pattern 4: description starts or ends with the source name exactly
    src_l = source.lower()
    d_l = d.lower()
    if d_l.startswith(src_l):
        d = d[len(source):].strip(" -–—|·•,")
    if d_l.endswith(src_l):
        d = d[:-len(source)].strip(" -–—|·•,")

    # If after all cleaning we have less than 30 chars, it's not useful
    if len(d.strip()) < 30:
        return ""

    return d.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  Title-similarity deduplication (within a batch / cross-query)
# ─────────────────────────────────────────────────────────────────────────────

_DEDUP_STOPWORDS = frozenset({
    "the","a","an","in","of","for","and","or","to","at","on","with","by",
    "from","as","is","are","was","its","into","that","this","has","have",
    "be","do","it","not","can","will","but","up","out","all","new","says",
    "said","after","over","about","been","more","how","also","than","one",
})

def _title_fp(title: str) -> frozenset:
    """Significant-word fingerprint for near-duplicate detection."""
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()
    sig = [w for w in words if len(w) > 3 and w not in _DEDUP_STOPWORDS]
    return frozenset(sig[:10])  # cap at 10 to avoid over-matching short titles


def deduplicate_by_title(articles: list[dict]) -> tuple[list[dict], int]:
    """Collapse near-duplicate articles.

    Two articles are duplicates if:
    - Their title fingerprints share ≥ 5 significant words, AND
    - They were published within 72 hours of each other.

    When duplicates are found, keep the article with the longer/better description.
    Returns (deduplicated_list, dropped_count).
    """
    kept: list[dict] = []
    dropped = 0

    for art in articles:
        fp = _title_fp(art["title"])
        if len(fp) < 4:
            # Too short to fingerprint reliably — always keep
            kept.append(art)
            continue

        is_dup = False
        for existing in kept:
            existing_fp = _title_fp(existing["title"])
            overlap = len(fp & existing_fp)
            if overlap >= 5:
                # Check time proximity (within 72 hours)
                try:
                    t_new = art.get("published", "")
                    t_old = existing.get("published", "")
                    if t_new and t_old and abs(
                        datetime.fromisoformat(t_new.replace("Z", "+00:00")).timestamp() -
                        datetime.fromisoformat(t_old.replace("Z", "+00:00")).timestamp()
                    ) < 72 * 3600:
                        # Duplicate — keep the one with better description
                        if len(art.get("description", "")) > len(existing.get("description", "")):
                            kept[kept.index(existing)] = art
                        is_dup = True
                        dropped += 1
                        break
                except Exception:
                    pass

        if not is_dup:
            kept.append(art)

    return kept, dropped


# ─────────────────────────────────────────────────────────────────────────────
#  Cross-run deduplication
# ─────────────────────────────────────────────────────────────────────────────

def load_previous(path: str = "news.json") -> tuple[list[dict], set[str]]:
    """Load articles from a prior run.  Returns (articles, seen_urls)."""
    p = Path(path)
    if not p.exists():
        return [], set()
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        prior = payload.get("articles", [])
        urls  = {a["url"] for a in prior}
        log.info("Loaded %d prior articles from %s", len(prior), path)
        return prior, urls
    except Exception as exc:
        log.warning("Could not read prior %s: %s", path, exc)
        return [], set()


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def fetch_all(keep_days: int = 30) -> list[dict]:
    """Fetch new articles and merge with prior runs, keeping up to keep_days days."""
    prior, seen = load_previous()

    new_articles: list[dict] = []
    accessed_at = datetime.now(timezone.utc).isoformat()

    # Parallel fetch: 20 workers.  Each worker gets a snapshot of 'seen' so
    # intra-run URL dedup happens inside fetch_feed; final URL dedup runs below.
    seen_snapshot = frozenset(seen)

    def _fetch_one(feed_url: str) -> list[dict]:
        local_seen = set(seen_snapshot)
        return fetch_feed(feed_url, local_seen)

    log.info("Fetching %d feeds with 20 parallel workers…", len(RSS_FEEDS))
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(_fetch_one, url): url for url in RSS_FEEDS}
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                batch = future.result()
                for a in batch:
                    a["accessed_at"] = accessed_at
                new_articles.extend(batch)
            except Exception as exc:
                log.warning("Feed worker error: %s", exc)
            if done % 50 == 0:
                log.info("Progress: %d/%d feeds done, %d articles so far",
                         done, len(RSS_FEEDS), len(new_articles))

    # URL-level dedup: drop any article whose URL was already in prior runs
    seen_urls: set[str] = set(seen_snapshot)
    deduped: list[dict] = []
    for a in new_articles:
        u = a.get("url", "")
        if u and u not in seen_urls:
            seen_urls.add(u)
            deduped.append(a)
    new_articles = deduped

    log.info("New articles this run: %d", len(new_articles))

    # Merge: new first, then prior (already deduped via seen set)
    merged = new_articles + prior

    # Trim to keep_days window
    cutoff_ts = datetime.now(timezone.utc).isoformat()[:10]
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
    merged = [a for a in merged if a.get("published", "") >= cutoff]

    # Quality-adjusted sort: tier-1 sources surface as if published N hours later
    from datetime import timedelta
    def _sort_key(a: dict) -> str:
        try:
            pub = datetime.fromisoformat(a["published"].replace("Z", "+00:00"))
            boost = timedelta(hours=a.get("quality", 0))
            return (pub + boost).isoformat()
        except Exception:
            return a.get("published", "")

    merged.sort(key=_sort_key, reverse=True)

    # Title-similarity deduplication (collapses cross-query duplicate stories)
    merged, n_dropped = deduplicate_by_title(merged)
    log.info("Dedup removed %d near-duplicate articles", n_dropped)
    log.info("Total articles after merge + trim + dedup: %d", len(merged))
    return merged


def save(articles: list[dict], path: str = "news.json") -> None:
    payload = {
        "last_updated":   datetime.now(timezone.utc).isoformat(),
        "total_articles": len(articles),
        "articles":       articles,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    log.info("Saved %d articles → %s", len(articles), path)


if __name__ == "__main__":
    art = fetch_all(keep_days=90)
    save(art)
    print(f"\n✅  {len(art)} articles saved to news.json")

    # Auto-rebuild site.html so it can be opened directly without a server
    try:
        import importlib.util, sys as _sys
        _build_path = Path(__file__).parent / "build.py"
        spec = importlib.util.spec_from_file_location("build", _build_path)
        _build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_build)
        _build.build()
    except Exception as _e:
        print(f"⚠️  Could not auto-rebuild index.html/site.html: {_e}")
