# Sources — every dataset and benchmark, what it feeds, and its status

Status legend: **ARCHIVED** (file in `data/raw/`), **TO PULL** (I could not reach the site from the build sandbox — pull and archive before the trial), **VERIFY** (my recollection of the URL / schema / figure; confirm live).

| # | Source | URL (VERIFY) | Feeds | Status |
|---|---|---|---|---|
| S1 | FMCSA QCMobile API — carrier, basics, authority, cargo, operation-classification endpoints | https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcApi (register for free webKey) | `rater/enrich.py` runtime enrichment | TO PULL — get webKey, save one raw response per endpoint into `data/raw/qcmobile_samples/` and fix field names in `_parse_carrier()` |
| S2 | FMCSA SAFER Company Snapshot | https://safer.fmcsa.dot.gov/CompanySnapshot.aspx | Manual cross-check of S1 fields | TO PULL (screenshots of 3 carriers) |
| S3 | FMCSA Motor Carrier Census file (monthly bulk) | https://ai.fmcsa.dot.gov/SMS/Tools/Downloads.aspx and/or https://data.transportation.gov (search "Motor Carrier Census") | Denominator; `analysis/build_frequency_tables.py`; sample set | TO PULL → `data/raw/census.csv` |
| S4 | MCMIS Crash file (public) | data.transportation.gov "Motor Carrier Crash" / FMCSA Data Dissemination | Numerator; crash rate by segment/state; severity flags | TO PULL → `data/raw/crash_YYYY.csv` (3 years) |
| S5 | MCMIS Inspection file | same as S4 ("Inspections") | Segment OOS averages (`segment_averages` in rates.yaml) | TO PULL (optional if time short — QCMobile gives per-carrier OOS + national avg) |
| S6 | FMCSA Licensing & Insurance (L&I) | https://li-public.fmcsa.dot.gov/LIVIEW/pkg_carrquery.prc_carrlist | Authority grant date, insurance filings, cancellation history (rule D23) | TO PULL — scrape for sample set only; if too slow, note that D23 uses the submission's self-declared cancellation field |
| S7 | FMCSA SMS methodology (post-2025 reform) | https://csa.fmcsa.dot.gov/ | Which BASICs are public; percentile thresholds used in `basic_percentile` | VERIFY |
| S8 | NHTSA vPIC VIN decoder (batch) | https://vpic.nhtsa.dot.gov/api/ | `rater/enrich.decode_vins`; vehicle age; trailer/pickup detection (rule D30) | TO PULL — test batch endpoint, archive one response |
| S9 | FMCSA Large Truck and Bus Crash Facts (annual) | https://www.fmcsa.dot.gov/safety/data-and-statistics/large-truck-and-bus-crash-facts | Severity mix (PDO / injury / fatal shares); crash-rate sanity anchor | TO PULL (PDF) — my anchors: fatal ≈1–1.5% of police-reported large-truck crashes, injury ≈ 20–25% |
| S10 | NHTSA FARS | https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars | Fatality mix by state (venue tier) | Optional |
| S11 | ATRI — *An Analysis of the Operational Costs of Trucking* (annual) | https://truckingresearch.org | Insurance $/mile (≈ $0.09–0.10/mile industry; far higher per unit for 1–5 unit fleets); market price anchor | TO PULL (PDF) |
| S12 | ATRI — *Understanding the Impact of Nuclear Verdicts on the Trucking Industry* (2020) and *Impact of Small Cases* (2021) | truckingresearch.org | Severity tail, verdict trend (`severity_trend_annual`), venue tier | TO PULL |
| S13 | III / AM Best / NAIC commercial auto results | https://www.iii.org | Industry combined ratio >100% most years since ~2011 — margin story | TO PULL (one chart) |
| S14 | SERFF rate filings — Progressive Commercial (Progressive County Mutual / Progressive Casualty), Sentry, Great West, Canal, Northland | State DOI SERFF portals (e.g. Texas, Florida, Illinois offer public SERFF access) | Relativity structure (radius, GVW, new venture, driver factors) and base-rate benchmark | TO PULL — highest-value benchmark; archive PDFs |
| S15 | 49 CFR 387.9 minimum financial responsibility | https://www.ecfr.gov | $750k general freight, $1m oil, $5m hazmat; base limit choice | VERIFY (stable) |
| S16 | Observed market quotes (broker sites, OOIDA, Progressive quote pages) | various | 5–10 price points for `minimum_premium_per_unit` and validation | TO PULL — record date, carrier profile, quoted premium |

Numbers currently in `config/rates.yaml` tagged [S] or [B] are my anchors from memory; every one is a candidate for replacement by S3+S4 output. The [E] tag is reserved for values produced by `analysis/build_frequency_tables.py`.
