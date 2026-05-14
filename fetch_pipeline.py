#!/usr/bin/env python3
"""
fetch_pipeline.py — FitOut Post Pipeline Aggregator

Collects project pipeline signals that indicate future fit-out demand:
  - Hotel openings / pipeline announcements
  - Museum / cultural centre projects
  - Office tower / commercial developments
  - Retail / mall / mixed-use developments
  - Healthcare facility developments
  - Education campus projects
  - Stadia / sports / leisure developments
  - Major infrastructure driving interior demand

Sources: Google News RSS (200+ queries across all sectors and regions)

Output: pipeline.json
    {
      "last_updated": "ISO",
      "total": N,
      "by_sector": {...},
      "by_continent": {...},
      "projects": [ { ... } ]
    }

Usage:
    python fetch_pipeline.py
"""

import json
import logging
import re
import time
import urllib.parse
import urllib.request
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE    = Path(__file__).parent
OUT     = BASE / "pipeline.json"
MAX_AGE = 548   # days — 18 months rolling window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ─── Country / continent mapping ──────────────────────────────────────────────

COUNTRY_FLAGS = {
    "AE":"🇦🇪","SA":"🇸🇦","QA":"🇶🇦","KW":"🇰🇼","BH":"🇧🇭","OM":"🇴🇲",
    "JO":"🇯🇴","EG":"🇪🇬","LB":"🇱🇧","IQ":"🇮🇶","MA":"🇲🇦","TN":"🇹🇳",
    "GB":"🇬🇧","IE":"🇮🇪","FR":"🇫🇷","DE":"🇩🇪","NL":"🇳🇱","ES":"🇪🇸",
    "IT":"🇮🇹","BE":"🇧🇪","CH":"🇨🇭","SE":"🇸🇪","NO":"🇳🇴","DK":"🇩🇰",
    "FI":"🇫🇮","PL":"🇵🇱","PT":"🇵🇹","AT":"🇦🇹","CZ":"🇨🇿","TR":"🇹🇷",
    "RO":"🇷🇴","GR":"🇬🇷","HU":"🇭🇺","HR":"🇭🇷","SK":"🇸🇰","BG":"🇧🇬",
    "US":"🇺🇸","CA":"🇨🇦","MX":"🇲🇽","BR":"🇧🇷","AR":"🇦🇷","CO":"🇨🇴",
    "CL":"🇨🇱","PE":"🇵🇪","PA":"🇵🇦","JM":"🇯🇲","BB":"🇧🇧","TT":"🇹🇹",
    "DO":"🇩🇴","BS":"🇧🇸","KY":"🇰🇾","PR":"🇵🇷","CU":"🇨🇺","HT":"🇭🇹",
    "AU":"🇦🇺","NZ":"🇳🇿","SG":"🇸🇬","HK":"🇭🇰","JP":"🇯🇵","KR":"🇰🇷",
    "CN":"🇨🇳","IN":"🇮🇳","TH":"🇹🇭","VN":"🇻🇳","MY":"🇲🇾","ID":"🇮🇩",
    "PH":"🇵🇭","PK":"🇵🇰","LK":"🇱🇰","BD":"🇧🇩",
    "ZA":"🇿🇦","NG":"🇳🇬","KE":"🇰🇪","GH":"🇬🇭","ET":"🇪🇹","TZ":"🇹🇿",
    "UG":"🇺🇬","MZ":"🇲🇿","CM":"🇨🇲","SN":"🇸🇳","CI":"🇨🇮","RW":"🇷🇼",
    "MU":"🇲🇺","AO":"🇦🇴","ZM":"🇿🇲",
}

COUNTRY_NAMES = {
    "AE":"UAE","SA":"Saudi Arabia","QA":"Qatar","KW":"Kuwait","BH":"Bahrain",
    "OM":"Oman","JO":"Jordan","EG":"Egypt","LB":"Lebanon","IQ":"Iraq",
    "MA":"Morocco","TN":"Tunisia",
    "GB":"United Kingdom","IE":"Ireland","FR":"France","DE":"Germany",
    "NL":"Netherlands","ES":"Spain","IT":"Italy","BE":"Belgium","CH":"Switzerland",
    "SE":"Sweden","NO":"Norway","DK":"Denmark","FI":"Finland","PL":"Poland",
    "PT":"Portugal","AT":"Austria","CZ":"Czech Republic","TR":"Turkey",
    "RO":"Romania","GR":"Greece","HU":"Hungary","HR":"Croatia",
    "US":"United States","CA":"Canada","MX":"Mexico","BR":"Brazil","AR":"Argentina",
    "CO":"Colombia","CL":"Chile","PE":"Peru","PA":"Panama",
    "JM":"Jamaica","BB":"Barbados","TT":"Trinidad","DO":"Dominican Republic",
    "BS":"Bahamas","KY":"Cayman Islands","PR":"Puerto Rico","CU":"Cuba",
    "AU":"Australia","NZ":"New Zealand","SG":"Singapore","HK":"Hong Kong",
    "JP":"Japan","KR":"South Korea","CN":"China","IN":"India","TH":"Thailand",
    "VN":"Vietnam","MY":"Malaysia","ID":"Indonesia","PH":"Philippines",
    "ZA":"South Africa","NG":"Nigeria","KE":"Kenya","GH":"Ghana","ET":"Ethiopia",
    "TZ":"Tanzania","UG":"Uganda","MZ":"Mozambique","CM":"Cameroon","SN":"Senegal",
    "CI":"Ivory Coast","RW":"Rwanda","MU":"Mauritius","AO":"Angola","ZM":"Zambia",
}

