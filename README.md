# Small-Fleet Trucking Rater

Pricing and risk-selection core for **for-hire trucking, 1–5 power units, primary auto liability ($1m CSL)**. A submission (USDOT + drivers + VINs + radius + commodity) goes in; the system enriches it from FMCSA and NHTSA public data, forms a loss-cost view, and returns one of three decisions with a full breakdown: **price**, **refer** (priced, but flagged for a human), or **decline** (with the rule that fired).

Start here:

| Document | What it is for |
|---|---|
| [docs/DELIVERABLES.md](docs/DELIVERABLES.md) | Maps every deliverable in the task brief to the repo, explains how the code works end to end, lists every decline/refer rule with why and how often it fires, and keeps the **gap register** |
| [docs/DEFEND.md](docs/DEFEND.md) | The walkthrough: method, sources, mental model, process; what book it attracts and whether it makes money; where it is wrong and what to watch; roadmap; bonus topics; open research items |
| [docs/RATIONALE.md](docs/RATIONALE.md) | Exposure base, loss-cost view, every numbered assumption with its evidence and its price impact |
| [docs/RATING_MANUAL.md](docs/RATING_MANUAL.md) | The rating manual, rendered from `config/rates.yaml` (never edited by hand) |
| [docs/SOURCES.md](docs/SOURCES.md) | Every dataset and benchmark: URL, what it feeds, archive status |
| [docs/MARKET_BENCHMARK.md](docs/MARKET_BENCHMARK.md) | Ten observed 2025–26 price points vs our rater, and the calibration changes they drove |
| [docs/FREQUENCY_PROPOSAL_2026-09-09.md](docs/FREQUENCY_PROPOSAL_2026-09-09.md) | Census × crash-file GLM: what was adopted, what was rejected and why |
| [docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md) | Running someone else's carriers live: where their files go, the exact commands, and what each decline/refer means |

## Quick start

```powershell
# PowerShell (Windows)
pip install -r requirements.txt
$env:RATER_OFFLINE = "1"                                        # fixtures + cached API responses only; no network
python -m rater samples\submissions\00_established_clean_ia.json # one submission -> full breakdown
python -m rater.book samples\submissions samples\submissions_real # book check across any folders / files
python run_all.py                                                # everything: samples, manual, ILFs, tornado, backtest, portfolio, tests, book checks
```

```bash
# bash / macOS / Linux
pip install -r requirements.txt
RATER_OFFLINE=1 python -m rater samples/submissions/00_established_clean_ia.json
RATER_OFFLINE=1 python -m rater.book samples/submissions samples/submissions_real
./run_all.sh                                                     # wrapper around run_all.py
```

Python 3.10+; dependencies are pyyaml, numpy, pandas, requests, scipy, statsmodels, pytest.

### Running your own carriers (live enrichment)

1. Register for a free FMCSA QCMobile webKey at https://mobile.fmcsa.dot.gov/QCDevsite/ and put it in a `.env` file at the repo root: `FMCSA_WEBKEY=...` (`.env` is gitignored; `rater/config.py` loads it).
2. Leave `RATER_OFFLINE` unset or set it to `0`. Every API response is cached under `data/cache/`, so a carrier is fetched once.
3. `python -m rater.book path/to/your/folder` (or a list of files). vPIC VIN decoding needs no key.

If the API is unreachable, the carrier is priced on segment defaults and referred (rule R02) rather than declined or errored. Without a key and without `RATER_OFFLINE=1`, an unknown DOT behaves the same way.

**Registration dates come from the census, not the API.** QCMobile returns no `addDate`, MCS-150 date or hazmat/passenger flag, so those come from an FMCSA census snapshot. `data/raw/census.csv` is 731 MB and gitignored, so the repo ships **`data/census_slim.csv.gz`** — the same columns for the 1.95 M carriers with ≤ 6 power units, 19.3 MB — and `rater/enrich.py` indexes that automatically when the full file is absent. A clone therefore gets the same authority ages, and the same decisions, as the machine this was built on. Rebuild it with `python -m analysis.build_census_slim` after re-pulling the census.

