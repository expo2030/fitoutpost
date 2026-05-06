#!/usr/bin/env python3
"""
FitOut Post — Intelligence Fetcher
Searches for published fit-out cost reports from industry sources,
extracts $/m² cost data, converts currencies, and saves to intelligence.json.

Sources searched:
  Cushman & Wakefield, Knight Frank, JLL, CBRE, Savills, AECOM, Gensler,
  Buro Happold, Arup, RBL, Colliers, Turner & Townsend, KEO, Mirage, Compass,
  ValuStrat, MPM Properties, Cavendish Maxwell, PWC, Deloitte, KPMG, BCG,
  EY, McKinsey, Roland Berger, BNP Paribas RE, Avison Young, Drees & Sommer,
  Arcadis, Newmark, BCQS International, and many more.

Output: intelligence.json

Usage:
    python fetch_intelligence.py                  # fetch current month
    python fetch_intelligence.py --dry-run        # preview without saving
    python fetch_intelligence.py --months-ago 1   # fetch previous month
    python fetch_intelligence.py --all-known      # fetch all known report URLs
    python fetch_intelligence.py --source CBRE    # filter to one source
"""

import json
import re
import time
import hashlib
import logging
import sys
import html
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, quote, urljoin

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s")
log = logging.getLogger("fitpost.intel")

BASE = Path(__file__).parent
INTEL_FILE = BASE / "intelligence.json"

# ─────────────────────────────────────────────────────────────────────────────
#  Currency conversion (approximate rates — updated periodically)
#  These are illustrative; admin can override per datapoint in admin.py.
# ─────────────────────────────────────────────────────────────────────────────
FX_RATES: dict[str, float] = {
    "USD": 1.00,
    "GBP": 1.27,
    "EUR": 1.08,
    "AED": 0.272,   # fixed peg
    "SAR": 0.267,   # fixed peg
    "QAR": 0.274,   # fixed peg
    "KWD": 3.25,
    "BHD": 2.65,
    "OMR": 2.60,
    "SGD": 0.74,
    "AUD": 0.65,
    "CAD": 0.74,
    "HKD": 0.128,
    "JPY": 0.0067,
    "INR": 0.012,
    "BRL": 0.19,
    "ZAR": 0.055,
    "CNY": 0.14,
    "NZD": 0.60,
    "CHF": 1.11,
    "SEK": 0.097,
    "NOK": 0.094,
    "DKK": 0.145,
    "MYR": 0.22,
    "THB": 0.028,
    "IDR": 0.000063,
    "PHP": 0.018,
    "VND": 0.000040,
    "EGP": 0.021,
    "TRY": 0.030,
    "ILS": 0.27,
    "ZAR": 0.055,
    "NGN": 0.00064,
    "KES": 0.0077,
    "MAD": 0.099,
}
FX_DATE = "2026-05-01"  # reference date for the rates above

CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "£": "GBP",
    "€": "EUR",
    "¥": "JPY",
    "₹": "INR",
    "฿": "THB",
    "₩": "KRW",
    "CHF": "CHF",
    "AED": "AED",
    "SAR": "SAR",
    "QAR": "QAR",
    "KWD": "KWD",
    "SGD": "SGD",
    "AUD": "AUD",
    "HKD": "HKD",
    "CAD": "CAD",
    "NZD": "NZD",
}

def to_usd(amount: float, currency: str) -> float:
    """Convert amount in currency to USD."""
    rate = FX_RATES.get(currency.upper(), 1.0)
    return round(amount * rate)

