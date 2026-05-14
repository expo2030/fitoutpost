#!/usr/bin/env python3
"""
fetch_tenders.py — FitOut Post Tender Aggregator
Fetches open tenders/bids/RFPs for fit-out works worldwide.
Saves to tenders.json

Sources:
  1. TED (Tenders Electronic Daily) — EU & EEA via title keywords
  2. TED — EU & EEA via CPV codes (joinery, partitioning, shopfitting, fit-out)
  3. Contracts Finder — UK (below-threshold and awarded contracts)
  4. Find a Tender — UK procurement (above-threshold)
  5. SAM.gov — US federal procurement
  6. AusTender — Australia
  7. Google News RSS — 80+ targeted global queries

Run:
  python fetch_tenders.py
"""

import json, re, hashlib, time, sys, logging
import urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

BASE   = Path(__file__).parent
OUTPUT = BASE / "tenders.json"

# ── Geography ─────────────────────────────────────────────────────────────────
COUNTRY_TO_CONTINENT = {
    "AT":"Europe","BE":"Europe","BG":"Europe","CY":"Europe","CZ":"Europe",
    "DE":"Europe","DK":"Europe","EE":"Europe","ES":"Europe","FI":"Europe",
    "FR":"Europe","GR":"Europe","HR":"Europe","HU":"Europe","IE":"Europe",
    "IT":"Europe","LT":"Europe","LU":"Europe","LV":"Europe","MT":"Europe",
    "NL":"Europe","PL":"Europe","PT":"Europe","RO":"Europe","SE":"Europe",
    "SI":"Europe","SK":"Europe","GB":"Europe","CH":"Europe","NO":"Europe",
    "IS":"Europe","LI":"Europe","AL":"Europe","BA":"Europe","ME":"Europe",
    "MK":"Europe","RS":"Europe","TR":"Europe","UA":"Europe","XK":"Europe",
    "AE":"Middle East","SA":"Middle East","QA":"Middle East","KW":"Middle East",
    "BH":"Middle East","OM":"Middle East","JO":"Middle East","LB":"Middle East",
    "IL":"Middle East","IQ":"Middle East","YE":"Middle East","EG":"Middle East",
    "CN":"Asia Pacific","JP":"Asia Pacific","KR":"Asia Pacific","IN":"Asia Pacific",
    "AU":"Asia Pacific","NZ":"Asia Pacific","SG":"Asia Pacific","HK":"Asia Pacific",
    "TW":"Asia Pacific","TH":"Asia Pacific","VN":"Asia Pacific","MY":"Asia Pacific",
    "PH":"Asia Pacific","ID":"Asia Pacific","PK":"Asia Pacific","BD":"Asia Pacific",
    "LK":"Asia Pacific","MM":"Asia Pacific","KH":"Asia Pacific",
    "US":"Americas","CA":"Americas","MX":"Americas","BR":"Americas","AR":"Americas",
    "CL":"Americas","CO":"Americas","PE":"Americas","EC":"Americas",
    "ZA":"Africa","NG":"Africa","KE":"Africa","GH":"Africa","MA":"Africa",
    "TZ":"Africa","UG":"Africa","ET":"Africa","SN":"Africa","CM":"Africa",
}

COUNTRY_NAMES = {
    "AE":"UAE","AU":"Australia","BE":"Belgium","CA":"Canada","CH":"Switzerland",
    "CN":"China","DE":"Germany","DK":"Denmark","EG":"Egypt","ES":"Spain",
    "FI":"Finland","FR":"France","GB":"United Kingdom","GH":"Ghana","GR":"Greece",
    "HK":"Hong Kong","HR":"Croatia","HU":"Hungary","ID":"Indonesia","IE":"Ireland",
    "IL":"Israel","IN":"India","IT":"Italy","JP":"Japan","KE":"Kenya",
    "KR":"South Korea","KW":"Kuwait","LB":"Lebanon","LU":"Luxembourg","MA":"Morocco",
    "MY":"Malaysia","NG":"Nigeria","NL":"Netherlands","NO":"Norway","NZ":"New Zealand",
    "OM":"Oman","PH":"Philippines","PK":"Pakistan","PL":"Poland","PT":"Portugal",
    "QA":"Qatar","RO":"Romania","SA":"Saudi Arabia","SE":"Sweden","SG":"Singapore",
    "SI":"Slovenia","SK":"Slovakia","TH":"Thailand","TR":"Turkey","TW":"Taiwan",
    "TZ":"Tanzania","UA":"Ukraine","US":"United States","VN":"Vietnam",
    "ZA":"South Africa","BH":"Bahrain","NO":"Norway","DK":"Denmark","FI":"Finland",
    "AT":"Austria","CZ":"Czech Republic","RS":"Serbia","BG":"Bulgaria","LT":"Lithuania",
    "LV":"Latvia","EE":"Estonia","HR":"Croatia","SK":"Slovakia","SI":"Slovenia",
    "NZ":"New Zealand","CL":"Chile","CO":"Colombia","PE":"Peru","BR":"Brazil",
    "MX":"Mexico","AR":"Argentina",
}

COUNTRY_FLAGS = {
    "AE":"🇦🇪","AU":"🇦🇺","BE":"🇧🇪","CA":"🇨🇦","CH":"🇨🇭","CN":"🇨🇳","DE":"🇩🇪",
    "DK":"🇩🇰","ES":"🇪🇸","FI":"🇫🇮","FR":"🇫🇷","GB":"🇬🇧","GH":"🇬🇭","GR":"🇬🇷",
    "HK":"🇭🇰","HU":"🇭🇺","ID":"🇮🇩","IE":"🇮🇪","IL":"🇮🇱","IN":"🇮🇳","IT":"🇮🇹",
    "JP":"🇯🇵","KE":"🇰🇪","KR":"🇰🇷","KW":"🇰🇼","LB":"🇱🇧","MA":"🇲🇦","MY":"🇲🇾",
    "NG":"🇳🇬","NL":"🇳🇱","NO":"🇳🇴","NZ":"🇳🇿","OM":"🇴🇲","PH":"🇵🇭","PL":"🇵🇱",
    "PT":"🇵🇹","QA":"🇶🇦","RO":"🇷🇴","SA":"🇸🇦","SE":"🇸🇪","SG":"🇸🇬","TH":"🇹🇭",
    "TR":"🇹🇷","TW":"🇹🇼","UA":"🇺🇦","US":"🇺🇸","VN":"🇻🇳","ZA":"🇿🇦","BH":"🇧🇭",
    "EG":"🇪🇬","LU":"🇱🇺","HR":"🇭🇷","RS":"🇷🇸","AT":"🇦🇹","CZ":"🇨🇿","BG":"🇧🇬",
    "FI":"🇫🇮","DK":"🇩🇰","SK":"🇸🇰","SI":"🇸🇮","LT":"🇱🇹","LV":"🇱🇻","EE":"🇪🇪",
    "CL":"🇨🇱","CO":"🇨🇴","PE":"🇵🇪","BR":"🇧🇷","MX":"🇲🇽","AR":"🇦🇷","NZ":"🇳🇿",
}

CATEGORY_KEYWORDS = {
    "Office":       ["office","workspace","headquarters","hq","corporate","coworking","co-working","workstation"],
    "Retail":       ["retail","shop","store","showroom","boutique","mall","shopping","outlet","commercial unit",
                     "shopfitting","shopfit","shop fit"],
    "Hospitality":  ["hotel","restaurant","bar","hospitality","lounge","café","cafe","spa","resort","club","leisure",
                     "catering","canteen","kitchen"],
    "Healthcare":   ["hospital","clinic","medical","healthcare","pharmacy","laboratory","lab","dental","surgery",
                     "health centre","health center","nhs","ward"],
    "Education":    ["school","university","college","education","library","campus","learning","classroom","student",
                     "preschool","nursery","lecture","faculty"],
    "Public":       ["government","municipal","public","civic","ministry","embassy","court","airport","station",
                     "transit","council","parliament","police","fire station","courthouse"],
    "Industrial":   ["warehouse","factory","industrial","manufacturing","logistics","data centre","datacenter",
                     "data center","depot","storage"],
    "Residential":  ["residential","apartment","flat","condo","housing","villa","dormitory","student accommodation",
                     "student housing","care home","retirement"],
}

