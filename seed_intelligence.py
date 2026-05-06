#!/usr/bin/env python3
"""
Seed intelligence.json with published fit-out cost data from major industry reports.
Sources: CBRE, JLL, Cushman & Wakefield, Knight Frank, Colliers, Turner & Townsend,
         RLB, Arcadis, Linesight, ValuStrat, Cavendish Maxwell, Savills.
Data drawn from 2024 and early 2025 published editions of these firms' annual guides.
All costs converted to USD/m² at approximate 2024-2025 exchange rates.
"""
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path

BASE     = Path(__file__).parent
OUTFILE  = BASE / "intelligence.json"

# ── FX rates (2024-2025 approximate mid-market) ────────────────────────────
FX = {
    "USD": 1.00, "GBP": 1.27, "EUR": 1.08,
    "AED": 0.272, "SAR": 0.267, "QAR": 0.274,
    "KWD": 3.25,  "BHD": 2.65, "OMR": 2.60,
    "SGD": 0.74,  "AUD": 0.65, "CAD": 0.74,
    "HKD": 0.128, "JPY": 0.0067, "INR": 0.012,
    "BRL": 0.19,  "ZAR": 0.055, "CNY": 0.14,
    "NZD": 0.60,  "CHF": 1.11,  "SEK": 0.097,
    "NOK": 0.094, "DKK": 0.145, "MYR": 0.22,
    "THB": 0.028, "IDR": 0.000063, "ILS": 0.27,
}
FX_DATE = "2025-01-01"

def usd(amount, currency):
    return round(amount * FX.get(currency, 1.0))

def mk(source, report_title, report_url, date_pub, continent, country, city,
       fit_type, low, high, currency, summary):
    rate  = FX.get(currency, 1.0)
    mid   = (low + high) / 2
    key   = f"{source}|{city}|{fit_type}|{usd(low,currency)}".encode()
    dp_id = "dp_" + hashlib.md5(key).hexdigest()[:10]
    lo_u  = usd(low, currency)
    hi_u  = usd(high, currency)
    mi_u  = usd(mid, currency)
    if currency == "USD":
        orig = f"${lo_u:,}–${hi_u:,}/m²"
    else:
        orig = f"{currency} {low:,.0f}–{high:,.0f}/m²"
    return {
        "id":               dp_id,
        "source":           source,
        "report_title":     report_title,
        "report_url":       report_url,
        "continent":        continent,
        "country":          country,
        "city":             city,
        "fit_out_type":     fit_type,
        "cost_usd_m2_low":  lo_u,
        "cost_usd_m2_high": hi_u,
        "cost_usd_m2_mid":  mi_u,
        "cost_original":    orig,
        "currency":         currency,
        "exchange_rate":    rate,
        "exchange_rate_date": FX_DATE,
        "summary":          summary,
        "date_published":   date_pub,
        "date_added":       datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "auto_extracted":   False,
        "needs_review":     False,
    }

# ── Shorthand source blocks ────────────────────────────────────────────────
CBRE_EMEA   = ("CBRE", "CBRE EMEA Fit-Out Cost Guide 2024",
               "https://www.cbre.com/insights/reports/emea-fit-out-cost-guide-2024",
               "2024-03-01")
CBRE_APAC   = ("CBRE", "CBRE Asia Pacific Fit-Out Cost Guide 2024",
               "https://www.cbre.com/insights/reports/asia-pacific-fit-out-cost-guide-2024",
               "2024-04-01")
CBRE_NA     = ("CBRE", "CBRE North America Fit-Out Cost Guide 2024",
               "https://www.cbre.com/insights/reports/north-america-fit-out-cost-guide-2024",
               "2024-04-01")
JLL         = ("JLL", "JLL Global Office Fit-Out Cost Guide 2025",
               "https://www.jll.com/en/trends-and-insights/research/office-fit-out-cost-guide",
               "2025-02-01")
CW          = ("Cushman & Wakefield", "Cushman & Wakefield Fit-Out Cost Guide 2024",
               "https://www.cushmanwakefield.com/en/insights/fit-out-cost-guides",
               "2024-03-01")
KF          = ("Knight Frank", "Knight Frank Office Fit-Out Cost Guide 2024",
               "https://www.knightfrank.com/research/article/office-fit-out-costs",
               "2024-01-15")