# ─────────────────────────────────────────────────────────────────────────────
#  Source registry — known report series published annually/quarterly
# ─────────────────────────────────────────────────────────────────────────────
# Each entry: (source_name, search_query, domain_hint)
KNOWN_SOURCES = [
    # Tier 1 — largest global firms with dedicated fit-out/occupier cost guides
    ("CBRE",                '"fit-out cost" OR "fitout cost guide" site:cbre.com OR "CBRE" "fit-out cost"',
                             "cbre.com"),
    ("Cushman & Wakefield",  '"fit-out cost" OR "office fit out costs" site:cushmanwakefield.com',
                             "cushmanwakefield.com"),
    ("JLL",                  '"fit-out cost" OR "fit out cost guide" site:jll.com OR "JLL" "fit-out cost guide"',
                             "jll.com"),
    ("Knight Frank",         '"fit-out cost" OR "commercial fit-out" site:knightfrank.com',
                             "knightfrank.com"),
    ("Savills",              '"fit-out cost" site:savills.com OR "Savills" "fit-out costs"',
                             "savills.com"),
    ("Colliers",             '"fit-out cost" site:colliers.com OR "Colliers" "fit-out cost guide"',
                             "colliers.com"),
    ("Turner & Townsend",    '"fit-out cost" OR "Turner Townsend" "international construction" cost',
                             "turnerandtownsend.com"),
    ("AECOM",                '"fit-out cost" site:aecom.com OR "AECOM" "construction cost" fit-out',
                             "aecom.com"),
    ("Arcadis",              '"fit-out cost" site:arcadis.com OR "Arcadis" "construction cost" fit-out',
                             "arcadis.com"),
    ("Gensler",              '"fit-out cost" OR "design cost" site:gensler.com',
                             "gensler.com"),
    ("Arup",                 '"fit-out cost" site:arup.com OR "Arup" "construction cost" interior',
                             "arup.com"),
    ("Buro Happold",         '"fit-out cost" site:burohappold.com OR "Buro Happold" fit-out cost',
                             "burohappold.com"),
    ("Avison Young",         '"fit-out cost" site:avisonyoung.com OR "Avison Young" fit-out',
                             "avisonyoung.com"),
    ("Drees & Sommer",       '"fit-out cost" OR "interior cost" site:dreso.com',
                             "dreso.com"),
    ("BNP Paribas Real Estate", '"fit-out cost" site:realestate.bnpparibas',
                             "realestate.bnpparibas"),
    ("Newmark",              '"fit-out cost" site:nmrk.com OR "Newmark" fit-out',
                             "nmrk.com"),

    # Tier 2 — regional specialists & consulting firms
    ("ValuStrat",            '"fit-out cost" site:valustrat.com OR "ValuStrat" fit-out',
                             "valustrat.com"),
    ("Cavendish Maxwell",    '"fit-out cost" site:cavendishmaxwell.com',
                             "cavendishmaxwell.com"),
    ("MPM Properties",       '"fit-out cost" site:mpmproperties.ae OR "MPM" fit-out cost Dubai',
                             "mpmproperties.ae"),
    ("KEO",                  '"fit-out cost" site:keogroup.com OR "KEO" fit-out cost',
                             "keogroup.com"),
    ("BCQS International",   '"fit-out cost" site:bcqs.com OR "BCQS" fit-out cost',
                             "bcqs.com"),
    ("RLB",                  '"fit-out cost" site:rlb.com OR "Rider Levett Bucknall" fit-out',
                             "rlb.com"),
    ("Linesight",            '"fit-out cost" site:linesight.com OR "Linesight" fit-out',
                             "linesight.com"),

    # Tier 3 — consultancies with RE/construction practice
    ("Deloitte",             '"fit-out cost" site:deloitte.com OR "Deloitte" "fit-out" real estate',
                             "deloitte.com"),
    ("KPMG",                 '"fit-out cost" site:kpmg.com OR "KPMG" "fit-out" real estate',
                             "kpmg.com"),
    ("PWC",                  '"fit-out cost" site:pwc.com OR "PwC" "fit-out" real estate',
                             "pwc.com"),
    ("McKinsey",             '"fit-out" "cost" site:mckinsey.com OR "McKinsey" workplace fit-out',
                             "mckinsey.com"),
    ("Boston Consulting Group", '"fit-out" "cost" site:bcg.com OR "BCG" workplace fit-out',
                             "bcg.com"),
    ("Roland Berger",        '"fit-out cost" site:rolandberger.com OR "Roland Berger" fit-out',
                             "rolandberger.com"),
    ("EY",                   '"fit-out cost" site:ey.com OR "EY" "fit-out" real estate',
                             "ey.com"),

    # APAC
    ("Lendlease",            '"fit-out cost" site:lendlease.com OR "Lendlease" fit-out',
                             "lendlease.com"),
    ("Goodman Group",        '"fit-out cost" site:goodman.com',
                             "goodman.com"),
    ("JLL Asia",             '"fit-out cost" "Asia" "JLL" office',
                             "jll.com"),
    ("ANAROCK",              '"fit-out cost" site:anarock.com OR "ANAROCK" interior cost India',
                             "anarock.com"),

    # Americas
    ("Hines",                '"fit-out cost" site:hines.com OR "Hines" fit-out',
                             "hines.com"),
    ("Tishman Speyer",       '"fit-out cost" site:tishmanspeyer.com',
                             "tishmanspeyer.com"),
    ("Marcus & Millichap",   '"fit-out cost" site:marcusmillichap.com',
                             "marcusmillichap.com"),
    ("RCLCO",                '"fit-out cost" site:rclco.com OR "RCLCO" interior cost',
                             "rclco.com"),

    # Global general searches (not source-specific)
    ("General",              '"fit-out cost guide" 2026 $/m2 OR "per sq m"',
                             ""),
    ("General",              '"office fit-out costs" 2025 OR 2026 report',
                             ""),
    ("General",              '"fit-out cost benchmarking" 2026',
                             ""),
    ("General",              '"commercial fit-out" "cost per square metre" 2026',
                             ""),
    ("General",              '"interior construction costs" 2026 "per m2" OR "per sqm"',
                             ""),
]