COUNTRY_TO_CONTINENT = {
    "AE":"Middle East","SA":"Middle East","QA":"Middle East","KW":"Middle East",
    "BH":"Middle East","OM":"Middle East","JO":"Middle East","EG":"Africa",
    "IQ":"Middle East","LB":"Middle East","MA":"Africa","TN":"Africa",
    "GB":"Europe","IE":"Europe","FR":"Europe","DE":"Europe","NL":"Europe",
    "ES":"Europe","IT":"Europe","BE":"Europe","CH":"Europe","SE":"Europe",
    "NO":"Europe","DK":"Europe","FI":"Europe","PL":"Europe","PT":"Europe",
    "AT":"Europe","CZ":"Europe","TR":"Europe","RO":"Europe","GR":"Europe",
    "HU":"Europe","HR":"Europe","SK":"Europe","BG":"Europe",
    "US":"Americas","CA":"Americas","MX":"Americas","BR":"Americas","AR":"Americas",
    "CO":"Americas","CL":"Americas","PE":"Americas","PA":"Americas",
    "JM":"Americas","BB":"Americas","TT":"Americas","DO":"Americas",
    "BS":"Americas","KY":"Americas","PR":"Americas","CU":"Americas","HT":"Americas",
    "AU":"Asia Pacific","NZ":"Asia Pacific","SG":"Asia Pacific","HK":"Asia Pacific",
    "JP":"Asia Pacific","KR":"Asia Pacific","CN":"Asia Pacific","IN":"Asia Pacific",
    "TH":"Asia Pacific","VN":"Asia Pacific","MY":"Asia Pacific","ID":"Asia Pacific",
    "PH":"Asia Pacific","PK":"Asia Pacific","LK":"Asia Pacific","BD":"Asia Pacific",
    "ZA":"Africa","NG":"Africa","KE":"Africa","GH":"Africa","ET":"Africa",
    "TZ":"Africa","UG":"Africa","MZ":"Africa","CM":"Africa","SN":"Africa",
    "CI":"Africa","RW":"Africa","MU":"Africa","AO":"Africa","ZM":"Africa",
}

TEXT_TO_COUNTRY = {
    # ME
    "UAE":"AE","Dubai":"AE","Abu Dhabi":"AE","Sharjah":"AE","Ajman":"AE",
    "Ras Al Khaimah":"AE","DIFC":"AE","Dubai Creek":"AE",
    "Saudi":"SA","Riyadh":"SA","Jeddah":"SA","KSA":"SA","NEOM":"SA","Mecca":"SA",
    "Medina":"SA","Tabuk":"SA","KAEC":"SA","Red Sea Project":"SA","AlUla":"SA",
    "Diriyah":"SA","Qiddiya":"SA","ROSHN":"SA","Amaala":"SA","Sindalah":"SA",
    "Qatar":"QA","Doha":"QA","Lusail":"QA","Msheireb":"QA",
    "Kuwait":"KW","Kuwait City":"KW","Bahrain":"BH","Manama":"BH",
    "Oman":"OM","Muscat":"OM","Salalah":"OM","Jordan":"JO","Amman":"JO",
    "Egypt":"EG","Cairo":"EG","Alexandria":"EG","New Cairo":"EG","Lebanon":"LB",
    "Morocco":"MA","Casablanca":"MA","Marrakech":"MA","Rabat":"MA",
    # Europe
    "UK":"GB","Britain":"GB","England":"GB","London":"GB","Manchester":"GB",
    "Edinburgh":"GB","Birmingham":"GB","Glasgow":"GB","Liverpool":"GB","Bristol":"GB",
    "Ireland":"IE","Dublin":"IE","France":"FR","Paris":"FR","Lyon":"FR","Nice":"FR",
    "Germany":"DE","Berlin":"DE","Munich":"DE","Frankfurt":"DE","Hamburg":"DE",
    "Netherlands":"NL","Amsterdam":"NL","Rotterdam":"NL","Netherlands":"NL",
    "Spain":"ES","Madrid":"ES","Barcelona":"ES","Seville":"ES","Valencia":"ES",
    "Malaga":"ES","Ibiza":"ES","Marbella":"ES","Palma":"ES",
    "Italy":"IT","Milan":"IT","Rome":"IT","Venice":"IT","Florence":"IT","Naples":"IT",
    "Belgium":"BE","Brussels":"BE","Switzerland":"CH","Zurich":"CH","Geneva":"CH",
    "Sweden":"SE","Stockholm":"SE","Norway":"NO","Oslo":"NO","Denmark":"DK",
    "Copenhagen":"DK","Finland":"FI","Helsinki":"FI","Poland":"PL","Warsaw":"PL",
    "Krakow":"PL","Portugal":"PT","Lisbon":"PT","Porto":"PT","Algarve":"PT",
    "Austria":"AT","Vienna":"AT","Czech":"CZ","Prague":"CZ","Turkey":"TR",
    "Istanbul":"TR","Ankara":"TR","Romania":"RO","Bucharest":"RO","Greece":"GR",
    "Athens":"GR","Croatia":"HR","Dubrovnik":"HR","Hungary":"HU","Budapest":"HU",
    # Americas
    "United States":"US","USA":"US","America":"US","New York":"US","Manhattan":"US",
    "Los Angeles":"US","Chicago":"US","Houston":"US","Dallas":"US","Miami":"US",
    "Las Vegas":"US","Orlando":"US","Atlanta":"US","Boston":"US","Seattle":"US",
    "San Francisco":"US","Washington":"US","Denver":"US","Nashville":"US",
    "Canada":"CA","Toronto":"CA","Vancouver":"CA","Montreal":"CA","Calgary":"CA",
    "Mexico":"MX","Mexico City":"MX","Cancun":"MX","Guadalajara":"MX","Los Cabos":"MX",
    "Brazil":"BR","São Paulo":"BR","Rio de Janeiro":"BR","Sao Paulo":"BR",
    "Argentina":"AR","Buenos Aires":"AR","Colombia":"CO","Bogotá":"CO","Medellin":"CO",
    "Chile":"CL","Santiago":"CL","Peru":"PE","Lima":"PE","Panama":"PA",
    "Jamaica":"JM","Kingston":"JM","Barbados":"BB","Bridgetown":"BB",
    "Trinidad":"TT","Dominican Republic":"DO","Punta Cana":"DO","Santo Domingo":"DO",
    "Bahamas":"BS","Nassau":"BS","Cayman":"KY","Cayman Islands":"KY",
    "Puerto Rico":"PR","Cuba":"CU","Havana":"CU","Aruba":"AW",
    "Caribbean":"JM",  # hint only
    "Saint Lucia":"LC","Antigua":"AG","Grenada":"GD","Dominica":"DM",
    # Asia Pacific
    "Australia":"AU","Sydney":"AU","Melbourne":"AU","Brisbane":"AU","Perth":"AU",
    "Gold Coast":"AU","Adelaide":"AU",
    "New Zealand":"NZ","Auckland":"NZ","Queenstown":"NZ",
    "Singapore":"SG","Hong Kong":"HK","Japan":"JP","Tokyo":"JP","Osaka":"JP",
    "Kyoto":"JP","South Korea":"KR","Seoul":"KR","Busan":"KR",
    "China":"CN","Shanghai":"CN","Beijing":"CN","Shenzhen":"CN","Guangzhou":"CN",
    "Hainan":"CN","Sanya":"CN",
    "India":"IN","Mumbai":"IN","Bangalore":"IN","Delhi":"IN","Hyderabad":"IN",
    "Chennai":"IN","Goa":"IN","Rajasthan":"IN",
    "Thailand":"TH","Bangkok":"TH","Phuket":"TH","Chiang Mai":"TH","Koh Samui":"TH",
    "Vietnam":"VN","Ho Chi Minh":"VN","Hanoi":"VN","Da Nang":"VN","Hoi An":"VN",
    "Malaysia":"MY","Kuala Lumpur":"MY","Penang":"MY","Langkawi":"MY",
    "Indonesia":"ID","Jakarta":"ID","Bali":"ID","Lombok":"ID",
    "Philippines":"PH","Manila":"PH","Cebu":"PH","Boracay":"PH",
    "Maldives":"MV","Sri Lanka":"LK","Colombo":"LK",
    # Africa
    "South Africa":"ZA","Johannesburg":"ZA","Cape Town":"ZA","Durban":"ZA",
    "Pretoria":"ZA","Sandton":"ZA",
    "Nigeria":"NG","Lagos":"NG","Abuja":"NG","Kigali":"RW","Rwanda":"RW",
    "Kenya":"KE","Nairobi":"KE","Mombasa":"KE","Tanzania":"TZ","Dar es Salaam":"TZ",
    "Ethiopia":"ET","Addis Ababa":"ET","Ghana":"GH","Accra":"GH",
    "Ivory Coast":"CI","Abidjan":"CI","Senegal":"SN","Dakar":"SN",
    "Cameroon":"CM","Yaoundé":"CM","Mauritius":"MU","Port Louis":"MU",
    "Angola":"AO","Luanda":"AO","Zambia":"ZM","Lusaka":"ZM",
    "Mozambique":"MZ","Maputo":"MZ","Uganda":"UG","Kampala":"UG",
    "Morocco":"MA","Casablanca":"MA","Marrakech":"MA",
    "Egypt":"EG","Cairo":"EG","Sharm El Sheikh":"EG","Hurghada":"EG",
    "Tunisia":"TN","Tunis":"TN",
}