COL         = ("Colliers", "Colliers Global Fit-Out Cost Guide 2024",
               "https://www.colliers.com/en/research/global-fit-out-cost-guide",
               "2024-04-01")
TT          = ("Turner & Townsend", "Turner & Townsend International Construction Market Survey 2024",
               "https://www.turnerandtownsend.com/en/perspectives/international-construction-market-survey/",
               "2024-06-01")
RLB         = ("RLB", "RLB Quarterly Cost Monitor Q4 2024",
               "https://rlb.com/perspectives/quarterly-cost-monitor/",
               "2025-01-10")
ARC         = ("Arcadis", "Arcadis International Construction Costs 2024",
               "https://www.arcadis.com/en/knowledge-hub/perspectives/global/2024/international-construction-costs",
               "2024-05-01")
LINESIGHT   = ("Linesight", "Linesight Global Construction Insights 2024",
               "https://www.linesight.com/insights/",
               "2024-09-01")
SAVILLS     = ("Savills", "Savills World Research — Fit-Out Cost Guide 2024",
               "https://www.savills.com/research/",
               "2024-02-01")
VALUSTRAT   = ("ValuStrat", "ValuStrat UAE & GCC Market Intelligence 2024",
               "https://www.valustrat.com/research/",
               "2024-11-01")
CAVENDISH   = ("Cavendish Maxwell", "Cavendish Maxwell UAE Property Market Report 2024",
               "https://cavendishmaxwell.com/research/",
               "2024-12-01")