## Submission format

Only `usdot` is needed to get a decision. Everything else is coerced, defaulted from the FMCSA record, and the assumption recorded in the result's `flags`. Canonical form ([config/schema.json](config/schema.json)):

```json
{
  "submission_id": "example",
  "usdot": 1000986,
  "drivers": [{"age": 41, "cdl_years": 12}, {"age": 35, "cdl_years": 4}],
  "units": [{"vin": "1FUJGLDR3CLBP8834"}, {"vin": "1XKYDP9XXFJ440749"}],
  "radius": "regional_201_500",
  "commodity": "dry_van",
  "garaging_state": "TX",
  "limit": 1000000,
  "insurance_history": {"cancellation_24m": false}
}
```

The ingest is deliberately lenient so files that do not follow the schema to the letter still run. Keys are matched case-insensitively and through aliases; values are coerced; a submission nested one level down (`{"carrier": {...}}`) is unwrapped. Every assumption lands in the result's `flags`:

| Field | Also accepted as | Value forms accepted |
|---|---|---|
| `usdot` | `dot`, `dot_number`, `usdot_number`, `us_dot` | `1000986`, `"1000986"`, `1000986.0`, `"USDOT 1000986"` |
| `units` | `vins`, `vehicles`, `trucks`; count via `power_units`, `unit_count`, `num_units` | list of `{"vin": ...}`, list of VIN strings, one VIN string, or a bare unit count (no VINs) |
| `drivers` | `driver_count`, `num_drivers`, `total_drivers` | list of driver objects, or a count |
| `radius` | `operating_radius`, `radius_miles` | band name, `local`/`intermediate`/`regional`/`long_haul`, a number of miles (`300`), or `"500+ miles"` |
| `commodity` | `cargo`, `commodity_type`, `freight` | free text (`"Dry Van"`, `"reefer"`, `"flatbed"`, ...) |
| `garaging_state` | `state`, `domicile_state`, `phy_state` | two-letter code or full name (`"Iowa"`), any case |
| `limit` | `csl`, `liability_limit` | `1000000`, `"1,000,000"`, `"1m"`, `"750k"` |

## What the book check prints

`python -m rater.book <folders or files> [--csv out.csv] [--jsonl out.jsonl]` prints priced / referred / declined / errored counts, decline and refer rates, how many risks sit at the minimum premium, the premium distribution (total policy and per power unit), a histogram of rules fired, every errored submission with its reason, and one line per submission. An unreadable file is reported, not fatal.

A file may hold one submission (JSON object) or many — a **JSON array**, a **`.jsonl`** feed, or a **`.csv`** with one row per carrier (header spellings resolve through the same alias table). Each carrier is its own result row, tagged `<file>#<i>`. `python -m rater <folder>` runs a book check as well.

Current results (offline, run 2026-09-10): synthetic adversarial set of 31 → 12 priced / 5 referred / 13 declined / 1 unreadable file; 45 real carriers drawn from the FMCSA census → 16 priced / 18 referred / 11 declined (decline rate 24.4%, refer rate 40.0%); 68 cold-start carriers the rules were never tuned on → 49 priced / 8 referred / 11 declined, 0 errors; 10 market-benchmark mirrors → 9 priced / 1 referred; 16 carriers across the four container shapes in `samples/reviewer_formats` → 12 priced / 3 referred / 1 deliberately corrupt file. Details and per-rule counts in [docs/DELIVERABLES.md](docs/DELIVERABLES.md).

## How it works