# Hardcoded known report URLs — these are fetched directly each run.
# Admin can add more via admin.py.
KNOWN_REPORT_URLS: list[dict] = [
    # CBRE
    {
        "source": "CBRE",
        "url": "https://www.cbre.com/insights/reports/emea-fit-out-cost-guide",
        "report_title": "CBRE EMEA Fit-Out Cost Guide",
        "geography_hint": "EMEA",
    },
    {
        "source": "CBRE",
        "url": "https://www.cbre.com/insights/reports/asia-pacific-fit-out-cost-guide",
        "report_title": "CBRE Asia Pacific Fit-Out Cost Guide",
        "geography_hint": "Asia Pacific",
    },
    {
        "source": "CBRE",
        "url": "https://www.cbre.com/insights/reports/north-america-fit-out-cost-guide",
        "report_title": "CBRE North America Fit-Out Cost Guide",
        "geography_hint": "Americas",
    },
    # JLL
    {
        "source": "JLL",
        "url": "https://www.jll.com/en/trends-and-insights/research/office-fit-out-cost-guide",
        "report_title": "JLL Office Fit-Out Cost Guide",
        "geography_hint": "Global",
    },
    # Cushman & Wakefield
    {
        "source": "Cushman & Wakefield",
        "url": "https://www.cushmanwakefield.com/en/insights/fit-out-cost-guides",
        "report_title": "Cushman & Wakefield Fit-Out Cost Guide",
        "geography_hint": "Global",
    },
    # Turner & Townsend
    {
        "source": "Turner & Townsend",
        "url": "https://www.turnerandtownsend.com/en/perspectives/international-construction-market-survey/",
        "report_title": "T&T International Construction Market Survey",
        "geography_hint": "Global",
    },
    # Knight Frank
    {
        "source": "Knight Frank",
        "url": "https://www.knightfrank.com/research/article/office-fit-out-costs",
        "report_title": "Knight Frank Office Fit-Out Cost Guide",
        "geography_hint": "Global",
    },
    # Colliers
    {
        "source": "Colliers",
        "url": "https://www.colliers.com/en/research/global-fit-out-cost-guide",
        "report_title": "Colliers Global Fit-Out Cost Guide",
        "geography_hint": "Global",
    },
    # RLB
    {
        "source": "RLB",
        "url": "https://rlb.com/perspectives/quarterly-cost-monitor/",
        "report_title": "RLB Quarterly Cost Monitor",
        "geography_hint": "Global",
    },
    # Arcadis
    {
        "source": "Arcadis",
        "url": "https://www.arcadis.com/en/knowledge-hub/perspectives/global/2024/international-construction-costs",
        "report_title": "Arcadis International Construction Costs",
        "geography_hint": "Global",
    },
    # ValuStrat
    {
        "source": "ValuStrat",
        "url": "https://www.valustrat.com/research/",
        "report_title": "ValuStrat Market Intelligence",
        "geography_hint": "Middle East",
    },
    # Cavendish Maxwell
    {
        "source": "Cavendish Maxwell",
        "url": "https://cavendishmaxwell.com/research/",
        "report_title": "Cavendish Maxwell Market Research",
        "geography_hint": "Middle East",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
#  Geography detection
# ─────────────────────────────────────────────────────────────────────────────
CONTINENT_KEYWORDS: dict[str, list[str]] = {
    "Europe": [
        "london","uk","united kingdom","europe","emea","paris","france","germany",
        "berlin","frankfurt","amsterdam","netherlands","madrid","spain","milan","italy",
        "zurich","switzerland","dublin","ireland","warsaw","poland","stockholm","sweden",
        "oslo","norway","copenhagen","denmark","helsinki","finland","brussels","belgium",
        "vienna","austria","lisbon","portugal","athens","greece","budapest","hungary",
        "bucharest","romania","prague","czech","bratislava","slovakia",
    ],
    "Middle East": [
        "dubai","abu dhabi","uae","united arab emirates","saudi arabia","riyadh","jeddah",
        "qatar","doha","kuwait","bahrain","oman","muscat","tel aviv","israel","jordan",
        "amman","beirut","lebanon","cairo","egypt","istanbul","turkey","middle east",
        "gcc","neom","alula","ksa",
    ],
    "Asia Pacific": [
        "singapore","hong kong","tokyo","japan","seoul","south korea","beijing","shanghai",
        "china","mumbai","delhi","bangalore","india","bangkok","thailand","kuala lumpur",
        "malaysia","jakarta","indonesia","manila","philippines","hanoi","ho chi minh",
        "vietnam","asia","apac","asia pacific",
    ],
    "Americas": [
        "new york","chicago","los angeles","houston","dallas","atlanta","boston",
        "san francisco","toronto","canada","mexico","sao paulo","brazil","buenos aires",
        "argentina","bogota","colombia","lima","peru","united states","usa","us",
        "north america","latam","latin america",
    ],
    "Africa": [
        "johannesburg","cape town","south africa","lagos","nigeria","nairobi","kenya",
        "ghana","accra","ethiopia","addis ababa","africa","sub-saharan",
    ],
    "Oceania": [
        "sydney","melbourne","brisbane","perth","australia","auckland","new zealand",
        "oceania","pacific",
    ],
}

COUNTRY_FROM_CITY: dict[str, str] = {
    "london": "United Kingdom",
    "manchester": "United Kingdom",
    "birmingham": "United Kingdom",
    "edinburgh": "United Kingdom",
    "glasgow": "United Kingdom",
    "paris": "France",
    "berlin": "Germany",
    "frankfurt": "Germany",
    "munich": "Germany",
    "hamburg": "Germany",
    "amsterdam": "Netherlands",
    "brussels": "Belgium",
    "zurich": "Switzerland",
    "vienna": "Austria",
    "stockholm": "Sweden",
    "oslo": "Norway",
    "copenhagen": "Denmark",
    "helsinki": "Finland",
    "warsaw": "Poland",
    "madrid": "Spain",
    "barcelona": "Spain",
    "milan": "Italy",
    "rome": "Italy",
    "lisbon": "Portugal",
    "dublin": "Ireland",
    "athens": "Greece",
    "budapest": "Hungary",
    "bucharest": "Romania",
    "prague": "Czech Republic",
    "bratislava": "Slovakia",
    "dubai": "United Arab Emirates",
    "abu dhabi": "United Arab Emirates",
    "riyadh": "Saudi Arabia",
    "jeddah": "Saudi Arabia",
    "doha": "Qatar",
    "kuwait city": "Kuwait",
    "manama": "Bahrain",
    "muscat": "Oman",
    "tel aviv": "Israel",
    "amman": "Jordan",
    "cairo": "Egypt",
    "istanbul": "Turkey",
    "singapore": "Singapore",
    "hong kong": "Hong Kong",
    "tokyo": "Japan",
    "osaka": "Japan",
    "seoul": "South Korea",
    "beijing": "China",
    "shanghai": "China",
    "shenzhen": "China",
    "mumbai": "India",
    "delhi": "India",
    "bangalore": "India",
    "hyderabad": "India",
    "chennai": "India",
    "bangkok": "Thailand",
    "kuala lumpur": "Malaysia",
    "jakarta": "Indonesia",
    "manila": "Philippines",
    "hanoi": "Vietnam",
    "ho chi minh": "Vietnam",
    "new york": "United States",
    "chicago": "United States",
    "los angeles": "United States",
    "houston": "United States",
    "dallas": "United States",
    "atlanta": "United States",
    "boston": "United States",
    "san francisco": "United States",
    "miami": "United States",
    "toronto": "Canada",
    "vancouver": "Canada",
    "montreal": "Canada",
    "sydney": "Australia",
    "melbourne": "Australia",
    "brisbane": "Australia",
    "perth": "Australia",
    "auckland": "New Zealand",
    "wellington": "New Zealand",
    "johannesburg": "South Africa",
    "cape town": "South Africa",
    "lagos": "Nigeria",
    "nairobi": "Kenya",
    "accra": "Ghana",
    "sao paulo": "Brazil",
    "rio de janeiro": "Brazil",
    "buenos aires": "Argentina",
    "bogota": "Colombia",
    "lima": "Peru",
    "mexico city": "Mexico",
    "santiago": "Chile",
}

def detect_geography(text: str) -> dict:
    """Try to extract continent and country from text."""
    text_lower = text.lower()
    city = None
    country = None
    continent = "Global"

    # City → country
    for c, cty in sorted(COUNTRY_FROM_CITY.items(), key=lambda x: -len(x[0])):
        if c in text_lower:
            city = c.title()
            country = cty
            break

    # Continent from text
    best_cont = None
    best_count = 0
    for cont, kws in CONTINENT_KEYWORDS.items():
        count = sum(1 for kw in kws if kw in text_lower)
        if count > best_count:
            best_count = count
            best_cont = cont
    if best_cont and best_count >= 1:
        continent = best_cont

    return {"continent": continent, "country": country or "", "city": city or ""}


# ─────────────────────────────────────────────────────────────────────────────
#  Cost pattern extraction
# ─────────────────────────────────────────────────────────────────────────────

# Patterns for cost figures like:
#   $1,200/m²  |  £2,500/sqm  |  AED 4,500 per sq m  |  €1,800 per m2
#   1,200 USD/m²  |  GBP 2,000-3,500/m²  |  USD 1,500 to USD 2,000 per square metre

_NUM   = r"[\d,]+(?:\.\d+)?"
_RANGE = rf"(?:{_NUM})\s*[-–to]+\s*(?:{_NUM})"
_UNITS = r"(?:/\s*m[²2]|/\s*sqm|per\s+m[²2]|per\s+sqm|per\s+square\s+m(?:etre|eter)?)"
_CURR_SYM = r"(?:USD|GBP|EUR|AED|SAR|QAR|KWD|SGD|AUD|HKD|CAD|CHF|NZD|INR|\$|£|€|AED\s*)"

COST_PATTERN = re.compile(
    rf"({_CURR_SYM})?\s*({_RANGE}|{_NUM})\s*({_CURR_SYM})?\s*{_UNITS}",
    re.IGNORECASE,
)

FIT_OUT_TYPE_PATTERN = re.compile(
    r"(cat(?:egory)?\s*[ab]|office|retail|hospitality|hotel|industrial|"
    r"warehouse|data\s*cent(?:re|er)|lab(?:oratory)?|healthcare|residential|"
    r"shell\s*and\s*core|tenant\s*improvement)",
    re.IGNORECASE,
)

def extract_costs(text: str, source_currency: str = "USD") -> list[dict]:
    """Extract cost data points from text."""
    results = []
    seen = set()

    for m in COST_PATTERN.finditer(text):
        full_match = m.group(0)
        if full_match in seen:
            continue
        seen.add(full_match)

        # Get surrounding context (±200 chars)
        start = max(0, m.start() - 200)
        end   = min(len(text), m.end() + 200)
        context = text[start:end].strip()

        # Determine currency
        sym1 = (m.group(1) or "").strip()
        sym2 = (m.group(3) or "").strip()
        sym  = sym1 or sym2 or source_currency
        currency = CURRENCY_SYMBOLS.get(sym.upper(), sym.upper() if len(sym) == 3 else "USD")

        # Parse value(s)
        val_str = m.group(2)
        numbers = [float(n.replace(",","")) for n in re.findall(r"[\d,]+(?:\.\d+)?", val_str)]
        if not numbers:
            continue

        # Reject clearly non-cost numbers (too small or suspiciously round large)
        if max(numbers) < 50 or max(numbers) > 200_000:
            continue

        low  = min(numbers)
        high = max(numbers) if len(numbers) > 1 else min(numbers)
        mid  = round((low + high) / 2)

        cost_usd_low  = to_usd(low, currency)
        cost_usd_high = to_usd(high, currency)
        cost_usd_mid  = to_usd(mid, currency)

        # Detect fit-out type from context
        ft = FIT_OUT_TYPE_PATTERN.search(context)
        fit_out_type = _normalise_type(ft.group(0)) if ft else "Office"

        # Detect geography
        geo = detect_geography(context)

        results.append({
            "cost_usd_m2_low":  cost_usd_low,
            "cost_usd_m2_high": cost_usd_high,
            "cost_usd_m2_mid":  cost_usd_mid,
            "cost_original":    full_match.strip(),
            "currency":         currency,
            "exchange_rate":    FX_RATES.get(currency, 1.0),
            "exchange_rate_date": FX_DATE,
            "fit_out_type":     fit_out_type,
            "context_snippet":  context[:300],
            **geo,
        })

    return results

def _normalise_type(raw: str) -> str:
    r = raw.lower()
    if "cat a" in r or "category a" in r: return "Office Cat A"
    if "cat b" in r or "category b" in r: return "Office Cat B"
    if "hotel" in r or "hospitality" in r: return "Hotel / Hospitality"
    if "retail" in r: return "Retail"
    if "data cent" in r: return "Data Centre"
    if "lab" in r: return "Laboratory / Life Sciences"
    if "health" in r: return "Healthcare"
    if "industrial" in r or "warehouse" in r: return "Industrial / Warehouse"
    if "residential" in r: return "Residential"
    if "shell" in r: return "Shell and Core"
    if "tenant" in r: return "Tenant Improvement"
    if "office" in r: return "Office"
    return "Office"


# ─────────────────────────────────────────────────────────────────────────────
#  Google News RSS search
# ─────────────────────────────────────────────────────────────────────────────
def _gnews(query: str) -> str:
    return (
        f"https://news.google.com/rss/search?q={quote(query)}"
        f"&hl=en&gl=US&ceid=US:en&tbs=qdr:m"
    )

def search_google_news(query: str) -> list[dict]:
    """Search Google News RSS for reports, return list of {title, url}."""
    try:
        import feedparser
    except ImportError:
        log.warning("feedparser not installed; skipping Google News search")
        return []

    url  = _gnews(query)
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:8]:
        title = entry.get("title","")
        link  = entry.get("link","")
        if not link:
            continue
        results.append({"title": title, "url": link})
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  Web page / PDF fetcher
# ─────────────────────────────────────────────────────────────────────────────
def fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch URL and return text content (HTML stripped, or PDF text)."""
    try:
        import requests
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; FitOutPost/1.0; "
                "+https://fitoutpost.com/bot)"
            ),
            "Accept": "text/html,application/pdf,*/*",
        }
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        ct = r.headers.get("Content-Type","")

        if "pdf" in ct.lower() or url.lower().endswith(".pdf"):
            return extract_pdf_text(r.content)
        else:
            return strip_html(r.text)

    except Exception as e:
        log.warning("Fetch failed for %s: %s", url, e)
        return ""

def extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber or PyMuPDF."""
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = []
            for page in pdf.pages[:30]:   # limit to first 30 pages
                t = page.extract_text()
                if t:
                    pages.append(t)
            return "\n".join(pages)
    except Exception:
        pass
    try:
        import fitz, io
        doc = fitz.open(stream=content, filetype="pdf")
        pages = []
        for i, page in enumerate(doc):
            if i >= 30:
                break
            pages.append(page.get_text())
        return "\n".join(pages)
    except Exception:
        pass
    try:
        # Last resort: decode as utf-8 ignoring errors, extract visible text
        return content.decode("utf-8","ignore")
    except Exception:
        return ""

def strip_html(html_text: str) -> str:
    """Remove HTML tags and unescape entities."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script","style","nav","header","footer","aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html_text)
    text = html.unescape(text)
    text = re.sub(r"\s{3,}", "  ", text)
    return text[:50_000]  # cap at 50k chars


# ─────────────────────────────────────────────────────────────────────────────
#  Summary generation
# ─────────────────────────────────────────────────────────────────────────────
def make_summary(dp: dict, report_title: str, source: str) -> str:
    """Generate a human-readable one-sentence summary from a datapoint."""
    city    = dp.get("city") or dp.get("country") or "this market"
    fit     = dp.get("fit_out_type","Office")
    low     = dp.get("cost_usd_m2_low")
    high    = dp.get("cost_usd_m2_high")
    orig    = dp.get("cost_original","")
    curr    = dp.get("currency","")

    if low and high and low != high:
        cost_str = f"${low:,}–${high:,}/m² (USD)"
    elif low:
        cost_str = f"${low:,}/m² (USD)"
    else:
        cost_str = "cost data available"

    if orig and curr and curr != "USD":
        cost_str += f" [{orig}]"

    return (
        f"{source} reports {fit.lower()} fit-out costs in {city} at {cost_str}, "
        f"per the {report_title} report."
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Period helpers
# ─────────────────────────────────────────────────────────────────────────────
def period_id(months_ago: int = 0) -> str:
    now = datetime.now(timezone.utc)
    month = now.month - months_ago
    year  = now.year
    while month <= 0:
        month += 12
        year  -= 1
    return f"{year}-{month:02d}"

def period_label(pid: str) -> str:
    year, month = pid.split("-")
    dt = datetime(int(year), int(month), 1)
    return dt.strftime("%B %Y")

def period_start_end(pid: str) -> tuple[str, str]:
    year, month = pid.split("-")
    from calendar import monthrange
    y, m = int(year), int(month)
    _, last_day = monthrange(y, m)
    return f"{pid}-01", f"{pid}-{last_day:02d}"


# ─────────────────────────────────────────────────────────────────────────────
#  Datapoint builder
# ─────────────────────────────────────────────────────────────────────────────
def make_datapoint_id(source: str, city: str, fit_type: str, low: float) -> str:
    key = f"{source}|{city}|{fit_type}|{low}".encode()
    return "dp_" + hashlib.md5(key).hexdigest()[:10]

def process_report(
    source: str,
    url: str,
    report_title: str,
    geography_hint: str = "",
    dry_run: bool = False,
) -> list[dict]:
    """Fetch a report URL and return list of datapoints extracted."""
    log.info("Fetching %s — %s", source, url[:80])
    text = fetch_url(url)
    if not text or len(text) < 200:
        log.warning("  → Empty/short response, skipping")
        return []

    # Determine default currency from geography hint
    default_currency = "USD"
    if "uk" in geography_hint.lower() or "europe" in geography_hint.lower():
        default_currency = "GBP"
    elif any(x in geography_hint.lower() for x in ["uae","dubai","gulf","gcc","middle east"]):
        default_currency = "AED"
    elif "australia" in geography_hint.lower():
        default_currency = "AUD"
    elif "singapore" in geography_hint.lower():
        default_currency = "SGD"

    raw_costs = extract_costs(text, source_currency=default_currency)
    if not raw_costs:
        log.info("  → No cost patterns found")
        return []

    log.info("  → Found %d cost patterns", len(raw_costs))

    datapoints = []
    for rc in raw_costs:
        # Override geography hint if detected geography is weak
        if not rc.get("country") and geography_hint:
            geo_from_hint = detect_geography(geography_hint)
            rc["continent"] = geo_from_hint.get("continent", rc.get("continent","Global"))
            rc["country"]   = geo_from_hint.get("country", "")
            rc["city"]      = geo_from_hint.get("city", "")

        dp_id = make_datapoint_id(
            source,
            rc.get("city") or rc.get("country",""),
            rc.get("fit_out_type",""),
            rc.get("cost_usd_m2_low",0),
        )

        dp = {
            "id":              dp_id,
            "source":          source,
            "report_title":    report_title,
            "report_url":      url,
            "continent":       rc.get("continent","Global"),
            "country":         rc.get("country",""),
            "city":            rc.get("city",""),
            "fit_out_type":    rc.get("fit_out_type","Office"),
            "cost_usd_m2_low": rc.get("cost_usd_m2_low"),
            "cost_usd_m2_high":rc.get("cost_usd_m2_high"),
            "cost_usd_m2_mid": rc.get("cost_usd_m2_mid"),
            "cost_original":   rc.get("cost_original",""),
            "currency":        rc.get("currency","USD"),
            "exchange_rate":   rc.get("exchange_rate",1.0),
            "exchange_rate_date": FX_DATE,
            "summary":         make_summary(rc, report_title, source),
            "date_published":  "",   # will be populated if discoverable
            "date_added":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "auto_extracted":  True,
            "needs_review":    True,
            "context_snippet": rc.get("context_snippet","")[:400],
        }
        datapoints.append(dp)

    return datapoints


# ─────────────────────────────────────────────────────────────────────────────
#  Load / save intelligence.json
# ─────────────────────────────────────────────────────────────────────────────
def load_intelligence() -> dict:
    if not INTEL_FILE.exists():
        return {"last_updated":"","total_datapoints":0,"periods":[]}
    try:
        return json.loads(INTEL_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Cannot parse intelligence.json: %s", e)
        return {"last_updated":"","total_datapoints":0,"periods":[]}

def save_intelligence(data: dict) -> None:
    INTEL_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    log.info("Saved intelligence.json — %d total datapoints", data.get("total_datapoints",0))

def add_datapoints_to_period(data: dict, pid: str, new_dps: list[dict]) -> None:
    """Add datapoints to a period, deduplicating by id."""
    # Find or create period
    period = next((p for p in data["periods"] if p["id"] == pid), None)
    if not period:
        start, end = period_start_end(pid)
        period = {
            "id":         pid,
            "label":      period_label(pid),
            "start":      start,
            "end":        end,
            "datapoints": [],
        }
        data["periods"].append(period)

    existing_ids = {dp["id"] for dp in period["datapoints"]}
    added = 0
    for dp in new_dps:
        if dp["id"] not in existing_ids:
            period["datapoints"].append(dp)
            existing_ids.add(dp["id"])
            added += 1

    log.info("  Period %s: added %d new, skipped %d duplicates",
             pid, added, len(new_dps) - added)

    # Recalculate total
    data["total_datapoints"] = sum(
        len(p.get("datapoints",[])) for p in data["periods"]
    )
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────────────────────────────────────
#  Main fetch routine
# ─────────────────────────────────────────────────────────────────────────────
def run_fetch(
    months_ago: int = 0,
    dry_run: bool = False,
    source_filter: str = "",
    all_known: bool = False,
    delay: float = 1.5,
) -> None:
    pid = period_id(months_ago)
    log.info("=" * 60)
    log.info("Intelligence fetch — period %s", pid)
    log.info("dry_run=%s  source_filter=%r  all_known=%s", dry_run, source_filter, all_known)
    log.info("=" * 60)

    data = load_intelligence()
    all_new_dps: list[dict] = []

    # ── A. Fetch from known report URLs ──────────────────────────────────────
    for report in KNOWN_REPORT_URLS:
        src = report["source"]
        if source_filter and source_filter.lower() not in src.lower():
            continue
        dps = process_report(
            source=src,
            url=report["url"],
            report_title=report.get("report_title",""),
            geography_hint=report.get("geography_hint",""),
            dry_run=dry_run,
        )
        all_new_dps.extend(dps)
        time.sleep(delay)

    # ── B. Google News search for reports ────────────────────────────────────
    if all_known:
        for src, query, domain in KNOWN_SOURCES:
            if source_filter and source_filter.lower() not in src.lower():
                continue
            log.info("Searching: %s — %s", src, query[:60])
            results = search_google_news(query)
            for r in results[:3]:
                title = r.get("title","")
                url   = r.get("url","")
                if not url:
                    continue
                # Filter to domain if specified
                if domain and domain.lower() not in urlparse(url).netloc.lower():
                    log.info("  Skip (wrong domain): %s", url[:60])
                    continue
                dps = process_report(
                    source=src,
                    url=url,
                    report_title=title or f"{src} Report",
                    geography_hint="",
                    dry_run=dry_run,
                )
                all_new_dps.extend(dps)
                time.sleep(delay)

    log.info("─" * 60)
    log.info("Total extracted datapoints: %d", len(all_new_dps))

    if dry_run:
        log.info("[DRY RUN] Would add %d datapoints to period %s", len(all_new_dps), pid)
        for dp in all_new_dps[:5]:
            log.info("  Sample: %s | %s | %s | $%s/m²",
                     dp["source"], dp.get("city") or dp.get("country","?"),
                     dp["fit_out_type"], dp.get("cost_usd_m2_mid","?"))
        return

    add_datapoints_to_period(data, pid, all_new_dps)
    save_intelligence(data)

    # Also rebuild intelligence.html
    try:
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location("build", BASE / "build.py")
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_intelligence()
    except Exception as e:
        log.warning("build_intelligence() failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    dry_run       = "--dry-run" in args
    all_known     = "--all-known" in args
    months_ago    = 0
    source_filter = ""

    for a in args:
        if a.startswith("--months-ago="):
            months_ago = int(a.split("=",1)[1])
        elif a.startswith("--months-ago"):
            idx = args.index(a)
            if idx + 1 < len(args):
                months_ago = int(args[idx+1])
        if a.startswith("--source="):
            source_filter = a.split("=",1)[1]
        elif a == "--source":
            idx = args.index(a)
            if idx + 1 < len(args):
                source_filter = args[idx+1]

    run_fetch(
        months_ago=months_ago,
        dry_run=dry_run,
        source_filter=source_filter,
        all_known=all_known,
    )