# ─── Sector classification ─────────────────────────────────────────────────────

SECTOR_KEYWORDS = {
    "Hospitality": [
        "hotel","resort","marriott","hilton","hyatt","ihg","accor","radisson","wyndham",
        "four seasons","ritz","bulgari","mandarin","peninsula","shangri-la","aman",
        "six senses","rosewood","raffles","banyan tree","nobu","w hotel","edition hotel",
        "intercontinental","crowne plaza","doubletree","holiday inn","sheraton","westin",
        "sofitel","pullman","mgallery","mondrian","st regis","waldorf","park hyatt",
        "andaz","aloft","viceroy","one&only","belmond","jumeirah","kempinski","langham",
        "mövenpick","rotana","anantara","avani","nh hotel","melia","riu","iberostar",
        "sandals","karisma","nickelodeon","all-inclusive","hospitality","guestroom",
        "branded residence","resort opening","hotel opening","hotel development",
        "hotel pipeline","hotel brand","hotel group","luxury lodge","safari lodge",
        "boutique hotel","lifestyle hotel","flagship hotel","hotel construction",
    ],
    "Cultural & Museums": [
        "museum","gallery","cultural centre","arts centre","cultural center",
        "national museum","science museum","art gallery","louvre","guggenheim",
        "moma","tate","smithsonian","natural history","maritime museum",
        "heritage","exhibition centre","cultural district","arts district",
        "performing arts","concert hall","opera house","theatre","theater",
        "cultural complex","world expo","pavilion","cultural hub","cultural quarter",
        "visitor centre","interpretation centre","memorial","monument","aquarium",
        "science center","planetarium","library","archive",
    ],
    "Offices & Workplace": [
        "office tower","office building","office park","office campus","headquarters",
        "hq","corporate campus","business district","business park","mixed-use office",
        "co-working","coworking","workspace","commercial tower","grade a office",
        "office complex","tech campus","office development","office scheme",
        "office district","office hub","central business district","cbd",
    ],
    "Retail & Mixed-Use": [
        "shopping mall","shopping centre","shopping center","retail mall","retail park",
        "outlet mall","outlet centre","flagship store","department store",
        "lifestyle centre","lifestyle center","entertainment district","retail district",
        "mixed-use","mixed use","retail development","luxury mall","high street",
        "town centre","retail complex","retail hub","fashion mall",
    ],
    "Healthcare": [
        "hospital","clinic","medical centre","medical center","healthcare facility",
        "health city","health hub","wellness centre","wellness center","medical city",
        "health campus","research hospital","cancer centre","cancer center",
        "children's hospital","private hospital","specialist hospital","polyclinic",
        "healthcare development","healthcare complex",
    ],
    "Education": [
        "university","college","school","campus","education campus","academic building",
        "student accommodation","student housing","academy","polytechnic",
        "research centre","science park","knowledge hub","education city",
        "international school","american school","british school","stem campus",
    ],
    "Sports & Leisure": [
        "stadium","arena","sports complex","velodrome","aquatic centre","aquatic center",
        "theme park","entertainment park","water park","leisure complex",
        "sports hub","sports city","entertainment venue","convention centre",
        "convention center","exhibition centre","exhibition center","expo",
        "race track","race circuit","golf resort","ski resort","sports resort",
        "esports arena","indoor arena",
    ],
    "Infrastructure & Transport": [
        "airport","terminal","transit hub","metro station","rail station","port",
        "cruise terminal","ferry terminal","transport hub","logistics hub",
        "gateway","interchange",
    ],
}

def classify_sector(title, desc):
    text = (title + " " + desc).lower()
    for sector, kws in SECTOR_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return sector
    return "Commercial Development"

def guess_country(title, desc):
    text = title + " " + desc
    for name, code in TEXT_TO_COUNTRY.items():
        if re.search(r'\b' + re.escape(name) + r'\b', text, re.IGNORECASE):
            return code
    return ""