```
submission.json
   │  rater/ingest.py      normalise: aliases, coercion, defaults, flags            (never raises)
   ▼
   │  rater/enrich.py      FMCSA QCMobile carrier + BASICs + authority + classification, local census snapshot,
   │                       NHTSA vPIC VIN decode.  Order: live API → data/cache → samples/fixtures → segment defaults
   ▼
   │  rater/features.py    flat feature dict: exposure, authority age, crashes, OOS ratios, VIN classes, mileage, ...
   ▼
   │  rater/rules.py       config/rules.yaml: any DECLINE wins, else any REFER, else PRICE
   ▼
   │  rater/losscost.py    base loss cost per power-unit-year = crash rate × claims per crash × limited severity × trend;
   │                       Bühlmann credibility on the carrier's own 24-month crashes
   ▼
   │  rater/price.py       × relativities (config/rates.yaml) → loss cost → + ALAE ÷ (1 − expense − reinsurance − profit)
   │                       → floor $8,000 per unit → × units + policy fee.  Returns decision + breakdown + flags.
   ▼
result dict          rater/book.py runs price() over folders and summarises
```

Every number the rater uses lives in `config/rates.yaml`, tagged **[E]** estimated from data, **[S]** selected by judgment, or **[B]** benchmark-anchored, with the evidence in a comment. `docs/RATING_MANUAL.md` is rendered from that file so manual and code cannot diverge.

## Repository layout

```
config/       rates.yaml (the rating manual), rules.yaml (decline / refer rules), schema.json (submission shape)
rater/        ingest → enrich → features → rules → losscost → price;  book.py (book check CLI);  __main__.py (single-file CLI)
analysis/     build_frequency_tables.py (census × crash file → crash rates, NB GLM), build_sample_set.py (real-carrier draw),
              fit_severity.py (ILFs), sensitivity.py (tornado), synthetic_backtest.py, portfolio.py (1-in-200, capital, ROC),
              render_manual.py
samples/      submissions/ (25 synthetic carriers + 6 edge cases), submissions_real/ (45 census-drawn carriers),
              submissions_benchmark/ (10 market price-point mirrors), reviewer_formats/ (16 carriers in 9 files across
              4 container shapes), fixtures/ (fake API responses for the synthetic sets),
              make_synthetic_samples.py, make_benchmark_samples.py
data/         census_slim.csv.gz (committed 19 MB census subset: registration dates for a clone with no bulk file)
data/raw/     bulk downloads (gitignored, 1 GB: census.csv, crash_2023..2026.csv) + archived API samples and data
              dictionaries (committed)
data/cache/   carrier/ and vin/ API responses (committed so the real-carrier book check reproduces offline);
              census.sqlite (rebuilt locally from census.csv)
data/derived/ every table the analysis scripts write: crash rates by segment and state, GLM relativities, ILFs,
              tornado, market benchmark, book-check outputs
docs/         see the table at the top
tests/        pytest: never-crash on every sample, garbage input, breakdown reconciles, manual == code, rule firing,
              live API shapes, input aliases, book summary
run_all.py    reproduce everything (run_all.sh wraps it)
```

## Reproducing the analysis from raw data

The rater itself runs from the committed caches. Re-deriving the frequency tables needs the two bulk FMCSA files (about 1 GB, gitignored). Pull them with the Socrata endpoints recorded in [docs/SOURCES.md](docs/SOURCES.md) rows S3 and S4:

```
data/raw/census.csv        https://data.transportation.gov/resource/kjg3-diqy.csv?$order=:id            (paged 250k rows)
data/raw/crash_<year>.csv  https://data.transportation.gov/resource/aayw-vxb3.csv?$where=report_date >= 'YYYY0101' AND report_date <= 'YYYY1231'&$order=:id
```

then `python -m analysis.build_frequency_tables --years 3` (writes `data/derived/crash_rate_by_segment.csv`, `crash_rate_by_state.csv`, `glm_relativities.csv`) and, with a webKey, `python -m analysis.build_sample_set --n 45` to redraw the real-carrier sample.

## Status and known gaps

The gap register in [docs/DELIVERABLES.md](docs/DELIVERABLES.md) is the single list. Headline items: BASIC-percentile factors and rule D24 are dormant on live data (FMCSA does not publish property-carrier percentiles); rule R06 (chameleon carriers) is a stub; the insurance-cancellation decline reads a self-declared field until FMCSA L&I is automated; SERFF rate filings have not been pulled; physical damage is designed but not built.