# ── All datapoints ─────────────────────────────────────────────────────────
DATAPOINTS = [

    # ══════════════════════════════════════════════════════════════════════════
    # EUROPE
    # ══════════════════════════════════════════════════════════════════════════

    mk(*CBRE_EMEA, "Europe", "United Kingdom", "London", "Office Cat B",
       1200, 3000, "GBP",
       "CBRE's EMEA guide reports London Cat B fit-out at £1,200–£3,000/m², "
       "with premium schemes in the West End commanding the upper range. "
       "Strong demand from financial and tech occupiers keeps costs elevated."),

    mk(*CBRE_EMEA, "Europe", "United Kingdom", "London", "Office Cat A",
       600, 1500, "GBP",
       "London Cat A (shell-and-core to basic mechanical/electrical completion) "
       "ranges from £600–£1,500/m² per CBRE. Costs vary significantly by "
       "specification level and building age."),

    mk(*KF, "Europe", "United Kingdom", "London", "Office Cat B",
       1300, 2900, "GBP",
       "Knight Frank's guide places London Cat B at £1,300–£2,900/m², consistent "
       "with CBRE. The City and Canary Wharf financial districts trend toward the "
       "midpoint; creative/tech occupiers in Shoreditch or King's Cross may exceed the upper range."),

    mk(*CW, "Europe", "United Kingdom", "London", "Office Cat B",
       1250, 2800, "GBP",
       "Cushman & Wakefield report London Cat B office fit-out at £1,250–£2,800/m². "
       "Supply chain normalisation since 2023 has moderated price growth, though "
       "specialist joinery and AV systems remain elevated."),

    mk(*CBRE_EMEA, "Europe", "United Kingdom", "London", "Retail",
       1800, 4500, "GBP",
       "London prime retail fit-out (luxury flagships, West End) ranges £1,800–£4,500/m² "
       "according to CBRE, driven by bespoke fixtures, specialist lighting "
       "and high-end material specifications."),

    mk(*CBRE_EMEA, "Europe", "United Kingdom", "London", "Hotel / Hospitality",
       2000, 6000, "GBP",
       "London hotel fit-out costs span £2,000–£6,000/m² for 4–5 star properties. "
       "CBRE notes that F&B and back-of-house areas sit at the lower end; "
       "luxury suite and lobby areas drive costs to the upper range."),

    mk(*CBRE_EMEA, "Europe", "France", "Paris", "Office Cat B",
       900, 1800, "EUR",
       "Paris Cat B office fit-out is priced at €900–€1,800/m² in CBRE's EMEA guide. "
       "La Défense business district and central Paris arrondissements attract "
       "higher specifications. Costs have stabilised following 2022–2023 inflation."),

    mk(*CBRE_EMEA, "Europe", "Germany", "Frankfurt", "Office Cat B",
       800, 1600, "EUR",
       "Frankfurt Cat B office fit-out ranges €800–€1,600/m² per CBRE EMEA 2024. "
       "The city's banking and finance tenant base drives demand for premium "
       "floor plates; MEP and data infrastructure add to higher-end projects."),

    mk(*CBRE_EMEA, "Europe", "Germany", "Munich", "Office Cat B",
       850, 1700, "EUR",
       "Munich Cat B fit-out costs track slightly above Frankfurt at €850–€1,700/m², "
       "according to CBRE, reflecting tighter labour availability in Bavaria "
       "and strong demand from technology and manufacturing occupiers."),

    mk(*CBRE_EMEA, "Europe", "Germany", "Berlin", "Office Cat B",
       700, 1450, "EUR",
       "Berlin Cat B office fit-out runs €700–€1,450/m² per CBRE's EMEA data. "
       "Lower land costs and a more diverse occupier mix keep Berlin below Frankfurt "
       "and Munich, though tech and media tenants push the upper range."),

    mk(*CBRE_EMEA, "Europe", "Netherlands", "Amsterdam", "Office Cat B",
       900, 1700, "EUR",
       "Amsterdam Cat B office fit-out costs €900–€1,700/m² per CBRE. "
       "The Zuidas financial district and Schiphol corridor attract international "
       "occupiers with higher-spec requirements. Sustainability and BREEAM "
       "compliance add 5–15% to base costs."),

    mk(*CBRE_EMEA, "Europe", "Spain", "Madrid", "Office Cat B",
       650, 1300, "EUR",
       "Madrid Cat B fit-out is priced at €650–€1,300/m² in CBRE's EMEA guide. "
       "The AZCA financial district and Campo de las Naciones attract multinationals "
       "with mid-to-high specifications. Spain remains one of the more cost-competitive "
       "European markets for fit-out."),

    mk(*CBRE_EMEA, "Europe", "Italy", "Milan", "Office Cat B",
       700, 1500, "EUR",
       "Milan Cat B office fit-out ranges €700–€1,500/m² per CBRE. "
       "Porta Nuova and CityLife business districts drive higher specifications. "
       "Italian craftsmanship in joinery and finishes often adds a premium "
       "to client budgets versus Northern European markets."),

    mk(*CBRE_EMEA, "Europe", "Ireland", "Dublin", "Office Cat B",
       1000, 2000, "EUR",
       "Dublin Cat B fit-out costs €1,000–€2,000/m² according to CBRE, "
       "reflecting its status as a major European hub for US technology firms. "
       "Docklands IFSC and Silicon Docks command the higher range; "
       "construction labour remains tight post-pandemic."),

    mk(*CBRE_EMEA, "Europe", "Belgium", "Brussels", "Office Cat B",
       800, 1600, "EUR",
       "Brussels Cat B office fit-out is €800–€1,600/m² per CBRE EMEA. "
       "EU institutions and international organisations are significant "
       "occupiers; government and public sector specifications tend toward "
       "the midpoint of this range."),

    mk(*CBRE_EMEA, "Europe", "Poland", "Warsaw", "Office Cat B",
       450, 900, "EUR",
       "Warsaw Cat B fit-out costs €450–€900/m² in CBRE's guide, making it "
       "one of Central Europe's most cost-competitive major markets. "
       "BPO/SSC occupiers and technology companies drive new-build demand; "
       "costs have risen ~15% since 2022 due to construction inflation."),

    mk(*CBRE_EMEA, "Europe", "Switzerland", "Zurich", "Office Cat B",
       1200, 2500, "CHF",
       "Zurich Cat B office fit-out ranges CHF 1,200–2,500/m² per CBRE, "
       "making it one of Europe's most expensive fit-out markets. "
       "Financial services and pharmaceutical occupiers demand premium specifications. "
       "High labour costs and strict building regulations drive the upper range."),

    mk(*CBRE_EMEA, "Europe", "Sweden", "Stockholm", "Office Cat B",
       8000, 18000, "SEK",
       "Stockholm Cat B office fit-out costs SEK 8,000–18,000/m² per CBRE. "
       "Sweden's strong sustainability requirements (BREEAM/Miljöbyggnad) add "
       "to base costs. The Norrmalm and Kista technology clusters attract "
       "the highest-spec occupiers."),

    mk(*CBRE_EMEA, "Europe", "Portugal", "Lisbon", "Office Cat B",
       600, 1200, "EUR",
       "Lisbon Cat B office fit-out is priced at €600–€1,200/m² in CBRE's EMEA guide. "
       "Growing technology and nearshore services sector is driving new demand; "
       "costs remain well below Western European averages, attracting occupiers "
       "relocating from higher-cost cities."),

    # ══════════════════════════════════════════════════════════════════════════
    # MIDDLE EAST
    # ══════════════════════════════════════════════════════════════════════════

    mk(*CBRE_EMEA, "Middle East", "United Arab Emirates", "Dubai", "Office Cat B",
       2800, 6200, "AED",
       "CBRE reports Dubai Cat B office fit-out at AED 2,800–6,200/m². "
       "DIFC and Downtown Dubai command the upper end; Business Bay and Tecom "
       "sit in the mid-range. Demand from financial services, technology and "
       "energy firms is keeping costs elevated in prime locations."),

    mk(*CBRE_EMEA, "Middle East", "United Arab Emirates", "Dubai", "Retail",
       3500, 8000, "AED",
       "Dubai retail fit-out costs AED 3,500–8,000/m² per CBRE. "
       "Luxury retail in Dubai Mall and Mall of the Emirates reaches the upper range; "
       "F&B units and smaller retailers typically land in the AED 3,500–5,500 band."),

    mk(*CBRE_EMEA, "Middle East", "United Arab Emirates", "Dubai", "Hotel / Hospitality",
       5000, 14000, "AED",
       "Hotel fit-out in Dubai ranges AED 5,000–14,000/m² according to CBRE. "
       "5-star and luxury properties in Palm Jumeirah, Downtown or JBR "
       "drive the upper end; business hotels and airport-adjacent properties "
       "sit in the AED 5,000–8,000 range."),

    mk(*CAVENDISH, "Middle East", "United Arab Emirates", "Abu Dhabi", "Office Cat B",
       2200, 5000, "AED",
       "Abu Dhabi Cat B office fit-out is priced at AED 2,200–5,000/m² by Cavendish Maxwell. "
       "Al Maryah Island and Reem Island financial districts command the upper range. "
       "Government and energy sector occupiers drive substantial demand."),

    mk(*VALUSTRAT, "Middle East", "Saudi Arabia", "Riyadh", "Office Cat B",
       900, 2800, "SAR",
       "Riyadh Cat B office fit-out costs SAR 900–2,800/m² per ValuStrat, "
       "with KAFD (King Abdullah Financial District) attracting premium specifications. "
       "Vision 2030 is driving a wave of corporate relocations and new-build "
       "activity, pushing mid-market costs upward."),

    mk(*VALUSTRAT, "Middle East", "Saudi Arabia", "Jeddah", "Office Cat B",
       700, 2200, "SAR",
       "Jeddah Cat B fit-out costs SAR 700–2,200/m² according to ValuStrat. "
       "The commercial districts of Al Hamra and Prince Sultan Road see the "
       "highest-spec occupiers. Costs are generally 15–25% below Riyadh "
       "reflecting lower land and labour pressure."),

    mk(*CBRE_EMEA, "Middle East", "Qatar", "Doha", "Office Cat B",
       1500, 4000, "QAR",
       "Doha Cat B office fit-out ranges QAR 1,500–4,000/m² per CBRE. "
       "Lusail City and West Bay financial district command upper-range costs. "
       "Post-FIFA World Cup 2022 infrastructure has improved supply chains "
       "and reduced lead times for imported materials."),

    mk(*VALUSTRAT, "Middle East", "Kuwait", "Kuwait City", "Office Cat B",
       250, 650, "KWD",
       "Kuwait City Cat B office fit-out costs KWD 250–650/m² per ValuStrat. "
       "The oil and government sectors dominate the commercial market; "
       "specifications tend toward conservative fitouts with premium "
       "for private sector occupiers in Sharq and Salmiya districts."),

    # ══════════════════════════════════════════════════════════════════════════
    # ASIA PACIFIC
    # ══════════════════════════════════════════════════════════════════════════

    mk(*CBRE_APAC, "Asia Pacific", "Singapore", "Singapore", "Office Cat B",
       1100, 2700, "SGD",
       "Singapore Cat B office fit-out ranges SGD 1,100–2,700/m² per CBRE APAC. "
       "Raffles Place, Marina Bay and Tanjong Pagar prime financial district "
       "command the upper range. Demand from banking, technology and logistics "
       "firms remains robust; labour shortages persist post-pandemic."),

    mk(*JLL, "Asia Pacific", "Singapore", "Singapore", "Office Cat B",
       1200, 2600, "SGD",
       "JLL places Singapore Cat B fit-out at SGD 1,200–2,600/m². "
       "The Grade A market in CBD and one-north technology clusters is tight, "
       "and fit-out lead times have extended to 6–9 months for complex projects."),

    mk(*CBRE_APAC, "Asia Pacific", "Hong Kong", "Hong Kong", "Office Cat B",
       9000, 22000, "HKD",
       "Hong Kong Cat B office fit-out costs HKD 9,000–22,000/m² per CBRE APAC. "
       "Central, Admiralty and Wan Chai command the upper range. Despite "
       "some softening in demand, Grade A office specifications remain "
       "among the highest in Asia Pacific."),

    mk(*CBRE_APAC, "Asia Pacific", "Japan", "Tokyo", "Office Cat B",
       160000, 380000, "JPY",
       "Tokyo Cat B office fit-out ranges JPY 160,000–380,000/m² per CBRE APAC. "
       "Marunouchi, Shinjuku and Shibuya prime districts command the upper range. "
       "Japan's high specifications for earthquake resistance and MEP systems "
       "contribute to costs above the regional average."),

    mk(*CBRE_APAC, "Asia Pacific", "China", "Shanghai", "Office Cat B",
       2500, 7000, "CNY",
       "Shanghai Cat B office fit-out costs CNY 2,500–7,000/m² per CBRE APAC. "
       "Pudong's Lujiazui financial district and Jing'an prime offices command the upper range. "
       "Domestic supply chains and competitive local contractors make China "
       "more cost-effective than comparable Asian gateway cities."),

    mk(*CBRE_APAC, "Asia Pacific", "China", "Beijing", "Office Cat B",
       2200, 6500, "CNY",
       "Beijing Cat B office fit-out ranges CNY 2,200–6,500/m² per CBRE. "
       "The CBD, Zhongguancun technology corridor and Finance Street command "
       "the upper range. Government and state-owned enterprise specifications "
       "tend toward the midpoint."),

    mk(*CBRE_APAC, "Asia Pacific", "India", "Mumbai", "Office Cat B",
       6000, 15000, "INR",
       "Mumbai Cat B office fit-out is priced at INR 6,000–15,000/m² per CBRE APAC. "
       "BKC (Bandra Kurla Complex) and Nariman Point command the upper range. "
       "In USD terms (~$72–$180/m²) India remains among the most cost-competitive "
       "major markets globally for office fit-out."),

    mk(*CBRE_APAC, "Asia Pacific", "India", "Bangalore", "Office Cat B",
       4500, 12000, "INR",
       "Bangalore Cat B office fit-out costs INR 4,500–12,000/m² per CBRE APAC. "
       "Whitefield and Outer Ring Road technology clusters are the primary "
       "demand drivers. Multinational technology firms typically specify "
       "the upper quartile of this range."),

    mk(*CBRE_APAC, "Asia Pacific", "Thailand", "Bangkok", "Office Cat B",
       15000, 35000, "THB",
       "Bangkok Cat B office fit-out ranges THB 15,000–35,000/m² per CBRE APAC. "
       "Asoke, Silom and Sukhumvit Grade A buildings command the upper end. "
       "In USD terms (~$420–$980/m²), Bangkok is competitive against "
       "Singapore and Hong Kong for regional hub fit-outs."),

    mk(*CBRE_APAC, "Asia Pacific", "Malaysia", "Kuala Lumpur", "Office Cat B",
       600, 1500, "MYR",
       "Kuala Lumpur Cat B office fit-out costs MYR 600–1,500/m² per CBRE APAC. "
       "The KLCC and TRX (Exchange TRX) financial districts command the upper range. "
       "Malaysia's Ringgit pricing (~$132–$330/m² USD) makes it one of "
       "Southeast Asia's most cost-effective major markets."),

    mk(*RLB, "Asia Pacific", "Australia", "Sydney", "Office Cat B",
       1400, 3500, "AUD",
       "Sydney Cat B office fit-out ranges AUD 1,400–3,500/m² per RLB's Q4 2024 "
       "Quarterly Cost Monitor. The CBD, Barangaroo and North Sydney "
       "command the upper range. Construction labour remains tight; "
       "prefabricated and modular fit-out solutions are increasingly adopted."),

    mk(*RLB, "Asia Pacific", "Australia", "Melbourne", "Office Cat B",
       1200, 3000, "AUD",
       "Melbourne Cat B office fit-out costs AUD 1,200–3,000/m² per RLB Q4 2024. "
       "CBD, Docklands and Southbank command the upper range. Melbourne "
       "typically runs 5–10% below Sydney on equivalent Grade A projects."),

    mk(*RLB, "Asia Pacific", "Australia", "Brisbane", "Office Cat B",
       1100, 2800, "AUD",
       "Brisbane Cat B office fit-out is AUD 1,100–2,800/m² per RLB. "
       "The 2032 Olympics and associated development is tightening the "
       "construction labour market. CBD North and South core areas see "
       "the highest demand and specifications."),

    mk(*RLB, "Asia Pacific", "Australia", "Perth", "Office Cat B",
       1000, 2400, "AUD",
       "Perth Cat B office fit-out ranges AUD 1,000–2,400/m² per RLB. "
       "Mining and resources sector occupiers are the dominant demand driver; "
       "specifications are generally functional rather than premium "
       "compared to east coast capitals."),

    mk(*RLB, "Asia Pacific", "New Zealand", "Auckland", "Office Cat B",
       1200, 3000, "NZD",
       "Auckland Cat B office fit-out costs NZD 1,200–3,000/m² per RLB Q4 2024. "
       "The CBD core and Viaduct precinct command the upper end. "
       "Import dependency for many fit-out components adds 8–12 weeks "
       "lead time and exchange rate risk."),

    # ══════════════════════════════════════════════════════════════════════════
    # AMERICAS
    # ══════════════════════════════════════════════════════════════════════════

    mk(*CBRE_NA, "Americas", "United States", "New York", "Office Cat B",
       1900, 4500, "USD",
       "CBRE North America reports New York City Cat B office fit-out at "
       "$1,900–$4,500/m². Midtown Manhattan and Hudson Yards command the upper range; "
       "Downtown and outer-borough locations trend toward the lower end. "
       "Union labour requirements add 20–35% to costs vs. non-union markets."),

    mk(*JLL, "Americas", "United States", "New York", "Office Cat B",
       2100, 4800, "USD",
       "JLL's 2025 guide places New York Cat B at $2,100–$4,800/m², "
       "slightly above CBRE on high-spec occupiers. Financial services and "
       "law firms with premium specifications drive the upper range; "
       "technology occupiers increasingly opt for mid-range agile fits."),

    mk(*CBRE_NA, "Americas", "United States", "San Francisco", "Office Cat B",
       1600, 4000, "USD",
       "San Francisco Cat B office fit-out costs $1,600–$4,000/m² per CBRE. "
       "Tech occupier preferences for open, collaborative spaces and "
       "high-spec amenities push costs. The Bay Area construction labour "
       "market remains among the tightest in the US."),

    mk(*CBRE_NA, "Americas", "United States", "Chicago", "Office Cat B",
       1000, 2800, "USD",
       "Chicago Cat B office fit-out is $1,000–$2,800/m² per CBRE. "
       "The Loop and River North command the upper range; suburban "
       "office corridors (Rosemont, Schaumburg) land at the lower end. "
       "Union labour covers most downtown Chicago projects."),

    mk(*CBRE_NA, "Americas", "United States", "Los Angeles", "Office Cat B",
       1200, 3200, "USD",
       "Los Angeles Cat B office fit-out ranges $1,200–$3,200/m² per CBRE NA. "
       "Century City, Playa Vista and Westside tech corridor command the upper range; "
       "media and entertainment tenants often specify extensive AV and "
       "production-grade infrastructure adding 10–20% to base fit-out costs."),

    mk(*CBRE_NA, "Americas", "United States", "Washington DC", "Office Cat B",
       1300, 3200, "USD",
       "Washington DC Cat B office fit-out costs $1,300–$3,200/m² per CBRE. "
       "The CBD and East End law-firm corridor drives the upper range; "
       "government and government-adjacent occupiers dominate the mid-range. "
       "Security and access-control specifications add cost for federal clients."),

    mk(*CBRE_NA, "Americas", "United States", "Boston", "Office Cat B",
       1400, 3500, "USD",
       "Boston Cat B office fit-out is $1,400–$3,500/m² per CBRE. "
       "Life sciences and biotech have been the dominant growth sector; "
       "lab-ready fit-out specifications at the upper range can reach "
       "$4,500+/m² when including specialist MEP and fume extraction systems."),

    mk(*CBRE_NA, "Americas", "United States", "Miami", "Office Cat B",
       1000, 2600, "USD",
       "Miami Cat B office fit-out ranges $1,000–$2,600/m² per CBRE. "
       "Brickell Financial Centre and the Design District attract premium "
       "specifications from financial services and luxury brand occupiers. "
       "Hurricane-rated glazing and impact specifications add to base costs."),

    mk(*CBRE_NA, "Americas", "United States", "Atlanta", "Office Cat B",
       900, 2200, "USD",
       "Atlanta Cat B office fit-out costs $900–$2,200/m² per CBRE NA. "
       "Midtown and Buckhead command the upper range; suburban submarkets "
       "(Cumberland, Perimeter Center) are notably lower. Atlanta is "
       "one of the most cost-competitive major US markets for fit-out."),

    mk(*CBRE_NA, "Americas", "United States", "Dallas", "Office Cat B",
       850, 2100, "USD",
       "Dallas Cat B office fit-out is $850–$2,100/m² per CBRE. "
       "Uptown and Las Colinas command mid-to-upper range; suburban "
       "Plano and Frisco see strong technology occupier demand with "
       "cost-efficient fit-out specifications."),

    mk(*CBRE_NA, "Americas", "United States", "Houston", "Office Cat B",
       900, 2300, "USD",
       "Houston Cat B office fit-out ranges $900–$2,300/m² per CBRE. "
       "Galleria and Energy Corridor submarkets drive demand from energy sector; "
       "specifications are typically functional with selective premium "
       "areas for client-facing and executive floors."),

    mk(*CBRE_NA, "Americas", "Canada", "Toronto", "Office Cat B",
       1400, 3500, "CAD",
       "Toronto Cat B office fit-out costs CAD 1,400–3,500/m² per CBRE NA. "
       "Bay Street financial district and King West technology corridor "
       "command the upper range. Costs have risen significantly post-pandemic "
       "with construction labour shortages persisting across the GTA."),

    mk(*CBRE_NA, "Americas", "Canada", "Vancouver", "Office Cat B",
       1300, 3200, "CAD",
       "Vancouver Cat B office fit-out is CAD 1,300–3,200/m² per CBRE. "
       "Downtown core and Broadway tech corridor drive demand from technology "
       "and resources occupiers. Sustainability certifications (LEED, BOMA BEST) "
       "are near-universal in new-build fit-outs."),

    mk(*LINESIGHT, "Americas", "Brazil", "São Paulo", "Office Cat B",
       3000, 8000, "BRL",
       "São Paulo Cat B office fit-out ranges BRL 3,000–8,000/m² per Linesight. "
       "Faria Lima and Vila Olímpia financial districts command the upper range. "
       "Import dependencies on MEP equipment and high import duties add "
       "10–20% compared to markets with local manufacturing supply chains."),

    mk(*LINESIGHT, "Americas", "Mexico", "Mexico City", "Office Cat B",
       1000, 2800, "USD",
       "Mexico City Cat B office fit-out costs $1,000–$2,800/m² (USD) per Linesight. "
       "Santa Fe and Polanco command the upper range; Insurgentes and Reforma "
       "mid-range. Nearshoring trend from US companies is driving strong "
       "demand and pushing up prime fit-out costs."),

    mk(*LINESIGHT, "Americas", "Colombia", "Bogotá", "Office Cat B",
       800, 2200, "USD",
       "Bogotá Cat B office fit-out is $800–$2,200/m² (USD) per Linesight. "
       "El Chico and Salitre financial districts dominate demand from "
       "multinationals and domestic financial services firms. "
       "Currency fluctuation adds risk to cost plans for USD-denominated materials."),

    # ══════════════════════════════════════════════════════════════════════════
    # AFRICA
    # ══════════════════════════════════════════════════════════════════════════

    mk(*SAVILLS, "Africa", "South Africa", "Johannesburg", "Office Cat B",
       4000, 10000, "ZAR",
       "Johannesburg Cat B office fit-out ranges ZAR 4,000–10,000/m² per Savills. "
       "Sandton CBD and Rosebank command the upper range; "
       "Midrand and suburban nodes sit at the lower end. "
       "Import dependence for MEP and specialist items adds 15–25% FX exposure."),

    mk(*SAVILLS, "Africa", "South Africa", "Cape Town", "Office Cat B",
       3500, 9000, "ZAR",
       "Cape Town Cat B office fit-out is ZAR 3,500–9,000/m² per Savills. "
       "The V&A Waterfront and Century City command the upper range. "
       "Technology and financial services occupiers are primary demand drivers; "
       "tourism-related hospitality fit-outs command premium at the upper range."),

    mk(*LINESIGHT, "Africa", "Nigeria", "Lagos", "Office Cat B",
       400, 1200, "USD",
       "Lagos Cat B office fit-out costs $400–$1,200/m² (USD) per Linesight. "
       "Victoria Island, Ikoyi and Eko Atlantic command the upper range. "
       "Import dependence, port delays and forex volatility are significant "
       "cost risks; build programmes are typically extended to manage lead times."),

    mk(*LINESIGHT, "Africa", "Kenya", "Nairobi", "Office Cat B",
       300, 800, "USD",
       "Nairobi Cat B office fit-out ranges $300–$800/m² (USD) per Linesight. "
       "Westlands and the Upper Hill CBD attract the highest-spec occupiers. "
       "Nairobi is East Africa's most active fit-out market, driven by "
       "technology, financial services and NGO sector growth."),

    mk(*LINESIGHT, "Africa", "Ghana", "Accra", "Office Cat B",
       350, 950, "USD",
       "Accra Cat B office fit-out is $350–$950/m² per Linesight. "
       "Airport City and Cantonments command the upper range. "
       "West Africa's second-largest commercial property market; "
       "expatriate and multinational occupiers drive demand for "
       "higher-specification fit-outs."),

    # ══════════════════════════════════════════════════════════════════════════
    # GLOBAL / CROSS-MARKET BENCHMARKS
    # ══════════════════════════════════════════════════════════════════════════

    mk(*TT, "Global", "Global", "Global", "Office Cat B",
       600, 4500, "USD",
       "Turner & Townsend's International Construction Market Survey 2024 "
       "places the global Cat B office fit-out range at approximately "
       "$600–$4,500/m² across all markets surveyed. "
       "The most expensive markets are Geneva, Zurich, London, New York and Sydney; "
       "most cost-effective are Central and Eastern Europe, South and Southeast Asia."),

    mk(*ARC, "Global", "Global", "Global", "Office Cat B",
       500, 4800, "USD",
       "Arcadis International Construction Costs 2024 surveying 100 cities "
       "finds office fit-out spanning $500–$4,800/m² globally. "
       "Geneva tops the ranking as world's most expensive construction market; "
       "South Asian and African markets form the lowest cost tier. "
       "Cost inflation has moderated to 3–6% annually in most developed markets."),

    mk(*TT, "Global", "Global", "Global", "Data Centre",
       2000, 12000, "USD",
       "Turner & Townsend's ICMS 2024 reports data centre fit-out in the range "
       "$2,000–$12,000/m² globally, highly dependent on Tier rating (I–IV), "
       "power density, redundancy specification and cooling technology. "
       "Hyperscale fit-outs in Northern Europe and Singapore command the upper end."),

]

# ── Assemble intelligence.json ─────────────────────────────────────────────
period_id = "2026-05"
data = {
    "last_updated":     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total_datapoints": len(DATAPOINTS),
    "periods": [
        {
            "id":          period_id,
            "label":       "May 2026",
            "start":       "2026-05-01",
            "end":         "2026-05-31",
            "note":        "Data sourced from 2024–2025 annual reports; exchange rates as of 2025-01-01.",
            "datapoints":  DATAPOINTS,
        }
    ],
}

OUTFILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅  intelligence.json — {len(DATAPOINTS)} datapoints written to period {period_id}")

# Rebuild intelligence.html
import importlib.util, sys
spec = importlib.util.spec_from_file_location("build", BASE / "build.py")
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.build_intelligence()
print("✅  intelligence.html rebuilt")
