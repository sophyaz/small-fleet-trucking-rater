# Claude Code prompts — the live-data work I could not do from the sandbox

Run these in order from the repo root. Each is self-contained; paste as one message.

---

## Prompt 1 — QCMobile field verification (30 min, do first)
```
Read rater/enrich.py. I have an FMCSA QCMobile webKey in env FMCSA_WEBKEY. For USDOT numbers 2231000, 3456789 and one you find that is a 1-5 power unit for-hire carrier, call these endpoints and save each raw JSON to data/raw/qcmobile_samples/<dot>_<endpoint>.json:
  /carriers/{dot}, /carriers/{dot}/basics, /carriers/{dot}/authority, /carriers/{dot}/cargo-carried, /carriers/{dot}/operation-classification, /carriers/{dot}/docket-numbers
Then diff the actual field names against what _parse_carrier() expects (allowedToOperate, totalPowerUnits, totalDrivers, driverOosRate, vehicleOosRate, driverInsp, vehicleInsp, crashTotal, fatalCrash, injCrash, towawayCrash, safetyRating, oosDate, mcs150Date, mcs150Mileage, addDate, hazmat/pc flags, basics percentile path, cargo and operation-classification description paths). Fix _parse_carrier so every feature in rater/features.py is populated from the live response. Also confirm what the API returns for an unknown DOT (404? empty content?) and fix the not-found branch in fetch_carrier. Then run: RATER_OFFLINE=0 python -m rater samples/submissions/00_established_clean_ia.json with usdot swapped to a real DOT, and show me the breakdown. Do not change any number in config/rates.yaml.
```

## Prompt 2 — Bulk files and frequency tables (2–3 h incl. download)
```
Find and download the current FMCSA Motor Carrier Census file and the last three years of public MCMIS crash files (start at https://ai.fmcsa.dot.gov/SMS/Tools/Downloads.aspx and data.transportation.gov; also check FMCSA "Data Dissemination Program"). Save them as data/raw/census.csv and data/raw/crash_<year>.csv and record the URLs, pull date and file sizes in docs/SOURCES.md rows S3 and S4. Print the header of each file. Then update the COLS mapping at the top of analysis/build_frequency_tables.py to match the real column names — in particular the columns for power units, drivers, add date, MCS-150 date, interstate/for-hire operation, hazmat and passenger flags, and the crash file's DOT number, report date, state, fatalities, injuries, tow-away. Run python -m analysis.build_frequency_tables --years 3 and show me data/derived/crash_rate_by_segment.csv and glm_relativities.csv. Then propose (do not apply) the replacement values for crash_rate_per_unit_year, authority_age_years factors, fleet_size_units factors and the venue_state tiers in config/rates.yaml, each with its standard error, and flag any segment with fewer than 200 crashes.
```

## Prompt 3 — Real sample set (30 min, after Prompt 2)
```
Run python -m analysis.build_sample_set --n 45 to draw a stratified sample of real carriers and enrich them via QCMobile into data/cache. Then run python -m rater.book samples/submissions_real --csv data/derived/book_check_real.csv. Report the decline rate, refer rate, rules-fired histogram and per-unit premium distribution. If the decline rate is above 35% or below 10%, list which rules dominate and suggest threshold changes in config/rules.yaml — but do not apply them. Also pick 5 DOTs from the census at random that are NOT in the sample, run them cold, and report anything that errored or looked absurd.
```

## Prompt 4 — vPIC and VIN edge cases (20 min)
```
Test rater/enrich.decode_vins against the live NHTSA vPIC batch endpoint with: two real Class 8 tractor VINs, one trailer VIN, one pickup VIN, one malformed 17-char string. Save the raw response to data/raw/vpic_sample.json. Confirm _parse_vin and features._is_non_commercial classify trailer and pickup as non-commercial and the tractors as commercial. Fix the GVWR / BodyClass / VehicleType string matching if needed.
```

## Prompt 5 — SERFF benchmark (1–2 h)
```
Find publicly accessible commercial auto / trucking rate filings for Progressive (Progressive County Mutual or Progressive Casualty), Sentry, Great West or Canal via a state SERFF portal (Texas TDI, Florida OIR, Illinois DOI and others expose SERFF filing search). Download 2-3 filings as PDF into data/raw/serff/ and add rows to docs/SOURCES.md. Extract: exposure base, radius classes and factors, GVW classes, new-venture / years-in-business factors, driver factors, any territory factors for TX/FL/GA/LA/CA, minimum premiums. Write the extracted structure into docs/MARKET_BENCHMARK.md as a table alongside my config/rates.yaml factors, and highlight where mine differ by more than 20%.
```

## Prompt 6 — Market quotes (45 min)
```
Collect 6-10 observed 2025-2026 price points for primary auto liability at $1m CSL for 1-5 unit for-hire trucking (broker articles, OOIDA, Progressive/other quote examples, trucking forums quoting actual renewals). For each record: source URL, date, carrier profile (units, years in business, state, radius, commodity), quoted annual premium and per-unit premium. Add to docs/MARKET_BENCHMARK.md. Then run python -m rater on a synthetic submission matching each profile (use samples/make_synthetic_samples.py as a template) and tabulate our price vs observed. Do not change config; just report the gaps.
```

## Prompt 7 — L&I insurance history (optional, 1–2 h)
```
Write analysis/li_history.py that, for each DOT in samples/submissions_real, fetches the FMCSA Licensing & Insurance carrier detail (li-public.fmcsa.dot.gov, "Active/Pending Insurance" and "Insurance History" and "Authority History" pages), parses insurer name, policy effective/cancellation dates, cancellation reason, and authority grant/revocation dates, and caches to data/cache/li/<dot>.json. Then wire rater/enrich.py to read that cache and set features insurance_cancellation_24m and authority_age_years from it when present (submission field remains the fallback). Be polite: 1 request/second, cache everything, never raise.
```

## Prompt 8 — Chameleon flag (optional, 45 min)
```
Using data/raw/census.csv, build data/derived/revoked_addresses.parquet: physical address + phone for every carrier with inactive/revoked status. Then in rater/features.py set chameleon_flag=True when the enriched carrier's address or phone matches a revoked carrier registered within 3 years before this carrier's add date. Add a unit test with a fabricated pair.
```

## Prompt 9 — Physical damage (bonus, 1 h)
```
Add config/pd_rates.yaml and rater/physdam.py: stated value per unit from vPIC make/model/year via a simple depreciation table (config), comp and collision rates as % of value with vehicle-age and radius relativities, deductible credits. Expose price_physdam(submission) and add a --with-pd flag to rater.book. Keep it entirely config-driven and add a line to docs/RATING_MANUAL.md rendering.
```

## Prompt 10 — Final polish before the walkthrough
```
Run ./run_all.sh and fix anything that fails. Then read docs/RATIONALE.md and update every number in sections 1, 5 and 6 to match the current outputs in data/derived (crash_rate_by_segment.csv, tornado.csv, ilf_table.csv, book_check_real.csv). Re-render the manual. List every remaining VERIFY marker across the repo with a one-line status.
```