def continent_from_country(code):
    return COUNTRY_TO_CONTINENT.get(code, "Other")

def make_id(title, link=""):
    raw = (title + link)[:120]
    return "pl_" + hashlib.md5(raw.encode()).hexdigest()[:10]

# ─── HTTP helpers ──────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FitOutPost/1.0; +https://fitoutpost.com)",
    "Accept": "application/rss+xml,application/xml,text/xml,*/*;q=0.8",
}

def get_url(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get_content_charset("utf-8")
            return raw.decode(enc, errors="replace")
    except Exception as e:
        log.debug(f"GET failed {url}: {e}")
        return None

def parse_date(s):
    """Parse RSS pubDate, return YYYY-MM-DD or ''."""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
        try:
            return datetime.strptime((s or "").strip(), fmt).strftime("%Y-%m-%d")
        except: pass
    return ""

# ─── Google News queries ───────────────────────────────────────────────────────
# Format: (query_string, hint_continent)
# ~230 queries across all sectors and regions

PIPELINE_QUERIES = [

    # ══ HOSPITALITY — Brand pipeline ═════════════════════════════════════════

    # Marriott group
    ('Marriott "hotel opening" OR "new hotel" OR pipeline 2025 OR 2026',   "Americas"),
    ('"JW Marriott" opening OR development 2025 OR 2026',                  None),
    ('"Westin" hotel opening OR development 2025 OR 2026',                 None),
    ('"W Hotel" opening OR development 2025 OR 2026',                      None),
    ('"Edition Hotel" opening OR development 2025 OR 2026',                None),
    ('"Ritz-Carlton" opening OR new hotel 2025 OR 2026',                   None),
    ('"St. Regis" hotel opening OR development 2025 OR 2026',              None),

    # Hilton group
    ('Hilton "hotel opening" OR "new hotel" OR pipeline 2025 OR 2026',     None),
    ('"Waldorf Astoria" opening OR new 2025 OR 2026',                      None),
    ('"Conrad Hotel" opening OR development 2025 OR 2026',                 None),
    ('"LXR Hotels" opening OR development 2025 OR 2026',                   None),
    ('"Curio Collection" hotel opening 2025 OR 2026',                      None),

    # IHG group
    ('IHG "hotel opening" OR "new hotel" pipeline 2025 OR 2026',           None),
    ('"InterContinental" hotel opening OR development 2025 OR 2026',       None),
    ('"Six Senses" opening OR new resort 2025 OR 2026',                    None),
    ('"Regent Hotels" opening OR development 2026',                        None),
    ('"Vignette Collection" hotel opening 2026',                           None),

    # Accor group
    ('Accor "hotel opening" OR new hotel pipeline 2025 OR 2026',           None),
    ('"Raffles" hotel opening OR development 2025 OR 2026',                None),
    ('"Sofitel" hotel opening OR development 2025 OR 2026',                None),
    ('"Fairmont" hotel opening OR development 2025 OR 2026',               None),
    ('"Banyan Tree" opening OR new resort 2025 OR 2026',                   None),
    ('"MGallery" hotel opening 2025 OR 2026',                              None),
    ('"Rixos" hotel opening OR development 2026',                          "Middle East"),

    # Hyatt group
    ('Hyatt "hotel opening" OR new hotel pipeline 2025 OR 2026',           None),
    ('"Park Hyatt" opening OR development 2025 OR 2026',                   None),
    ('"Grand Hyatt" opening OR development 2025 OR 2026',                  None),
    ('"Alila" hotel opening OR development 2025 OR 2026',                  None),
    ('"Andaz" hotel opening OR development 2025 OR 2026',                  None),

    # Luxury independent brands
    ('"Aman" resort opening OR development 2025 OR 2026',                  None),
    ('"Four Seasons" hotel opening OR development 2025 OR 2026',           None),
    ('"Mandarin Oriental" opening OR new hotel 2025 OR 2026',              None),
    ('"Rosewood Hotels" opening OR development 2025 OR 2026',              None),
    ('"One&Only" resort opening OR development 2026',                      None),
    ('"Bulgari Hotel" opening OR development 2026',                        None),
    ('"Bvlgari Hotel" opening OR development 2026',                        None),
    ('"Belmond" opening OR development 2025 OR 2026',                      None),
    ('"Peninsula Hotels" opening OR development 2025 OR 2026',             None),
    ('"Nobu Hotel" opening OR development 2025 OR 2026',                   None),
    ('"Viceroy Hotels" opening OR development 2025 OR 2026',               None),
    ('"Kempinski" hotel opening OR development 2025 OR 2026',              None),
    ('"Jumeirah" hotel opening OR development 2025 OR 2026',               "Middle East"),
    ('"Rotana" hotel opening OR development 2025 OR 2026',                 "Middle East"),
    ('"Anantara" resort opening OR development 2025 OR 2026',              None),
    ('"Langham" hotel opening OR development 2025 OR 2026',                None),
    ('"Capella Hotels" opening OR development 2026',                       None),
    ('"Auberge Resorts" opening OR development 2026',                      None),
    ('"Minor Hotels" opening OR development 2025 OR 2026',                 None),
    ('"Mövenpick" hotel opening OR development 2026',                      None),
    ('"NH Hotels" opening OR development 2025 OR 2026',                    "Europe"),
    ('"Meliá Hotels" opening OR development 2025 OR 2026',                 "Europe"),

    # ══ HOSPITALITY — Regional pipeline ══════════════════════════════════════

    # KSA / Vision 2030
    ('"new hotel" OR "hotel opening" Saudi Arabia OR Riyadh 2025 OR 2026', "Middle East"),
    ('"new hotel" OR "hotel opening" NEOM OR "Red Sea" OR AlUla 2026',    "Middle East"),
    ('"new hotel" OR "hotel opening" Jeddah OR Mecca OR Medina 2026',     "Middle East"),
    ('"luxury hotel" development OR opening Diriyah OR Qiddiya 2026',     "Middle East"),
    ('hotel pipeline "Vision 2030" OR "Saudi tourism" 2025 OR 2026',      "Middle East"),
    ('"Amaala" OR "Sindalah" hotel development 2026',                     "Middle East"),

    # UAE
    ('"new hotel" OR "hotel opening" Dubai 2025 OR 2026',                  "Middle East"),
    ('"new hotel" OR "hotel opening" "Abu Dhabi" 2025 OR 2026',           "Middle East"),
    ('"luxury hotel" development OR pipeline UAE 2025 OR 2026',            "Middle East"),
    ('hotel development "Yas Island" OR "Palm Jumeirah" 2026',             "Middle East"),
    ('hotel opening OR development "Expo City" OR "Dubai Creek" 2026',    "Middle East"),

    # Rest of ME
    ('"new hotel" OR "hotel opening" Qatar OR Doha 2025 OR 2026',         "Middle East"),
    ('"new hotel" OR "hotel opening" Oman OR Muscat 2025 OR 2026',        "Middle East"),
    ('"new hotel" OR "hotel opening" Bahrain OR Kuwait 2025 OR 2026',     "Middle East"),
    ('"new hotel" OR "hotel opening" Jordan OR Amman 2026',               "Middle East"),
    ('"new hotel" OR "hotel opening" Egypt OR Cairo OR "Red Sea" 2026',   "Africa"),

    # Europe
    ('"new hotel" OR "hotel opening" London OR UK 2025 OR 2026',          "Europe"),
    ('"new hotel" OR "hotel opening" Spain OR Madrid OR Barcelona 2026',   "Europe"),
    ('"luxury hotel" opening OR development Paris OR France 2026',         "Europe"),
    ('"new hotel" OR "hotel opening" Italy OR Rome OR Milan 2026',         "Europe"),
    ('"new hotel" OR "hotel opening" Greece OR Athens OR Mykonos 2026',   "Europe"),
    ('"new hotel" OR "hotel opening" Portugal OR Lisbon OR Algarve 2026', "Europe"),
    ('"new hotel" OR "hotel opening" Croatia OR Dubrovnik 2026',           "Europe"),
    ('"hotel pipeline" OR "hotel development" Germany OR Berlin 2026',    "Europe"),

    # Americas
    ('"new hotel" OR "hotel opening" "New York" OR Manhattan 2025 OR 2026',"Americas"),
    ('"new hotel" OR "hotel opening" "Las Vegas" OR Nevada 2025 OR 2026', "Americas"),
    ('"new hotel" OR "hotel opening" Miami OR Florida 2025 OR 2026',      "Americas"),
    ('"new hotel" OR "hotel opening" Nashville OR Nashville 2026',         "Americas"),
    ('"new hotel" OR "hotel opening" "Los Angeles" OR Hollywood 2026',    "Americas"),
    ('"new hotel" OR "hotel opening" Caribbean 2025 OR 2026',             "Americas"),
    ('"new hotel" OR "hotel opening" Mexico OR Cancun OR "Los Cabos" 2026',"Americas"),
    ('"new hotel" OR "hotel opening" Dominican Republic OR Punta Cana 2026',"Americas"),
    ('"luxury hotel" development OR pipeline "North America" 2026',        "Americas"),
    ('"new hotel" OR "hotel opening" Jamaica OR Bahamas OR Barbados 2026',"Americas"),
    ('"new resort" Caribbean OR "all-inclusive" development 2025 OR 2026', "Americas"),

    # Africa
    ('"new hotel" OR "hotel opening" "South Africa" OR Johannesburg 2026', "Africa"),
    ('"new hotel" OR "hotel opening" Kenya OR Nairobi OR Mombasa 2026',   "Africa"),
    ('"new hotel" OR "hotel opening" Nigeria OR Lagos 2026',               "Africa"),
    ('"new hotel" OR "hotel opening" Rwanda OR Kigali 2026',              "Africa"),
    ('"new hotel" OR "hotel opening" Ghana OR Accra 2026',                "Africa"),
    ('"luxury hotel" OR "safari lodge" development Africa 2025 OR 2026',  "Africa"),
    ('"new hotel" OR "hotel opening" Morocco OR Marrakech 2026',          "Africa"),
    ('"new hotel" OR "hotel opening" Ethiopia OR "Addis Ababa" 2026',     "Africa"),
    ('"hotel development" OR "resort development" Africa 2026',            "Africa"),

    # Asia Pacific
    ('"new hotel" OR "hotel opening" Bali OR Indonesia 2025 OR 2026',     "Asia Pacific"),
    ('"new hotel" OR "hotel opening" Thailand OR Phuket OR Bangkok 2026', "Asia Pacific"),
    ('"new hotel" OR "hotel opening" Vietnam OR "Da Nang" 2025 OR 2026', "Asia Pacific"),
    ('"new hotel" OR "hotel opening" Maldives 2025 OR 2026',              "Asia Pacific"),
    ('"new hotel" OR "hotel opening" India OR Goa OR Mumbai 2026',        "Asia Pacific"),
    ('"luxury hotel" development OR pipeline Japan OR Tokyo 2026',         "Asia Pacific"),
    ('"new hotel" OR "hotel opening" Singapore OR "Hong Kong" 2026',      "Asia Pacific"),
    ('"new hotel" OR "hotel opening" Australia OR Sydney 2026',            "Asia Pacific"),

    # ══ CULTURAL & MUSEUMS ════════════════════════════════════════════════════

    ('"new museum" development OR opening 2025 OR 2026',                   None),
    ('"cultural centre" OR "cultural center" development OR opening 2026', None),
    ('"arts centre" OR "arts center" development 2025 OR 2026',            None),
    ('museum development OR "museum project" Saudi OR KSA 2026',          "Middle East"),
    ('"NEOM" museum OR culture OR arts 2026',                              "Middle East"),
    ('"Diriyah" cultural OR museum OR arts 2026',                          "Middle East"),
    ('"museum" development OR opening UAE OR Dubai 2026',                  "Middle East"),
    ('"Louvre Abu Dhabi" expansion OR development 2025 OR 2026',           "Middle East"),
    ('"cultural district" development OR project 2025 OR 2026',            None),
    ('"performing arts" centre development OR opening 2025 OR 2026',       None),
    ('"concert hall" development OR construction 2025 OR 2026',            None),
    ('"opera house" development OR opening 2025 OR 2026',                  None),
    ('museum OR "arts centre" development Africa 2025 OR 2026',            "Africa"),
    ('museum OR "cultural centre" development Caribbean 2026',             "Americas"),
    ('"national museum" project OR development 2025 OR 2026',              None),
    ('"science museum" OR "science centre" development 2026',              None),
    ('"world expo" pavilion OR development 2025 OR 2026',                  None),
    ('"visitor centre" OR "heritage centre" development 2025 OR 2026',     None),
    ('"aquarium" development OR new 2025 OR 2026',                         None),
    ('"entertainment district" development 2025 OR 2026',                  None),

    # ══ OFFICES & COMMERCIAL ══════════════════════════════════════════════════

    ('"office tower" development OR construction 2025 OR 2026',            None),
    ('"office campus" development OR construction 2025 OR 2026',           None),
    ('"headquarters" new OR development OR move 2025 OR 2026',             None),
    ('"Grade A office" development 2025 OR 2026',                          None),
    ('"tech campus" development OR construction 2025 OR 2026',             None),
    ('"commercial tower" development 2025 OR 2026',                        None),
    ('"business district" development OR launch 2025 OR 2026',             None),
    ('"office development" NEOM OR "Vision 2030" 2026',                   "Middle East"),
    ('"office tower" development Dubai OR "Abu Dhabi" 2026',               "Middle East"),
    ('"financial district" development Middle East 2026',                  "Middle East"),
    ('"office development" London OR UK 2025 OR 2026',                     "Europe"),
    ('"office campus" development Africa 2025 OR 2026',                    "Africa"),
    ('"corporate campus" development OR construction Americas 2026',        "Americas"),

    # ══ RETAIL & MIXED-USE ═══════════════════════════════════════════════════

    ('"shopping mall" development OR opening 2025 OR 2026',                None),
    ('"outlet mall" OR "outlet centre" development 2025 OR 2026',          None),
    ('"mixed-use" development OR project 2025 OR 2026',                    None),
    ('"lifestyle centre" development 2025 OR 2026',                        None),
    ('"luxury mall" OR "luxury retail" development 2025 OR 2026',          None),
    ('"flagship store" OR "retail development" 2025 OR 2026',              None),
    ('"shopping mall" development Saudi OR KSA OR NEOM 2026',             "Middle East"),
    ('"shopping centre" development UAE OR Dubai 2026',                    "Middle East"),
    ('"retail development" Africa 2025 OR 2026',                           "Africa"),
    ('"shopping centre" development Caribbean 2026',                       "Americas"),
    ('"mall development" Asia OR Southeast Asia 2025 OR 2026',             "Asia Pacific"),
    ('"entertainment district" OR "retail district" development 2026',     None),

    # ══ HEALTHCARE ════════════════════════════════════════════════════════════

    ('"new hospital" development OR construction 2025 OR 2026',            None),
    ('"medical city" OR "health city" development 2025 OR 2026',           None),
    ('"hospital development" Saudi OR KSA 2026',                           "Middle East"),
    ('"hospital development" UAE OR Dubai 2026',                           "Middle East"),
    ('"medical centre" development Africa 2025 OR 2026',                   "Africa"),
    ('"hospital" development OR construction Caribbean 2026',              "Americas"),
    ('"healthcare campus" development 2025 OR 2026',                       None),
    ('"research hospital" development 2025 OR 2026',                       None),

    # ══ EDUCATION ════════════════════════════════════════════════════════════

    ('"university campus" development OR construction 2025 OR 2026',       None),
    ('"education city" development 2025 OR 2026',                          None),
    ('"international school" development OR opening 2025 OR 2026',         None),
    ('"university" new campus OR development Saudi OR KSA 2026',           "Middle East"),
    ('"university" development OR campus UAE 2026',                        "Middle East"),
    ('"education campus" development Africa 2025 OR 2026',                 "Africa"),

    # ══ SPORTS & LEISURE ══════════════════════════════════════════════════════

    ('"new stadium" OR "stadium development" 2025 OR 2026',                None),
    ('"sports complex" development 2025 OR 2026',                          None),
    ('"entertainment arena" development 2025 OR 2026',                     None),
    ('"theme park" development OR opening 2025 OR 2026',                   None),
    ('"water park" development 2025 OR 2026',                              None),
    ('"sports city" development 2025 OR 2026',                             None),
    ('"golf resort" development OR opening 2025 OR 2026',                  None),
    ('"Qiddiya" development OR opening 2025 OR 2026',                     "Middle East"),
    ('"entertainment city" Saudi OR KSA development 2026',                 "Middle East"),
    ('"esports arena" development 2025 OR 2026',                           None),
    ('"convention centre" development 2025 OR 2026',                       None),
    ('"exhibition centre" development 2025 OR 2026',                       None),

    # ══ INFRASTRUCTURE (demand signal) ════════════════════════════════════════

    ('"new airport" terminal development 2025 OR 2026',                    None),
    ('"airport expansion" OR "airport terminal" development 2026',         None),
    ('"cruise terminal" development 2025 OR 2026',                         None),
    ('"train station" development OR opening 2025 OR 2026',                None),

    # ══ GEOGRAPHIC DEEP-DIVES ════════════════════════════════════════════════

    # KSA mega-projects
    ('NEOM development OR opening OR construction 2025 OR 2026',           "Middle East"),
    ('"The Line" NEOM 2025 OR 2026',                                       "Middle East"),
    ('"Sindalah" island development 2026',                                  "Middle East"),
    ('"AlUla" development OR tourism 2025 OR 2026',                        "Middle East"),
    ('"Red Sea Project" development 2025 OR 2026',                         "Middle East"),
    ('"ROSHN" development OR opening 2026',                                 "Middle East"),
    ('"Diriyah Gate" development OR opening 2025 OR 2026',                 "Middle East"),
    ('"New Murabba" development 2026',                                      "Middle East"),
    ('"King Salman Park" Riyadh development 2026',                         "Middle East"),
    ('Saudi "giga-project" OR "mega-project" development 2026',            "Middle East"),
    ('"Saudi tourism" development OR investment 2025 OR 2026',             "Middle East"),

    # UAE mega-projects
    ('"Expo City Dubai" development 2025 OR 2026',                         "Middle East"),
    ('"Dubai Creek Harbour" development 2025 OR 2026',                     "Middle East"),
    ('"Marsa Al Arab" development 2026',                                    "Middle East"),
    ('"Yas Island" development 2025 OR 2026',                              "Middle East"),
    ('"Saadiyat Island" development 2025 OR 2026',                         "Middle East"),
    ('"Abu Dhabi" tourism development OR investment 2025 OR 2026',         "Middle East"),

    # Qatar
    ('"Lusail" development OR opening 2025 OR 2026',                       "Middle East"),
    ('"Msheireb" development OR project 2025 OR 2026',                     "Middle East"),
    ('Qatar development OR "mega-project" 2025 OR 2026',                   "Middle East"),

    # Africa deep-dive
    ('"Kigali" development OR investment 2025 OR 2026',                    "Africa"),
    ('"Lagos" development OR "new district" 2025 OR 2026',                 "Africa"),
    ('"Nairobi" development OR construction 2025 OR 2026',                 "Africa"),
    ('"Accra" development OR construction 2026',                           "Africa"),
    ('"African Union" project development 2026',                           "Africa"),
    ('"African Development Bank" project 2025 OR 2026',                    "Africa"),
    ('"Cape Town" development OR construction 2025 OR 2026',               "Africa"),
    ('"Dakar" development OR construction 2026',                           "Africa"),

    # Caribbean deep-dive
    ('"Caribbean" resort OR hotel development 2025 OR 2026',               "Americas"),
    ('Sandals OR "Beaches" resort development OR opening 2025 OR 2026',   "Americas"),
    ('Karisma OR "Nickelodeon" resort development 2026',                   "Americas"),
    ('"Atlantis" expansion OR new development 2025 OR 2026',               "Americas"),
    ('Jamaica resort development OR opening 2025 OR 2026',                 "Americas"),
    ('Barbados resort development OR opening 2026',                         "Americas"),
    ('"Dominican Republic" resort development 2025 OR 2026',               "Americas"),
    ('"Turks and Caicos" development 2025 OR 2026',                        "Americas"),
    ('Bahamas resort OR hotel development 2025 OR 2026',                   "Americas"),
    ('"Cayman Islands" development OR hotel 2026',                         "Americas"),
    ('St Lucia OR "Saint Lucia" resort development 2026',                  "Americas"),
    ('Antigua OR Grenada resort development 2026',                         "Americas"),

    # Spain — strong pipeline
    ('"new hotel" OR resort development Spain 2025 OR 2026',               "Europe"),
    ('Mallorca OR Ibiza OR Menorca hotel development 2026',                "Europe"),
    ('Canary Islands hotel development OR opening 2025 OR 2026',           "Europe"),
    ('"Costa del Sol" OR Marbella development 2025 OR 2026',              "Europe"),
    ('Barcelona hotel development OR opening 2026',                        "Europe"),
    ('Madrid development OR "new hotel" OR office 2026',                   "Europe"),

    # North America broad
    ('"mixed-use" development "New York" 2025 OR 2026',                    "Americas"),
    ('"resort development" Florida OR "Sunny Isle" 2026',                  "Americas"),
    ('"new resort" OR "hotel development" "Las Vegas" 2026',               "Americas"),
    ('"hotel development" Nashville OR Austin OR Dallas 2026',             "Americas"),
    ('"new resort" OR "hotel development" Hawaii 2026',                    "Americas"),
    ('"resort development" Canada OR Banff OR Whistler 2026',              "Americas"),

    # Asia big pipeline
    ('"Bali" resort OR hotel development 2025 OR 2026',                    "Asia Pacific"),
    ('"Phuket" resort OR hotel development 2025 OR 2026',                  "Asia Pacific"),
    ('"Da Nang" resort OR hotel development 2025 OR 2026',                 "Asia Pacific"),
    ('Japan hotel OR resort development 2025 OR 2026',                     "Asia Pacific"),
    ('"India" hotel OR resort development 2025 OR 2026',                   "Asia Pacific"),
    ('"Maldives" resort development OR opening 2025 OR 2026',              "Asia Pacific"),
    ('"Sri Lanka" resort OR hotel development 2026',                       "Asia Pacific"),

    # ══ INTERNATIONAL LANGUAGE QUERIES ═══════════════════════════════════════

    # German — Innenausbau pipeline signals
    ('Innenausbau Projekt geplant 2025 OR 2026',                           "Europe"),
    ('Büroausbau Projekt 2025 OR 2026',                                    "Europe"),
    ('Hotelausbau Eröffnung OR Entwicklung 2026',                         "Europe"),
    ('gewerblicher Innenausbau Neubau 2026',                              "Europe"),
    ('Ladenausbau Eröffnung 2025 OR 2026',                                "Europe"),
    ('Innenausbau Großprojekt 2026',                                      "Europe"),

    # French — aménagement / hôtel pipeline
    ('aménagement intérieur projet 2025 OR 2026',                         "Europe"),
    ('hôtel ouverture OR développement 2025 OR 2026',                     "Europe"),
    ('agencement commercial projet 2026',                                 "Europe"),
    ('nouveau bureau aménagement 2025 OR 2026',                           "Europe"),
    ('rénovation hôtel ouverture 2025 OR 2026',                           "Europe"),

    # Spanish — desarrollo hotel / proyecto
    ('hotel apertura OR desarrollo España 2025 OR 2026',                  "Europe"),
    ('proyecto interiorismo comercial 2025 OR 2026',                      "Europe"),
    ('acondicionamiento proyecto nuevo 2026',                             "Europe"),
    ('hotel desarrollo apertura México 2025 OR 2026',                    "Americas"),
    ('hotel desarrollo apertura Colombia OR Chile 2026',                  "Americas"),

    # Brazilian Portuguese — pipeline
    ('hotel abertura OR desenvolvimento Brasil 2025 OR 2026',             "Americas"),
    ('escritório retrofit projeto 2025 OR 2026',                          "Americas"),
    ('desenvolvimento imobiliário São Paulo 2025 OR 2026',               "Americas"),

    # Italian — pipeline signals
    ('hotel apertura OR sviluppo Italia 2025 OR 2026',                    "Europe"),
    ('progetto interni commerciali 2025 OR 2026',                        "Europe"),
    ('nuovo hotel apertura Milano OR Roma 2026',                          "Europe"),

    # Dutch — pipeline signals
    ('kantoor inrichting project 2025 OR 2026',                           "Europe"),
    ('nieuw hotel opening Nederland 2025 OR 2026',                        "Europe"),
    ('kantoorontwikkeling project 2026',                                  "Europe"),

    # Nordic — Swedish pipeline
    ('hotell öppning OR utveckling Sverige 2025 OR 2026',                 "Europe"),
    ('kontorsprojekt inredning 2025 OR 2026',                            "Europe"),
    ('hotell åpning OR utvikling Norge 2025 OR 2026',                    "Europe"),
    ('hotel åbning OR udvikling Danmark 2025 OR 2026',                   "Europe"),

    # Japanese pipeline signals
    ('ホテル 開業 OR 開発 2025 OR 2026',                                   "Asia Pacific"),
    ('内装工事 計画 2025 OR 2026',                                         "Asia Pacific"),
    ('オフィス リノベーション 2025 OR 2026',                               "Asia Pacific"),
    ('商業施設 内装 開業 2026',                                            "Asia Pacific"),

    # Chinese pipeline signals
    ('酒店 开业 OR 开发 2025 OR 2026',                                     "Asia Pacific"),
    ('办公室装修 项目 2025 OR 2026',                                       "Asia Pacific"),
    ('商业地产 内装 2025 OR 2026',                                         "Asia Pacific"),

    # Arabic pipeline signals — Gulf
    ('فندق افتتاح OR تطوير 2025 OR 2026',                                "Middle East"),
    ('مشروع تشطيبات داخلية 2025 OR 2026',                                "Middle East"),
    ('تطوير عقاري دبي OR الرياض 2026',                                   "Middle East"),
    ('مشاريع سياحية السعودية 2025 OR 2026',                               "Middle East"),
]

# ─── Fetch engine ──────────────────────────────────────────────────────────────

# Keywords that confirm this is a pipeline/development signal (not a retrospective)
PIPELINE_SIGNAL_RE = re.compile(
    r'\bopen(?:ing|s|ed)?\b|\bnew\b|\bdevelop(?:ment|ing|ed)?\b|\bpipeline\b'
    r'|\bplanned?\b|\bunder\s+construction\b|\bbreak(?:ing)?\s+ground\b'
    r'|\blaunch(?:es|ed|ing)?\b|\bcompletion\b|\bdeliver(?:y|ed|ing)?\b'
    r'|\bannounced?\b|\bexpansion\b|\binvestment\b|\bproject\b|\bconstruct(?:ion|ing|ed)?\b'
    r'|\bphase\b|\brender(?:ing|s)?\b|\bdesigned?\b|\bplans?\b|\bproposal\b'
    r'|\bgreenlighted?\b|\bapproved?\b|\bawarded?\b|\bselected?\b|\bsigned?\b'
    r'|\bsigned?\s+contract\b|\bGFA\b|\bsqm\b|\bsq\s*m\b|\bmillion\b|\bbillion\b',
    re.IGNORECASE
)

# Keywords that would indicate this is NOT a pipeline signal (news/opinion pieces)
EXCLUDE_RE = re.compile(
    r'\bopinion\b|\bcommentary\b|\breview\b|\btop\s+\d+\b|\bbest\s+hotels?\b'
    r'|\bguide\s+to\b|\bwhere\s+to\s+stay\b|\btravel\s+guide\b|\brecommend\b',
    re.IGNORECASE
)

def fetch_pipeline():
    results = []
    seen_titles = set()
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE)).strftime("%Y-%m-%d")
    total_q = len(PIPELINE_QUERIES)
    log.info(f"📡 Fetching pipeline signals ({total_q} queries)…")

    for i, (query, hint_continent) in enumerate(PIPELINE_QUERIES, 1):
        if i % 20 == 0:
            log.info(f"   [{i}/{total_q}] {len(results)} signals so far…")

        url = (
            "https://news.google.com/rss/search"
            f"?q={urllib.parse.quote(query)}&hl=en&gl=GB&ceid=GB:en"
        )
        raw = get_url(url)
        if not raw:
            time.sleep(0.3)
            continue

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
            pub   = parse_date(txt("pubDate"))
            source_name = txt("source")

            if not title:
                continue

            # Strip source suffix from title (Google News appends " - Source Name")
            clean_title = re.sub(r'\s*[-—]\s*[^-—]+$', '', title).strip() if ' - ' in title or ' — ' in title else title

            # Dedup by clean title
            slug = re.sub(r'\W+', '', clean_title.lower())[:80]
            if slug in seen_titles:
                continue

            # Age gate
            if pub and pub < cutoff_date:
                continue

            # Must have a pipeline signal word
            combined = clean_title + " " + desc
            if not PIPELINE_SIGNAL_RE.search(combined):
                continue

            # Filter out travel guide / "best of" articles
            if EXCLUDE_RE.search(clean_title):
                continue

            seen_titles.add(slug)

            country_code = guess_country(clean_title, desc)
            continent    = continent_from_country(country_code) if country_code else (hint_continent or "Other")
            sector       = classify_sector(clean_title, desc)

            results.append({
                "id":           make_id(clean_title, link),
                "title":        clean_title,
                "source":       source_name or "News",
                "source_url":   link,
                "published":    pub,
                "accessed_at":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "country_code": country_code,
                "country_name": COUNTRY_NAMES.get(country_code, ""),
                "country_flag": COUNTRY_FLAGS.get(country_code, "🌍"),
                "continent":    continent,
                "sector":       sector,
                "summary":      desc[:300],
            })

        time.sleep(0.35)

    log.info(f"✅ Total pipeline signals: {len(results)}")
    return results


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    t0 = datetime.now(timezone.utc)
    projects = fetch_pipeline()

    # Sort: newest first
    projects.sort(key=lambda x: x.get("published",""), reverse=True)

    # Aggregation summaries
    by_continent: dict[str, int] = {}
    by_sector:    dict[str, int] = {}
    for p in projects:
        by_continent[p["continent"]] = by_continent.get(p["continent"], 0) + 1
        by_sector[p["sector"]]       = by_sector.get(p["sector"], 0) + 1

    # Sort summaries descending
    by_continent = dict(sorted(by_continent.items(), key=lambda x: -x[1]))
    by_sector    = dict(sorted(by_sector.items(),    key=lambda x: -x[1]))

    elapsed = (datetime.now(timezone.utc) - t0).seconds
    data = {
        "last_updated":  t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total":         len(projects),
        "elapsed_sec":   elapsed,
        "by_continent":  by_continent,
        "by_sector":     by_sector,
        "projects":      projects,
    }

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"💾 Saved {len(projects)} signals to {OUT.name} ({elapsed}s)")
    log.info(f"   Breakdown by continent: {by_continent}")
    log.info(f"   Breakdown by sector: {by_sector}")


if __name__ == "__main__":
    main()