def categorize(title, description="", issuer=""):
    text = (title + " " + description + " " + issuer).lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return cat
    return "Commercial"

def continent_from_country(code):
    return COUNTRY_TO_CONTINENT.get((code or "").upper(), "Other")

def days_until(deadline_str):
    if not deadline_str:
        return None
    try:
        d = datetime.strptime(deadline_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (d - datetime.now(timezone.utc)).days
    except Exception:
        return None

def status_from_days(d):
    if d is None: return "open"
    if d < 0:    return "closed"
    if d <= 14:  return "closing_soon"
    return "open"

def make_id(prefix, ref):
    return prefix[:3] + "-" + hashlib.md5(str(ref).encode()).hexdigest()[:8]

def fmt_value(mn, mx, currency):
    sym = {"EUR":"€","GBP":"£","USD":"$","AUD":"A$","SGD":"S$","AED":"AED "}.get(currency, currency+" ")
    def compact(v):
        if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
        if v >= 1_000:     return f"{v/1_000:.0f}K"
        return str(int(v))
    mn, mx = (mn or 0), (mx or 0)
    if mn <= 0 and mx <= 0: return ""
    if mn == mx or mx == 0: return f"{sym}{compact(mn or mx)}"
    return f"{sym}{compact(mn)} – {sym}{compact(mx)}"


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def get_url(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": "FitOutPost-Aggregator/1.0 (news aggregator; contact@fitoutpost.com)",
        "Accept": "application/json, text/html, application/xml, */*",
        **(headers or {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning(f"  ✗ GET {url[:70]}... → {e}")
        return None

def post_json(url, payload, timeout=15):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "FitOutPost-Aggregator/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        log.warning(f"  ✗ POST {url[:70]}... → {e}")
        return None


# 3-letter ISO → 2-letter ISO (TED uses 3-letter codes)
ISO3_TO_ISO2 = {
    "AUT":"AT","BEL":"BE","BGR":"BG","CYP":"CY","CZE":"CZ","DEU":"DE","DNK":"DK",
    "EST":"EE","ESP":"ES","FIN":"FI","FRA":"FR","GRC":"GR","HRV":"HR","HUN":"HU",
    "IRL":"IE","ITA":"IT","LTU":"LT","LUX":"LU","LVA":"LV","MLT":"MT","NLD":"NL",
    "POL":"PL","PRT":"PT","ROU":"RO","SWE":"SE","SVN":"SI","SVK":"SK","GBR":"GB",
    "CHE":"CH","NOR":"NO","ISL":"IS","LIE":"LI","ALB":"AL","BIH":"BA","MNE":"ME",
    "MKD":"MK","SRB":"RS","TUR":"TR","UKR":"UA","ARE":"AE","SAU":"SA","QAT":"QA",
    "KWT":"KW","BHR":"BH","OMN":"OM","JOR":"JO","LBN":"LB","ISR":"IL","AUS":"AU",
    "NZL":"NZ","SGP":"SG","HKG":"HK","IND":"IN","CHN":"CN","JPN":"JP","KOR":"KR",
    "USA":"US","CAN":"CA","BRA":"BR","ZAF":"ZA","NGA":"NG","KEN":"KE","EGY":"EG",
    "MAR":"MA","GHA":"GH","TZA":"TZ","CMR":"CM",
}

# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 1 — TED Title Queries (EU Tenders Electronic Daily)
#  API: https://api.ted.europa.eu/v3/notices/search (POST)
#  Query syntax: FIELD OPERATOR 'value'  e.g.  TI = 'refurbishment'
# ─────────────────────────────────────────────────────────────────────────────

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
# DT = deadline timestamp (list of ISO-8601), PD = publication date (string),
# DD is always null in TED v3 — do not request it.
TED_FIELDS = ["ND", "TI", "CY", "AU", "DT", "PD", "publication-number"]

# Title queries — TED supports both exact (=) and contains (~) operators
# Key: ~ "fit-out" works even with hyphen because ~ is phrase-contains not keyword
TED_TITLE_QUERIES = [
    # ── Phrase contains (most targeted) ──────────────────────────────────────
    'TI ~ "fit-out"',             # 19 — explicit fit-out notices
    'TI ~ "suspended ceiling"',   # 85 — ceiling installation (core fit-out)
    'TI ~ "interior fit"',        #  1 — interior fit works
    # ── Exact word matches ────────────────────────────────────────────────────
    'TI = "refurbishment"',       # 1119 — refurb (filtered by FITOUT_FILTER_WORDS)
    'TI = "joinery"',             # 1058 — joinery works (core fit-out)
    'TI = "partitioning"',        #  179 — partition works
    'TI = "mezzanine"',           #    3 — mezzanine installation
    'TI = "ceilings"',            #   88 — ceiling works
    'TI = "fitout"',              #    4 — no-hyphen variant
    'TI = "interior works"',      #    1 — explicit interior works
    'TI = "drylining"',           # drylining / dry lining
    'TI = "shopfitting"',         # shopfitting
    'TI = "shopfit"',             # shopfit variant
    'TI = "drywall"',             # drywall (US/Ireland term)
    'TI = "interiors"',           # interiors
    'TI = "tenant improvement"',  # US/APAC term
    'TI = "raised floor"',        # raised access floor
]

# CPV code queries — only truly specific fit-out CPV codes
# NOTE: CPV codes in TED can be secondary codes on broader contracts,
# so title filtering is still applied to reduce false positives.
# CPV 45421152 = Installation of partition walls  (~521 active, 11 pass title)
# CPV 45451000 = Decoration work                  (~122 active,  7 pass title)
# CPV 45421141 = Installation of partitioning     (~966 active,  2 pass title)
TED_CPV_QUERIES = [
    ('PC in ("45421152")', "Partition walls"),  # most specific
    ('PC in ("45451000")', "Decoration"),       # decoration / fit-out finishing
    ('PC in ("45421141")', "Partitioning"),     # partitioning
]

FITOUT_FILTER_WORDS = {
    "fit-out","fitout","fit out","interior","joinery","partition","shopfit",
    "refurb","tenant","raised floor","suspended ceiling","drylin","mezzanin",
    "ceilings","finishes","fitting out","finishing works","cat a","cat b",
    "decoration","refit","renovation","remodel","makeover","workspace",
    "commercial interior","office interior","retail interior",
}

def is_fitout_title(eng_title):
    t = eng_title.lower()
    return any(w in t for w in FITOUT_FILTER_WORDS)

def pick_eng(field_val):
    """Pick English value from TED multilingual dict/list."""
    if isinstance(field_val, dict):
        v = field_val.get("eng") or field_val.get("gle") or next(iter(field_val.values()), "")
        return (v[0] if isinstance(v, list) else v) or ""
    if isinstance(field_val, list):
        for item in field_val:
            if isinstance(item, dict):
                v = item.get("eng") or item.get("gle") or next(iter(item.values()), "")
                return v[0] if isinstance(v, list) else v
        return str(field_val[0]) if field_val else ""
    return str(field_val) if field_val else ""

def parse_ted_date(raw):
    """Parse a TED date value to YYYY-MM-DD.

    TED v3 returns:
      PD (publication date) — string like "2025-04-15+02:00" or "2023-12-06Z"
      DT (deadline)         — list like ["2025-05-12T16:00:00+01:00"]
    """
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    s = str(raw or "").strip()
    if not s:
        return ""
    # Take only the date portion (first 10 chars of YYYY-MM-DD)
    s10 = s[:10]
    try:
        return datetime.strptime(s10, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        pass
    # Legacy YYYYMMDD format
    try:
        return datetime.strptime(s10.replace("-", ""), "%Y%m%d").strftime("%Y-%m-%d")
    except Exception:
        pass
    return ""

def _run_ted_query(q, fields, scope=1, limit=50, seen_nd=None, filter_title=True,
                   cpv_label=""):
    """Execute one TED query and return list of tender dicts.

    filter_title=False: used for CPV queries — the CPV code is the signal,
    so we accept generic titles like 'Construction work' (they are relevant
    because they're tagged with a fit-out CPV code). We still de-dup by ND.
    """
    if seen_nd is None:
        seen_nd = set()
    results = []
    payload = {"query": q, "fields": fields, "page": 1, "limit": limit, "scope": scope}
    data = post_json(TED_URL, payload)
    if not data:
        time.sleep(1)
        return results

    total = data.get("totalNoticeCount", 0)
    log.info(f"   {q!r}: {total} total")

    for n in data.get("notices", []):
        ti_raw = n.get("TI", {})
        eng_title = pick_eng(ti_raw)
        if not eng_title:
            continue

        # Strip country/city prefix TED adds: "Netherlands-Amsterdam: Joinery work"
        if ": " in eng_title:
            eng_title = eng_title.split(": ", 1)[1]

        # For title queries, ensure the title contains fit-out vocabulary.
        # For CPV queries, the code IS the filter — accept all (CPV is precise).
        if filter_title and not is_fitout_title(eng_title):
            continue

        nd = str(n.get("ND") or n.get("publication-number") or "")

        # Filter to recent notices only — use publication year from ND as proxy
        nd_year = nd.split("-")[-1] if "-" in nd else "0"
        if nd_year.isdigit() and int(nd_year) < 2024:
            continue

        if nd in seen_nd:
            continue
        seen_nd.add(nd)

        cy_raw = n.get("CY", [])
        cy3 = cy_raw[0] if cy_raw else ""
        country = ISO3_TO_ISO2.get(cy3, cy3[:2] if cy3 else "")

        au_raw = n.get("AU", {})
        issuer = ""
        if isinstance(au_raw, dict):
            for lang_vals in au_raw.values():
                if isinstance(lang_vals, list) and lang_vals:
                    issuer = lang_vals[0]; break
                elif lang_vals:
                    issuer = str(lang_vals); break

        deadline  = parse_ted_date(n.get("DT"))   # list of ISO timestamps
        published = parse_ted_date(n.get("PD"))   # publication date string
        d_days    = days_until(deadline)

        # For CPV-based results with generic titles, append the CPV work type
        display_title = eng_title
        if cpv_label and not is_fitout_title(eng_title):
            display_title = f"{eng_title} – {cpv_label} works"

        results.append({
            "id": make_id("ted", nd or eng_title),
            "title": display_title,
            "issuer": issuer,
            "issuer_country": country,
            "issuer_country_name": COUNTRY_NAMES.get(country, country),
            "issuer_flag": COUNTRY_FLAGS.get(country, "🌍"),
            "continent": continent_from_country(country),
            "category": categorize(display_title, issuer=issuer),
            "published": published,
            "deadline": deadline,
            "deadline_days": d_days,
            "value_min": 0, "value_max": 0,
            "value_currency": "EUR",
            "value_display": "",
            "source": "TED EU",
            "source_url": f"https://ted.europa.eu/en/notice/-/detail/{nd}" if nd else "",
            "reference": nd,
            "status": status_from_days(d_days),
            "description_preview": "",
            "is_premium": True,
        })
    return results


def fetch_ted():
    results = []
    log.info("📡 TED EU — title queries...")
    seen_nd = set()

    for q in TED_TITLE_QUERIES:
        batch = _run_ted_query(q, TED_FIELDS, seen_nd=seen_nd)
        results.extend(batch)
        time.sleep(0.8)

    log.info(f"   title queries → {len(results)} tenders")

    log.info("📡 TED EU — CPV code queries...")
    cpv_fields = ["ND", "TI", "CY", "AU", "DT", "DD", "PC", "publication-number"]
    for q, label in TED_CPV_QUERIES:
        # filter_title=True: CPV codes can be secondary on unrelated contracts,
        # so title-filter still improves precision significantly
        batch = _run_ted_query(q, cpv_fields, limit=100, seen_nd=seen_nd,
                               filter_title=True, cpv_label=label)
        log.info(f"   CPV {label} → {len(batch)} notices")
        results.extend(batch)
        time.sleep(1.0)

    log.info(f"   → {len(results)} TED tenders total")
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 2 — Contracts Finder (UK — below-threshold and awarded notices)
#  API: https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search
# ─────────────────────────────────────────────────────────────────────────────

CONTRACTS_FINDER_URL = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"

CF_FITOUT_WORDS = {
    "fit-out","fitout","fit out","interior","joinery","partition","shopfit",
    "refurb","tenant improvement","raised floor","ceiling","drylining",
    "mezzanine","finishing works","internal works","office renovation",
    "commercial fit","workspace","refit","decoration works","internal fit",
    "building completion","shopfitting","office works","internal refurbishment",
}

def fetch_contracts_finder():
    results = []
    log.info("📡 Contracts Finder UK...")
    seen = set()

    keywords = [
        "fit-out", "fitout", "interior refurbishment", "shopfitting",
        "tenant improvement", "office fit", "joinery works", "partitioning",
        "ceiling works", "drylining", "workspace fit",
    ]

    for kw in keywords:
        url = (f"{CONTRACTS_FINDER_URL}?keyword={urllib.parse.quote(kw)}"
               f"&status=Published&limit=25")
        raw = get_url(url, headers={"Accept": "application/json"})
        if not raw:
            time.sleep(0.5); continue
        try:
            data = json.loads(raw)
        except Exception:
            time.sleep(0.5); continue

        for rel in data.get("releases", []):
            t = rel.get("tender", {})
            title = (t.get("title") or "").strip()
            if not title:
                continue

            # Only include notices that contain fit-out terms in title
            title_lower = title.lower()
            if not any(w in title_lower for w in CF_FITOUT_WORDS):
                continue

            slug = re.sub(r'\W+', '', title_lower)[:60]
            if slug in seen:
                continue
            seen.add(slug)

            ocid = rel.get("ocid", "")
            published = (rel.get("date") or "")[:10]
            tp = t.get("tenderPeriod", {})
            deadline = (tp.get("endDate") or "")[:10]
            val = t.get("value", {})
            amount = float(val.get("amount", 0) or 0)
            buyer = rel.get("buyer", {}).get("name", "")
            desc = (t.get("description") or "")[:300]
            d_days = days_until(deadline)
            notice_id = ocid.replace("ocds-b5fd17-", "") if ocid else make_id("cf", title)

            results.append({
                "id": make_id("cf", ocid or title),
                "title": title,
                "issuer": buyer,
                "issuer_country": "GB",
                "issuer_country_name": "United Kingdom",
                "issuer_flag": "🇬🇧",
                "continent": "Europe",
                "category": categorize(title, desc),
                "published": published,
                "deadline": deadline,
                "deadline_days": d_days,
                "value_min": amount,
                "value_max": amount,
                "value_currency": "GBP",
                "value_display": fmt_value(amount, amount, "GBP"),
                "source": "Contracts Finder",
                "source_url": f"https://www.contractsfinder.service.gov.uk/Notice/{notice_id}",
                "reference": ocid,
                "status": status_from_days(d_days),
                "description_preview": desc,
                "is_premium": True,
            })

        time.sleep(0.5)

    log.info(f"   → {len(results)} tenders")
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 3 — UK Find a Tender Service (above-threshold)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_find_a_tender():
    results = []
    log.info("📡 UK Find a Tender...")

    for keyword in ["fit-out", "fitout", "interior refurbishment", "shopfitting", "tenant improvement"]:
        url = (
            "https://www.find-tender.service.gov.uk/api/1.0/ocds/opportunities/"
            f"?query={urllib.parse.quote(keyword)}&limit=50"
        )
        raw = get_url(url, headers={"Accept": "application/json"})
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        for release in data.get("releases", []):
            t = release.get("tender", {})
            title = t.get("title","").strip()
            if not title:
                continue

            ref = release.get("ocid","") or t.get("id","")
            published = (release.get("date","") or "")[:10]
            tp = t.get("tenderPeriod", {})
            deadline = (tp.get("endDate","") or "")[:10]

            value_min = value_max = 0
            val = t.get("value", {})
            if val.get("amount"): value_min = value_max = float(val["amount"])
            minv = t.get("minValue", {}); maxv = t.get("maxValue", {})
            if minv.get("amount"): value_min = float(minv["amount"])
            if maxv.get("amount"): value_max = float(maxv["amount"])

            buyer = release.get("buyer",{}).get("name","")
            desc = (t.get("description","") or "")[:300]
            d_days = days_until(deadline)
            notice_id = ref.replace("ocds-b5fd17-","")

            results.append({
                "id": make_id("uk", ref or title),
                "title": title,
                "issuer": buyer,
                "issuer_country": "GB",
                "issuer_country_name": "United Kingdom",
                "issuer_flag": "🇬🇧",
                "continent": "Europe",
                "category": categorize(title, desc),
                "published": published,
                "deadline": deadline,
                "deadline_days": d_days,
                "value_min": value_min,
                "value_max": value_max,
                "value_currency": "GBP",
                "value_display": fmt_value(value_min, value_max, "GBP"),
                "source": "Find a Tender",
                "source_url": f"https://www.find-tender.service.gov.uk/Notice/{notice_id}",
                "reference": ref,
                "status": status_from_days(d_days),
                "description_preview": desc,
                "is_premium": True,
            })

        time.sleep(0.5)

    log.info(f"   → {len(results)} tenders")
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 4 — SAM.gov (US federal procurement)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_sam_gov():
    results = []
    log.info("📡 SAM.gov (US)...")

    from_date = (datetime.now() - timedelta(days=120)).strftime("%m/%d/%Y")

    for keyword in ["fit-out", "interior fit-out", "tenant improvement", "fitout", "shopfitting"]:
        url = (
            "https://api.sam.gov/opportunities/v2/search"
            f"?api_key=DEMO_KEY"
            f"&keywords={urllib.parse.quote(keyword)}"
            f"&ptype=o"
            f"&postedFrom={urllib.parse.quote(from_date)}"
            f"&limit=25&offset=0"
        )
        raw = get_url(url)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        for opp in (data.get("opportunitiesData") or []):
            title = opp.get("title","").strip()
            if not title:
                continue

            deadline = (opp.get("responseDeadLine","") or "")[:10]
            published = (opp.get("postedDate","") or "")[:10]
            ref = opp.get("noticeId","") or opp.get("solicitationNumber","")

            org = ""
            hier = opp.get("organizationHierarchy") or []
            if hier and isinstance(hier[0], dict):
                org = hier[0].get("name","")

            d_days = days_until(deadline)

            results.append({
                "id": make_id("sam", ref or title),
                "title": title,
                "issuer": org,
                "issuer_country": "US",
                "issuer_country_name": "United States",
                "issuer_flag": "🇺🇸",
                "continent": "Americas",
                "category": categorize(title),
                "published": published,
                "deadline": deadline,
                "deadline_days": d_days,
                "value_min": 0, "value_max": 0,
                "value_currency": "USD",
                "value_display": "",
                "source": "SAM.gov",
                "source_url": opp.get("uiLink","") or f"https://sam.gov/opp/{ref}/view",
                "reference": opp.get("solicitationNumber","") or ref,
                "status": status_from_days(d_days),
                "description_preview": "",
                "is_premium": True,
            })

        time.sleep(1)

    log.info(f"   → {len(results)} tenders")
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 5 — AusTender (Australia)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_austender():
    results = []
    log.info("📡 AusTender (AU)...")

    for term in ["fit-out", "fitout", "interior refurbishment"]:
        url = (
            "https://www.tenders.gov.au/atm/SearchResult"
            f"?AtmType=1&SearchFrom=MultipleSearch"
            f"&Title={urllib.parse.quote(term)}"
            f"&Row=1&Columns=30&OrderBy=CLOSINGDATE"
        )
        raw = get_url(url)
        if not raw:
            continue

        rows = re.findall(
            r'<tr[^>]*class="[^"]*(?:alternate|odd|even)[^"]*"[^>]*>(.*?)</tr>',
            raw, re.DOTALL | re.IGNORECASE
        )

        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) < 4:
                continue

            m = re.search(r'href="(/atm/[^"]+)"[^>]*>(.*?)</a', cells[0], re.DOTALL)
            if not m:
                continue
            src_url = "https://www.tenders.gov.au" + m.group(1)
            title = re.sub(r'\s+', ' ', re.sub("<[^>]+>","", m.group(2))).strip()
            agency = re.sub(r'\s+', ' ', re.sub("<[^>]+>","", cells[1])).strip()
            raw_dl = re.sub(r'\s+', ' ', re.sub("<[^>]+>","", cells[3])).strip()

            deadline = ""
            for fmt in ("%d/%m/%Y %I:%M %p", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
                try:
                    deadline = datetime.strptime(raw_dl, fmt).strftime("%Y-%m-%d"); break
                except: pass

            d_days = days_until(deadline)
            results.append({
                "id": make_id("au", src_url),
                "title": title,
                "issuer": agency,
                "issuer_country": "AU",
                "issuer_country_name": "Australia",
                "issuer_flag": "🇦🇺",
                "continent": "Asia Pacific",
                "category": categorize(title),
                "published": "",
                "deadline": deadline,
                "deadline_days": d_days,
                "value_min": 0, "value_max": 0,
                "value_currency": "AUD",
                "value_display": "",
                "source": "AusTender",
                "source_url": src_url,
                "reference": "",
                "status": status_from_days(d_days),
                "description_preview": "",
                "is_premium": True,
            })

        time.sleep(0.5)

    log.info(f"   → {len(results)} tenders")
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 6 — Google News RSS (global tender announcements — 80+ queries)
#  Covers: Middle East, Europe, Asia Pacific, Americas, Africa, sector-specific
# ─────────────────────────────────────────────────────────────────────────────

TEXT_TO_COUNTRY = {
    # Middle East
    "UAE":"AE","Dubai":"AE","Abu Dhabi":"AE","Sharjah":"AE","Ajman":"AE","Ras Al Khaimah":"AE",
    "Saudi":"SA","Riyadh":"SA","Jeddah":"SA","KSA":"SA","NEOM":"SA","Mecca":"SA","Medina":"SA",
    "Red Sea":"SA","Vision 2030":"SA",
    "Qatar":"QA","Doha":"QA","Lusail":"QA",
    "Kuwait":"KW","Kuwait City":"KW",
    "Bahrain":"BH","Manama":"BH",
    "Oman":"OM","Muscat":"OM","Salalah":"OM",
    "Jordan":"JO","Amman":"JO",
    "Lebanon":"LB","Beirut":"LB",
    "Iraq":"IQ","Baghdad":"IQ",
    "Egypt":"EG","Cairo":"EG","Alexandria":"EG",
    # Europe
    "UK":"GB","United Kingdom":"GB","London":"GB","Manchester":"GB","Edinburgh":"GB",
    "Birmingham":"GB","Glasgow":"GB","Bristol":"GB","Leeds":"GB","Cardiff":"GB",
    "Scotland":"GB","Wales":"GB","England":"GB",
    "Ireland":"IE","Dublin":"IE","Cork":"IE",
    "France":"FR","Paris":"FR","Lyon":"FR","Marseille":"FR",
    "Germany":"DE","Berlin":"DE","Frankfurt":"DE","Munich":"DE","Hamburg":"DE","Düsseldorf":"DE",
    "Spain":"ES","Madrid":"ES","Barcelona":"ES","Valencia":"ES","Seville":"ES",
    "Netherlands":"NL","Amsterdam":"NL","Rotterdam":"NL","The Hague":"NL",
    "Italy":"IT","Milan":"IT","Rome":"IT","Turin":"IT",
    "Belgium":"BE","Brussels":"BE","Antwerp":"BE",
    "Switzerland":"CH","Zurich":"CH","Geneva":"CH",
    "Sweden":"SE","Stockholm":"SE","Gothenburg":"SE",
    "Norway":"NO","Oslo":"NO","Bergen":"NO",
    "Denmark":"DK","Copenhagen":"DK",
    "Finland":"FI","Helsinki":"FI",
    "Poland":"PL","Warsaw":"PL","Krakow":"PL","Wroclaw":"PL",
    "Portugal":"PT","Lisbon":"PT","Porto":"PT",
    "Austria":"AT","Vienna":"AT",
    "Czech Republic":"CZ","Prague":"CZ",
    "Romania":"RO","Bucharest":"RO",
    "Turkey":"TR","Istanbul":"TR","Ankara":"TR",
    "Ukraine":"UA","Kyiv":"UA",
    # Asia Pacific
    "Singapore":"SG",
    "Hong Kong":"HK",
    "Australia":"AU","Sydney":"AU","Melbourne":"AU","Brisbane":"AU","Perth":"AU",
    "New Zealand":"NZ","Auckland":"NZ","Wellington":"NZ",
    "India":"IN","Mumbai":"IN","Delhi":"IN","Bangalore":"IN","Hyderabad":"IN",
    "Pune":"IN","Chennai":"IN","Ahmedabad":"IN","Kolkata":"IN","Gurgaon":"IN",
    "China":"CN","Shanghai":"CN","Beijing":"CN","Shenzhen":"CN","Guangzhou":"CN",
    "Japan":"JP","Tokyo":"JP","Osaka":"JP","Nagoya":"JP",
    "South Korea":"KR","Seoul":"KR","Busan":"KR",
    "Malaysia":"MY","Kuala Lumpur":"MY","KL":"MY","Penang":"MY",
    "Indonesia":"ID","Jakarta":"ID","Bali":"ID",
    "Vietnam":"VN","Ho Chi Minh":"VN","Hanoi":"VN",
    "Thailand":"TH","Bangkok":"TH","Phuket":"TH",
    "Philippines":"PH","Manila":"PH",
    "Taiwan":"TW","Taipei":"TW",
    # Americas
    "USA":"US","United States":"US","New York":"US","Chicago":"US","Los Angeles":"US",
    "Washington":"US","Texas":"US","California":"US","Florida":"US","Boston":"US",
    "Seattle":"US","San Francisco":"US","Denver":"US","Atlanta":"US",
    "Canada":"CA","Toronto":"CA","Vancouver":"CA","Ottawa":"CA","Calgary":"CA","Montreal":"CA",
    "Brazil":"BR","São Paulo":"BR","Rio de Janeiro":"BR","Brasilia":"BR",
    "Mexico":"MX","Mexico City":"MX","Monterrey":"MX",
    "Argentina":"AR","Buenos Aires":"AR",
    "Colombia":"CO","Bogotá":"CO","Medellin":"CO",
    "Chile":"CL","Santiago":"CL",
    "Peru":"PE","Lima":"PE",
    # Africa
    "South Africa":"ZA","Johannesburg":"ZA","Cape Town":"ZA","Durban":"ZA","Pretoria":"ZA",
    "Nigeria":"NG","Lagos":"NG","Abuja":"NG",
    "Kenya":"KE","Nairobi":"KE","Mombasa":"KE",
    "Ghana":"GH","Accra":"GH",
    "Ethiopia":"ET","Addis Ababa":"ET",
    "Morocco":"MA","Casablanca":"MA","Rabat":"MA",
    "Tanzania":"TZ","Dar es Salaam":"TZ",
    "Rwanda":"RW","Kigali":"RW",
}

GNEWS_QUERIES = [
    # ═══════════════════════════════════════════════════════════════════════════
    # ── Core universal ────────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    ('"fit-out" tender OR RFP OR bid 2026',                          None),
    ('"fit-out" contract awarded OR secured OR won 2026',            None),
    ('"fitout" tender OR procurement 2025 OR 2026',                  None),
    ('"interior fit-out" tender OR contract OR bid',                 None),
    ('"office fit-out" tender OR procurement OR RFP',                None),
    ('"commercial fit-out" tender OR contract',                      None),
    ('"interior refurbishment" tender OR contract OR procurement',   None),
    ('"shopfitting" tender OR contract OR bid',                      None),
    ('"joinery works" tender OR contract',                           None),
    ('"partitioning works" tender OR contract',                      None),
    ('"interior works" tender bid OR RFP 2026',                      None),
    ('"interior construction" tender OR contract 2026',              None),
    ('"fit-out works" tender OR bid 2026',                           None),

    # ═══════════════════════════════════════════════════════════════════════════
    # ── Middle East — open tenders ────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    ('"fit-out" tender Dubai OR "Abu Dhabi" OR UAE 2026',            "Middle East"),
    ('"fit-out" tender Saudi OR Riyadh OR Jeddah OR NEOM 2026',     "Middle East"),
    ('"fit-out" tender Qatar OR Doha OR Kuwait OR Bahrain 2026',    "Middle East"),
    ('"fit-out" tender Oman OR Muscat OR Jordan 2026',               "Middle East"),
    ('"fit-out" RFP OR EOI OR bid UAE OR Saudi OR Qatar 2026',      "Middle East"),
    ('"Vision 2030" fit-out OR "interior works" tender OR RFP',     "Middle East"),
    ('fitout RFP OR bid Riyadh OR NEOM OR "Red Sea" 2025 OR 2026',  "Middle East"),
    ('"interior works" tender OR RFP UAE OR Saudi Arabia 2026',     "Middle East"),
    ('site:etimad.sa interior OR fitout OR "fit-out"',              "Middle East"),
    ('site:gtenders.com "fit-out" OR "interior" Saudi OR UAE 2026', "Middle East"),

    # ── Middle East — contract awards (the news that actually gets published) ──
    ('interior fit-out contract awarded Dubai 2025 OR 2026',        "Middle East"),
    ('fit-out contract awarded OR secured UAE 2025 OR 2026',        "Middle East"),
    ('fit-out contract won OR secured Riyadh OR Saudi 2025 OR 2026',"Middle East"),
    ('interior fit-out contract Qatar OR Doha 2025 OR 2026',        "Middle East"),
    ('fit-out contract Kuwait OR Bahrain OR Oman 2025 OR 2026',     "Middle East"),
    ('hotel fit-out contract awarded "Middle East" 2025 OR 2026',   "Middle East"),
    ('luxury fit-out contract awarded UAE OR Saudi 2025 OR 2026',   "Middle East"),
    ('interior works contract awarded Dubai OR "Abu Dhabi" 2026',   "Middle East"),
    ('"interior fit-out" contract awarded OR secured "Middle East"', "Middle East"),
    ('office fit-out contract won OR awarded Riyadh OR Dubai 2026', "Middle East"),
    ('shopfit contract awarded OR secured UAE OR Saudi 2026',       "Middle East"),
    ('fitout contract wins GCC OR "Gulf" 2025 OR 2026',             "Middle East"),

    # ═══════════════════════════════════════════════════════════════════════════
    # ── Europe — UK ───────────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    ('"fit-out" tender London OR UK OR Britain 2026',                "Europe"),
    ('"fit-out" tender Manchester OR Birmingham OR Edinburgh 2026',  "Europe"),
    ('"fit-out" tender Ireland OR Dublin 2026',                      "Europe"),
    ('fitout contract award UK OR Ireland 2025 OR 2026',             "Europe"),
    ('site:contractsfinder.service.gov.uk "fit-out" OR "fitout"',   "Europe"),
    ('site:find-tender.service.gov.uk "fit-out" 2026',              "Europe"),
    # ── Europe — Western ──────────────────────────────────────────────────────
    ('"fit-out" tender France OR Paris 2026',                        "Europe"),
    ('"fit-out" tender Germany OR Berlin OR Frankfurt 2026',         "Europe"),
    ('"fit-out" tender Netherlands OR Amsterdam OR Rotterdam 2026',  "Europe"),
    ('"fit-out" tender Spain OR Madrid OR Barcelona 2026',           "Europe"),
    ('"fit-out" tender Italy OR Milan OR Rome 2026',                 "Europe"),
    ('"fit-out" tender Belgium OR Brussels OR Switzerland 2026',     "Europe"),
    ('"interior refurbishment" tender Europe 2026',                  "Europe"),
    # ── Europe — Nordic & Eastern ─────────────────────────────────────────────
    ('"fit-out" tender Sweden OR Norway OR Denmark OR Finland 2026', "Europe"),
    ('"fit-out" tender Poland OR Warsaw OR Portugal OR Lisbon 2026', "Europe"),
    ('"fit-out" tender Austria OR Czech OR Turkey OR Istanbul 2026', "Europe"),
    ('"fit-out" tender Romania OR Ukraine OR Bulgaria 2026',         "Europe"),
    ('site:ted.europa.eu "fit-out" OR "shopfitting" 2026',          "Europe"),
    ('site:doffin.no "interior" OR "innredning" 2026',              "Europe"),
    ('site:tenderned.nl "interieur" OR "inrichting" 2026',          "Europe"),
    ('site:etenders.gov.ie "fit-out" OR "interior" 2026',           "Europe"),

    # ═══════════════════════════════════════════════════════════════════════════
    # ── Asia Pacific ──────────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    ('"fit-out" tender Singapore OR "Hong Kong" 2026',               "Asia Pacific"),
    ('"fit-out" tender Australia OR Sydney OR Melbourne 2026',       "Asia Pacific"),
    ('"fit-out" tender "New Zealand" OR Auckland 2026',              "Asia Pacific"),
    ('fitout procurement Australia OR "New South Wales" 2026',       "Asia Pacific"),
    ('site:gebiz.gov.sg "fit-out" OR "interior" 2026',              "Asia Pacific"),
    ('"fit-out" tender India OR Mumbai OR Bangalore 2026',           "Asia Pacific"),
    ('"fit-out" tender Delhi OR Hyderabad OR Pune 2026',             "Asia Pacific"),
    ('"interior works" tender India 2026',                           "Asia Pacific"),
    ('"fit-out" tender China OR Shanghai OR Japan OR Tokyo 2026',    "Asia Pacific"),
    ('"fit-out" tender Malaysia OR "Kuala Lumpur" OR Vietnam 2026',  "Asia Pacific"),
    ('"fit-out" tender Thailand OR Philippines OR Indonesia 2026',   "Asia Pacific"),

    # ═══════════════════════════════════════════════════════════════════════════
    # ── Americas — US (key: use solicitation/RFP/bid not "tender") ────────────
    # ═══════════════════════════════════════════════════════════════════════════
    ('"tenant improvement" RFP OR solicitation OR bid 2026',         "Americas"),
    ('"tenant improvement" contract awarded OR won 2025 OR 2026',    "Americas"),
    ('"office build-out" OR "office buildout" RFP OR bid 2026',      "Americas"),
    ('"commercial interior" RFP OR solicitation 2026',               "Americas"),
    ('"interior fit-out" RFP OR bid OR solicitation USA OR Canada',  "Americas"),
    ('"fit-out" RFP OR bid "New York" OR Manhattan OR Chicago 2026', "Americas"),
    ('"fit-out" RFP OR bid California OR Texas OR Florida 2026',     "Americas"),
    ('interior refurbishment contract "United States" 2025 OR 2026', "Americas"),
    ('site:sam.gov "fit-out" OR "fitout" OR "tenant improvement"',   "Americas"),
    # ── Canada ────────────────────────────────────────────────────────────────
    ('"fit-out" tender OR RFP Canada OR Toronto OR Vancouver 2026',  "Americas"),
    ('"interior fit-out" contract awarded Canada 2025 OR 2026',      "Americas"),
    ('site:canadabuys.canada.ca "fit-out" OR "interior" 2026',       "Americas"),
    ('fit-out OR fitout contract awarded OR won Canada 2025 OR 2026',"Americas"),
    # ── Latin America ─────────────────────────────────────────────────────────
    ('"fit-out" tender OR contract Brazil OR "São Paulo" 2026',      "Americas"),
    ('"fit-out" tender OR bid Mexico OR "Mexico City" 2026',         "Americas"),
    ('"interior works" contract OR bid "Latin America" 2026',        "Americas"),
    ('"fit-out" OR fitout contract Colombia OR Chile OR Peru 2026',  "Americas"),
    # ── Caribbean ─────────────────────────────────────────────────────────────
    ('"fit-out" tender Caribbean OR Jamaica OR Barbados 2026',       "Americas"),
    ('"fit-out" tender "Trinidad" OR "Dominican Republic" 2026',     "Americas"),
    ('"fit-out" tender Bahamas OR Cayman OR "Puerto Rico" 2026',     "Americas"),
    ('interior construction tender "Caribbean Development Bank" 2026',"Americas"),

    # ═══════════════════════════════════════════════════════════════════════════
    # ── Africa — open tenders ─────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    ('"fit-out" tender "South Africa" OR Johannesburg 2026',         "Africa"),
    ('"fit-out" tender Nigeria OR Lagos OR Kenya OR Nairobi 2026',   "Africa"),
    ('"fit-out" tender Africa 2026',                                 "Africa"),
    ('"fit-out" tender Ghana OR Egypt OR Morocco OR Ethiopia 2026',  "Africa"),
    ('"interior fit-out" tender OR contract "West Africa" 2026',     "Africa"),
    ('"interior fit-out" tender OR contract "East Africa" 2026',     "Africa"),
    ('"shopfitting" tender OR contract "South Africa" 2025 OR 2026', "Africa"),
    ('interior construction tender "African Development Bank" OR AfDB 2026', "Africa"),
    ('site:ungm.org "interior" OR "fit-out" Africa 2026',           "Africa"),
    ('UNGM "interior" OR "fit-out" Africa procurement 2026',         "Africa"),
    # ── Africa — contract awards ───────────────────────────────────────────────
    ('interior fit-out contract awarded "South Africa" 2025 OR 2026',"Africa"),
    ('interior refurbishment contract Kenya OR Nigeria 2025 OR 2026', "Africa"),
    ('fit-out contract won OR awarded Africa 2025 OR 2026',          "Africa"),
    ('interior works contract Ghana OR Rwanda OR Tanzania 2026',     "Africa"),
    ('building refurbishment contract "South Africa" 2025 OR 2026',  "Africa"),
    ('interior renovation contract Cairo OR Nairobi 2025 OR 2026',  "Africa"),
    ('shopfitting contract "South Africa" OR Nigeria 2025 OR 2026',  "Africa"),
    ('refurbishment contract awarded Africa 2025 OR 2026',           "Africa"),

    # ═══════════════════════════════════════════════════════════════════════════
    # ── Sector specific ───────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    ('"hotel fit-out" tender OR contract awarded 2025 OR 2026',      None),
    ('"retail fit-out" tender OR contract awarded 2025 OR 2026',     None),
    ('"office fit-out" contract awarded OR won 2025 OR 2026',        None),
    ('"hospital fit-out" OR "healthcare fit-out" tender 2026',       None),
    ('"restaurant fit-out" tender OR contract 2026',                 None),
    ('"airport fit-out" OR "terminal fit-out" tender OR contract',   None),
    ('"data centre fit-out" OR "data center fitout" tender 2026',    None),
    ('"luxury fit-out" tender OR contract awarded 2025 OR 2026',     None),
    ('"showroom fit-out" tender OR RFP OR contract 2026',            None),

    # ── Global portals ────────────────────────────────────────────────────────
    ('site:afdb.org "interior" OR "fit-out" OR "refurbishment"',    "Africa"),
    ('site:ungm.org "interior" OR "fit-out" 2026',                  None),

    # ═══════════════════════════════════════════════════════════════════════════
    # ── International language queries ────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════

    # German — Innenausbau (interior fit-out) tenders
    ('Innenausbau Ausschreibung 2025 OR 2026',                       "Europe"),
    ('Büroausbau Ausschreibung OR Auftrag 2025 OR 2026',             "Europe"),
    ('Ladenausbau Ausschreibung OR Vergabe 2026',                    "Europe"),
    ('Hotelausbau Ausschreibung OR Auftrag 2026',                    "Europe"),
    ('Innenausbau Auftrag vergeben 2025 OR 2026',                    "Europe"),
    ('gewerblicher Innenausbau Auftrag 2026',                        "Europe"),

    # French — aménagement intérieur (interior fit-out) tenders
    ('aménagement intérieur appel offres 2025 OR 2026',              "Europe"),
    ('agencement commercial marché OR appel 2026',                   "Europe"),
    ('aménagement bureaux marché public 2026',                       "Europe"),
    ('travaux aménagement intérieur attribution 2025 OR 2026',       "Europe"),
    ('agencement hôtel marché OR contrat 2026',                      "Europe"),

    # Spanish — acondicionamiento / obra interior tenders
    ('acondicionamiento oficinas licitación 2025 OR 2026',           "Europe"),
    ('obra acondicionamiento interior contrato 2026',                "Europe"),
    ('reforma interior contrato adjudicado 2025 OR 2026',            "Europe"),
    ('interiorismo comercial licitación OR contrato 2026',           "Europe"),

    # Dutch — afbouw / interieurinrichting tenders
    ('kantoorinrichting aanbesteding 2025 OR 2026',                  "Europe"),
    ('afbouw kantoor opdracht OR aanbesteding 2026',                 "Europe"),
    ('interieurinrichting opdracht vergund 2025 OR 2026',            "Europe"),

    # Italian — allestimento interni tenders
    ('allestimento interni gara OR appalto 2025 OR 2026',            "Europe"),
    ('ristrutturazione uffici appalto OR contratto 2026',            "Europe"),
    ('lavori allestimento interni aggiudicazione 2025 OR 2026',      "Europe"),

    # Nordic — Swedish / Danish / Norwegian
    ('kontorsanpassning upphandling 2025 OR 2026',                   "Europe"),
    ('inredning kontor upphandling OR avtal 2026',                   "Europe"),
    ('indretning kontor udbud OR kontrakt 2026',                     "Europe"),
    ('kontortilpasning anbud OR kontrakt 2026',                      "Europe"),

    # Japanese — 内装工事 (interior construction) tenders
    ('内装工事 入札 2025 OR 2026',                                     "Asia Pacific"),
    ('内装工事 発注 OR 落札 2026',                                     "Asia Pacific"),
    ('店舗内装工事 入札 OR 契約 2026',                                 "Asia Pacific"),
    ('オフィス内装 受注 OR 契約 2025 OR 2026',                         "Asia Pacific"),

    # Chinese — 室内装修 (interior fit-out) tenders
    ('室内装修工程 招标 2025 OR 2026',                                 "Asia Pacific"),
    ('装饰装修工程 招标 OR 中标 2026',                                 "Asia Pacific"),
    ('办公室装修 合同 OR 招标 2026',                                   "Asia Pacific"),

    # Arabic — تشطيبات (finishing/fit-out) tenders
    ('تشطيبات داخلية مناقصة 2025 OR 2026',                           "Middle East"),
    ('أعمال التشطيب عقد OR مناقصة 2026',                             "Middle East"),
    ('تشطيب مكاتب عقد OR مناقصة 2026',                               "Middle East"),

    # US — Tenant improvement / build-out (not "tender") solicitations
    ('"tenant improvement" solicitation OR RFP 2026',                "Americas"),
    ('"interior build-out" solicitation OR contract awarded 2026',   "Americas"),
    ('"leasehold improvement" contract awarded 2025 OR 2026',        "Americas"),
    ('"commercial interior" construction contract awarded 2026',     "Americas"),
    ('"interior construction" RFP OR solicitation 2026 USA',         "Americas"),

    # Brazilian Portuguese
    ('reforma escritório contrato OR licitação 2025 OR 2026',        "Americas"),
    ('retrofit escritório contrato adjudicado 2026',                 "Americas"),
    ('interiores comerciais licitação OR contrato 2026 Brasil',      "Americas"),
]

def parse_gnews_date(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
        try:
            return datetime.strptime((s or "").strip(), fmt).strftime("%Y-%m-%d")
        except: pass
    return ""

def guess_country(title, desc):
    text = title + " " + desc
    for name, code in TEXT_TO_COUNTRY.items():
        if re.search(r'\b' + re.escape(name) + r'\b', text, re.IGNORECASE):
            return code
    return ""

def fetch_google_news_tenders():
    results = []
    log.info(f"📡 Google News ({len(GNEWS_QUERIES)} queries)...")

    FITOUT_RE = re.compile(
        r'\bfit[\-\s]?out\b|\bfitout\b'
        r'|\binterior\s+(?:fit|refurb|works|renovation|construction|design|upgrade|refit)\b'
        r'|\bshopfit'
        r'|\btenant\s+(?:improvement|fit|works?)\b'
        r'|\bjoinery\s+works?\b'
        r'|\bpartition(?:ing)?\s+works?\b'
        r'|\bworkspace\s+fit\b'
        r'|\boffice\s+(?:fit|renovation|refurb|buildout|build[\-\s]out|interior|refit)\b'
        r'|\bretail\s+(?:fit|renovation|interior|refurb)\b'
        r'|\bcommercial\s+interior\b'
        r'|\bbuild[\-\s]?out\b'
        r'|\brefurbishment\b'
        r'|\bsuspended\s+ceiling\b'
        r'|\bdrylining\b|\bdrywall\b'
        r'|\bmezzanine\b'
        # International equivalents
        r'|Innenausbau|B.roausbau|Ladenausbau|Hotelausbau'          # German
        r'|am.nagement\s+int.rieur|agencement\s+commercial'         # French
        r'|acondicionamiento|interiorismo\s+comercial'               # Spanish
        r'|afbouw|interieurinrichting|kantoorinrichting'             # Dutch
        r'|allestimento\s+interni|ristrutturazione\s+uffici'         # Italian
        r'|kontorsanpassning|inredningsentreprenad|indretning\s+kontor'  # Nordic
        r'|内装工事|室内装修'       # Japanese/Chinese
        r'|تشطيبات|تشطيب',  # Arabic
        re.IGNORECASE
    )
    TENDER_RE = re.compile(
        r'\btender\b|\bRFP\b|\bbid(?:ding|s)?\b|\bprocurement\b|\bcontract\b'
        r'|\baward(?:ed|s)?\b'          # fix: \baward\b misses "awarded"
        r'|\bITT\b|\bRFI\b|\bRFQ\b|\bIFB\b|\bITB\b'
        r'|\bsolicitation\b|\bproposal\b|\bEOI\b|\bexpression\s+of\s+interest\b'
        r'|\bprequalification\b|\bshortlist(?:ed)?\b'
        r'|\bwins?\b|\bwon\b|\bsecures?\b|\bsign(?:s|ed)?\b'   # "secures contract"
        r'|\binvitation\b|\btendering\b',
        re.IGNORECASE
    )

    seen_titles = set()
    # Only include news from the past 18 months (stale items pollute the feed)
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=548)).strftime("%Y-%m-%d")

    for query, hint_continent in GNEWS_QUERIES:
        url = (
            "https://news.google.com/rss/search"
            f"?q={urllib.parse.quote(query)}&hl=en&gl=GB&ceid=GB:en"
        )
        raw = get_url(url)
        if not raw:
            time.sleep(0.5); continue

        try:
            root = ET.fromstring(raw)
        except Exception:
            continue

        for item in root.findall(".//item"):
            def txt(tag):
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""

            title = txt("title")
            link  = txt("link")
            desc  = re.sub("<[^>]+>", " ", txt("description"))
            pub   = parse_gnews_date(txt("pubDate"))
            src   = txt("source")

            if not title or title in seen_titles:
                continue

            # Skip stale articles older than 18 months
            if pub and pub < cutoff_date:
                continue

            combined = title + " " + desc
            # FITOUT_RE: check title primarily; fall back to desc for articles
            # where title is generic (e.g. "Company wins contract at X")
            if not FITOUT_RE.search(title) and not FITOUT_RE.search(desc):
                continue
            if not TENDER_RE.search(combined):
                continue

            seen_titles.add(title)
            country_code = guess_country(title, desc)
            continent = continent_from_country(country_code) if country_code else (hint_continent or "Other")

            results.append({
                "id": make_id("gn", link or title),
                "title": title,
                "issuer": "",
                "issuer_country": country_code,
                "issuer_country_name": COUNTRY_NAMES.get(country_code, ""),
                "issuer_flag": COUNTRY_FLAGS.get(country_code, "🌍"),
                "continent": continent,
                "category": categorize(title, desc),
                "published": pub,
                "deadline": "",
                "deadline_days": None,
                "value_min": 0, "value_max": 0,
                "value_currency": "",
                "value_display": "",
                "source": src or "News",
                "source_url": link,
                "reference": "",
                "status": "open",
                "description_preview": desc[:250],
                "is_premium": False,
            })

        time.sleep(0.4)

    log.info(f"   → {len(results)} items")
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE 7 — GeBIZ (Singapore) via Google News
# ─────────────────────────────────────────────────────────────────────────────

def fetch_gebiz():
    results = []
    log.info("📡 GeBIZ (Singapore) via news...")

    for q in ["gebiz fit-out tender Singapore", "singapore government fit-out procurement 2026"]:
        url = (f"https://news.google.com/rss/search"
               f"?q={urllib.parse.quote(q)}&hl=en&gl=SG&ceid=SG:en")
        raw = get_url(url)
        if not raw:
            continue
        try:
            root = ET.fromstring(raw)
            for item in root.findall(".//item"):
                def txt(tag):
                    el = item.find(tag)
                    return (el.text or "").strip() if el is not None else ""
                title = txt("title")
                if "fit" not in title.lower() and "interior" not in title.lower():
                    continue
                results.append({
                    "id": make_id("sg", txt("link") or title),
                    "title": title,
                    "issuer": "",
                    "issuer_country": "SG",
                    "issuer_country_name": "Singapore",
                    "issuer_flag": "🇸🇬",
                    "continent": "Asia Pacific",
                    "category": categorize(title),
                    "published": parse_gnews_date(txt("pubDate")),
                    "deadline": "",
                    "deadline_days": None,
                    "value_min": 0, "value_max": 0,
                    "value_currency": "SGD", "value_display": "",
                    "source": txt("source") or "GeBIZ News",
                    "source_url": txt("link"),
                    "reference": "",
                    "status": "open",
                    "description_preview": re.sub("<[^>]+>"," ",txt("description"))[:200],
                    "is_premium": False,
                })
        except Exception:
            pass
        time.sleep(0.4)

    log.info(f"   → {len(results)} items")
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def deduplicate(tenders):
    seen = {}
    out  = []
    for t in tenders:
        k = t.get("id","")
        if k and k in seen:
            continue
        if k:
            seen[k] = True
        slug = re.sub(r'\W+','', t.get("title","").lower())[:60]
        if slug in seen:
            continue
        seen[slug] = True
        out.append(t)
    return out

def sort_key(t):
    d = t.get("deadline_days")
    s = t.get("status","open")
    if s == "closing_soon": base = 0
    elif s == "open":        base = 1
    else:                    base = 3
    return (base, d if d is not None else 9999)

def main():
    all_tenders = []

    SOURCES = [
        ("TED EU",             fetch_ted),
        ("Contracts Finder",   fetch_contracts_finder),
        ("Find a Tender UK",   fetch_find_a_tender),
        ("SAM.gov US",         fetch_sam_gov),
        ("AusTender AU",       fetch_austender),
        ("Google News",        fetch_google_news_tenders),
        ("GeBIZ SG",           fetch_gebiz),
    ]

    for name, fn in SOURCES:
        try:
            batch = fn()
            all_tenders.extend(batch)
            log.info(f"   subtotal: {len(all_tenders)}")
        except Exception as e:
            log.error(f"  ✗ {name} crashed: {e}")

    # Remove notices closed more than 30 days ago
    cutoff = -30
    filtered = [t for t in all_tenders
                if t.get("deadline_days") is None
                or t["deadline_days"] >= cutoff
                or not t.get("deadline")]
    if filtered:
        all_tenders = filtered

    all_tenders = deduplicate(all_tenders)
    all_tenders.sort(key=sort_key)

    # Stamp fetch time on every item
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for t in all_tenders:
        t.setdefault("accessed_at", fetched_at)

    # Stats
    by_continent = {}
    by_status    = {"open":0,"closing_soon":0,"closed":0,"unknown":0}
    by_category  = {}
    by_source    = {}
    for t in all_tenders:
        c = t.get("continent","Other")
        by_continent[c] = by_continent.get(c,0) + 1
        s = t.get("status","open")
        by_status[s] = by_status.get(s,0) + 1
        cat = t.get("category","Commercial")
        by_category[cat] = by_category.get(cat,0) + 1
        src = t.get("source","Other")
        by_source[src] = by_source.get(src,0) + 1

    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total": len(all_tenders),
        "by_continent": by_continent,
        "by_status": by_status,
        "by_category": by_category,
        "by_source": by_source,
        "tenders": all_tenders,
    }

    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"\n✅  {len(all_tenders)} tenders saved → tenders.json")
    log.info(f"   Open: {by_status.get('open',0)}  |  Closing soon: {by_status.get('closing_soon',0)}  |  Closed: {by_status.get('closed',0)}")
    for cont, n in sorted(by_continent.items(), key=lambda x:-x[1]):
        log.info(f"   {cont}: {n}")


if __name__ == "__main__":
    main()
