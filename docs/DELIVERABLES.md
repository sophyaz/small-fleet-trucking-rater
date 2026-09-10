# Deliverables — what the brief asks for, where it lives, how it works

**Brief:** *Small-Fleet Trucking Rater* (Corgi Quant work trial). Build the pricing and risk-selection core for for-hire trucking, 1–5 power units, primary auto liability: a rater that takes any conforming submission and returns a bindable price or a defensible decline, judged by reading how it is built and by running unseen carriers through it.

**Status 2026-09-10:** all five deliverables are in place and runnable offline from a fresh clone. The open items are calibration evidence (SERFF filings, inspection file, ATRI PDFs), two dormant rules, and the physical-damage bonus. On 2026-09-10 a self-review found and fixed four defects worth volunteering: a crash-experience decline rule that could not reach its own threshold, a minimum premium that levelled surcharges away, an unenforced limit table, and an unbalanced credibility procedure leaking ~4% of rate (G24-G27). The rules have since been run cold against 68 carriers from 19 states that were not in the sample they were tuned on, with no retuning afterwards (section 6.1). Section 1 is the full register.

---

## 1. Gap register

Priority: **H** would cost marks or break the live test; **M** weakens a defence answer; **L** cosmetic or roadmap.

| # | Pri | Gap | State (2026-09-10) | Fix / what to say |
|---|---|---|---|---|
| G1 | H | A fresh clone could not reproduce the real-carrier book check: the 53 cached QCMobile records, 5 VIN decodes and the archived raw API samples were gitignored, so `samples/submissions_real` referred all 45 on R02 without a key | **Fixed.** `.gitignore` now keeps `data/cache/carrier/`, `data/cache/vin/`, `data/raw/qcmobile_samples/`, `vpic_sample.json`, `census_readme.txt`, `crash_data_dictionary.pdf` (1.3 MB total; checked: no webKey in any response file). Bulk files (1 GB) stay ignored with pull URLs in SOURCES S3/S4 | Stage and commit those paths |
| G2 | H | Ingest only recognised the key `usdot`; a reviewer file using `dot_number`, `vins`, `state`, `cargo`, a numeric radius, a bare unit count or `"limit": "1m"` was declined D01 or silently defaulted | **Fixed.** Case-insensitive alias tables, numeric radius → band, count and numeric-string coercion, every assumption flagged (`rater/ingest.py`; `test_input_aliases_and_numeric_radius`) | Show the alias table (README) if asked how unseen formats are handled |
| G3 | H | `run_all.sh` was bash-only on a Windows machine | **Fixed.** `run_all.py` is the single cross-platform runner; `run_all.sh` wraps it | — |
| G4 | H | `python -m rater file.json` raised a traceback on a missing argument or unreadable file (the book check already handled it) | **Fixed.** Prints an error dict with a non-zero exit | — |
| G5 | M | `config/schema.json` did not describe the accepted aliases / value forms; `docs/CLAUDE_CODE_PROMPTS.md` statuses were stale | **Fixed** | — |
| G6 | M | Rule **R06 chameleon** is a stub: `chameleon_flag` is hard-coded False, so the rule can never fire | Open; marked DORMANT in `config/rules.yaml` | Needs the revoked-carrier address/phone index from the census file (Prompt 8, ~45 min) |
| G7 | M | Rule **D24** and the BASIC-percentile relativities are dormant on live data: FMCSA returns "Not Public" for property-carrier percentiles (53 of 53 live carriers) | Open by nature of the data; documented in rates.yaml, rules.yaml, RATIONALE §3 | Replacement is a measure-vs-threshold band from the `measureValue` / `basicsViolationThreshold` fields the API does return |
| G8 | M | **SERFF rate filings (S14) not pulled** — the best public benchmark for relativity structure and new-venture factors | Open | DEFEND §8 research list; 1–2 h with a state DOI portal |
| G9 | M | **Inspection file (S5) not pulled** — segment OOS averages (6.2% / 21.5%) are 2009–10 national figures; live small carriers average 19.4% / 29.9%, i.e. near D22's 3× threshold | Open | Re-derive `segment_averages` from the MCMIS inspection file for 1–5 unit carriers; expect D22 to fire less |
| G10 | M | **L&I (S6) not automated** — D23 (insurance cancelled in 24 months) reads the submission's self-declared field | Open; roadmap item 2 | Prompt 7 sketch; say so plainly in the walkthrough |
| G11 | M | **Physical damage** (bonus) is a design, not code | Open | DEFEND §5.2 has the design; Prompt 9 is the build sketch |
| G12 | M | **Trends** (bonus) is a severity trend factor only; no frequency trend by year although the 2023–2026 crash files are on disk | Open | A by-year crash-rate table from `build_frequency_tables` is a 30-minute addition |
| G13 | M | **ILFs look thin** (1.058 at $2m vs market ~1.3–1.5) — the fatal share or Pareto tail is light | Open, flagged in RATIONALE §6 | Multi-limit answer: at $1m primary it does not matter; at $2m+ buy severity data |
| G14 | L | Credibility k = 25 unit-years is selected, not fitted | Open | Fit from crash-file variance components |
| G15 | L | `limits.offered` is not enforced; any limit prices via the limited mean | **Superseded by G26** — and the L priority was wrong: an unenforced limit is a bindable mispricing, not a cosmetic gap | See G26 |
| G16 | L | A submission with no USDOT declines (D01) rather than referring | By design: the DOT is the carrier's identity and every enrichment hangs off it | Say so if challenged |
| G17 | L | Book-check figures shift slightly with the run date (authority age is computed from today) | Expected; outputs regenerated by `run_all.py` | Quote figures with the run date |
| G18 | L | Remaining VERIFY markers: A2 claims-per-crash (only verifiable in force), A8 trend figures vs the ATRI PDFs, A12 OOS averages (G9), S7 SMS methodology change | Open | DEFEND §8 |
| G19 | H | **A USDOT arriving as a float rated the wrong carrier.** `"usdot": 9900001.0` — what a spreadsheet or pandas export produces — had its decimal point stripped by `re.sub(r"\D","",...)` and became `99000010`, a different and possibly real DOT, silently and with no flag | **Fixed 2026-09-10.** `normalise` parses the DOT as a number first and only falls back to digit-extraction for genuine free text, which is now flagged `usdot_parsed_from_text` (`rater/ingest.py`; `test_float_usdot_is_not_a_different_carrier`) | Worth volunteering: it was found by fuzzing the ingest with reviewer-shaped inputs, which is also where G20/G21 came from |
| G20 | H | **A fresh clone priced a different book.** QCMobile returns no `addDate` / `mcs150Date` / HM–PC flags; they come from `data/raw/census.csv`, which is 731 MB and gitignored. Without it every live-fetched carrier is assumed 0.5 years old → 1.65 new-venture factor and an R01 refer | **Fixed 2026-09-10.** `analysis/build_census_slim.py` writes `data/census_slim.csv.gz` (1.95 M carriers ≤ 6 units, 19.3 MB, committed); `rater/enrich.py` indexes it when the full census is absent. A row missing from the slim file is *unknown*, not "not in the snapshot", so R08 stays silent for large carriers | `test_slim_census_fallback_supplies_registration_dates` |
| G21 | M | The book check read one submission per `*.json` file; a reviewer's JSON array, `.jsonl` feed or CSV of DOTs produced an error row or a D01 decline | **Fixed 2026-09-10.** `rater/book.py` reads object / array / jsonl / csv, one result row per carrier tagged `<file>#<i>`; `python -m rater <folder>` runs a book check | `samples/reviewer_formats/` is the demo folder |
| G22 | H | **The headline 24.4% decline rate is partly a sampling artifact.** The census `authorized_for_hire` flag is self-declared and goes stale, so a random census draw over-samples dormant shells. Only 23 of the 45 drawn carriers (51%) have active for-hire authority *and* BI/PD insurance on file — the other half are registrations no broker would submit | **Measured 2026-09-10**, and not a defect in the rater: `analysis/build_operating_set.py` draws the same segment filtered to operating carriers and the decline rate falls to 1 of 38 (2.6%). Both figures are reported in section 6.1 | Volunteer it: "24% is what a census draw declines; 2.6% is what a submission flow declines, and the difference is dormancy, not appetite" |
| G23 | M | The rules in section 5 were tuned on the 45-carrier census draw, which therefore could not also be the evidence that they generalise to unseen carriers | **Fixed 2026-09-10.** Three cold-start tracks (68 carriers, section 6.1) exclude every already-cached DOT; tracks A and B also exclude the original ten focus states. No rule was retuned afterwards, so the figures are a genuine out-of-sample read | Section 6.1; D11 fired on a real carrier for the first time |
| G24 | H | **The crash-experience decline rule could never fire.** D20 declined on `cred_rate_relativity > 3.0`, but that relativity caps the own rate at 3× and then credibility-weights it, so its ceiling is 1 + 2Z — 1.148 at one power unit, **1.571 at five**. No carrier in a 1–5 unit appetite could reach 3.0. Combined with a flat minimum premium the effect was worse than a dead rule: a 2-unit carrier with **12 crashes in 24 months** (67× segment) priced at exactly the clean $8,000/unit floor with **no rule fired at all**, while a carrier with one fatal plus one fender-bender declined on D21 | **Fixed 2026-09-10.** D20 now tests the uncapped `own_crash_rate_ratio` (> 4× segment, gated on ≥ 3 crashes so a noisy one-truck record cannot decline); new **R10** refers 2+ crashes at > 3× segment; new **R11** refers any fatal crash. The floor no longer levels the book — see G25. D20 now fires on the synthetic set and R10/R11 fire on real carriers | `test_d20_threshold_is_reachable_in_the_1_to_5_unit_segment`. **Volunteer this**: it was found by asking what the maximum attainable value of the rule's own test statistic was |
| G25 | H | **The minimum premium levelled the book.** `max(technical, $8,000)` was applied flat, so every surcharge that landed under the floor vanished: a 1-unit carrier with a crash paid exactly what a crash-free one paid. The floor binds on ~40% of the operating draw, so this was the normal case, not an edge case — and it silently contradicted the claim in DEFEND §1.2 that a one-truck carrier with one crash "gets about a 15% surcharge" (the *relativity* did; the *premium* did not) | **Fixed 2026-09-10.** `loadings.minimum_premium_experience_scaled`: the floor is multiplied by the experience relativity when that relativity is a surcharge, never when it is a discount, so every clean risk stays at the market-anchored $8,000 and an adverse record cannot fall back to it | `test_adverse_crash_record_cannot_price_at_the_clean_floor`. Residual, worth knowing: at one power unit `own_rate_cap_multiple` = 3.0 is already saturated by the *first* crash, so price alone cannot separate 1 crash from 5 — which is precisely why D20/R10 gate on the raw count too |
| G26 | H | **`limits.offered` was documentation, not a rule** (was G15, rated L — wrong: the rater issued a *bindable* price at a limit it cannot rate). Any submitted limit priced through the mixture's limited mean, so a **$5m CSL came out 9.3% above the $1m price** ($27,732 vs $25,365) against market trucking ILFs of 1.3–1.5 at $2m alone | **Fixed 2026-09-10.** **D32** declines a limit below the federal minimum or above the top limit offered; **R12** refers $2m — offered, but the tail is not calibrated for it (G13); **R13** refers a limit that is merely off the grid inside the writable band. The first cut of this fix declined `"limit": 1000001` outright, which traded a mispricing for a worse failure on an explicitly graded deliverable | `test_offered_limits_are_enforced`, `test_non_positive_limit_is_flagged_not_silently_defaulted` |
| G28 | M | **Two documents had drifted behind the code.** The `MARKET_BENCHMARK.md` price tables and the operating-draw median per unit ($9,038) predated the 2026-09-10 credibility and floor corrections, which raised every non-floor profile by 4–6%; the rendered `RATING_MANUAL.md` §5 still said any limit off the offered list declines, which stopped being true when D32 was narrowed and R13 was added the same day | **Fixed 2026-09-10.** `MARKET_BENCHMARK.md` carries a current table (median gap to the liability estimate +2.8%, to the published figure −5.1%, 8 of 10 within ±20%) and the superseded tables are marked as such; `analysis/render_manual.py` names D32, R12 and R13 correctly and the manual was re-rendered; the operating median is now $9,943 here and in DEFEND §2.1 | Worth volunteering as the reason for the gap register: **a number regenerated by a command will drift from a number typed into prose, so say which is which.** `data/derived/*.csv` is always the current answer |
| G27 | M | **The credibility procedure was not balanced.** `own_rate_cap_multiple` truncates the upside of the own-experience relativity but nothing truncates the downside (no crashes → `own_rel` = 0), so E\[cred_rel] < 1 by construction: **measured 0.958 across 113 real / operating / holdout carriers, 84% of them below 1.00**, against a closed-form expectation of 0.945–0.961. The segment crash rate was measured across all carriers *including* crash-free ones, so the base loss cost already contains them — crediting them again leaked 4–7% of rate (≈ $1m of premium on the $23.6m portfolio, against a $1.65m profit load) | **Fixed 2026-09-10.** `credibility.offbalance_correction`: the relativity is divided by its own expectation at that fleet size under Poisson(segment rate), so the procedure is balanced by construction and a clean carrier is credited for beating the segment *average*, not a capped worst case | `test_credibility_is_balanced`. Have the 0.958 to hand: *"what is the premium-weighted mean of your experience relativity?"* is the question this answers |

---

## 2. Deliverable checklist against the brief

| Brief bullet | Status | Where | Run | Evidence |
|---|---|---|---|---|
| **A working rater** — submission in, premium out, priced off an explicit loss-cost-plus-margin view; a number you'd take money on | Done | `rater/price.py`, `config/rates.yaml`, `docs/RATING_MANUAL.md` | `python -m rater samples/submissions/00_established_clean_ia.json` | Base loss cost $4,151 per unit-year = 0.045 crashes × 2.0 claims per crash × $42,265 limited severity × 1.091 trend; gross-up (1+14% ALAE) ÷ (1 − 22% expense − 6% reinsurance − 7% profit); floor $8,000 per unit, scaled by the experience relativity when that is a surcharge (G25); every step in the returned `breakdown` |
| **A decline list / rules** — the risks you won't write, and why | Done | `config/rules.yaml` (17 decline, 13 refer), section 5 below, RATIONALE §2 | rules fire inside every `price()` call; counts in the book check | 11 of 45 real carriers declined (24.4%); 13 of 31 synthetic; each with rule id and reason |
| **A system that generalises** — runnable on unseen submissions, sensible handling of missing or bad inputs | Done | `rater/ingest.py` (aliases, coercion, flags), `rater/enrich.py` (never raises; API → cache → fixture → segment defaults), `rater/price.py` (last-line try/except) | `python -m rater.book samples/submissions` includes six edge cases: unknown DOT, missing DOT, bad VINs, zero drivers, garbage types, not-JSON | Tests `test_never_crashes_on_any_sample`, `test_garbage_input`, `test_input_aliases_and_numeric_radius`; edge cases produce refer / decline / price with flags, and the unreadable file is reported as an error line |
| **...demonstrated on carriers the rules were not built on** | Done | `samples/submissions_holdout/` (30), `samples/submissions_operating/` (38), `samples/submissions_curveball/` (14 rows in 6 files) | `python -m rater.book samples/submissions_holdout samples/submissions_operating samples/submissions_curveball` | Section 6.1. 68 cold-start carriers from 19 states outside the original ten, none previously cached, no rule retuned afterwards; 0 crashes and every error row explained |
| **A reproducible pipeline** — sourced data plus a short rationale: exposure base, key variables, loss-cost view, every judgment call cited | Done | `run_all.py`; `docs/RATIONALE.md` (assumptions A1–A13 with impact), `docs/SOURCES.md` (S1–S16), `docs/FREQUENCY_PROPOSAL_2026-09-09.md`, `docs/MARKET_BENCHMARK.md`; archived sources in `data/raw/` | `python run_all.py` (offline); `python -m analysis.build_frequency_tables --years 3` after pulling S3/S4 | Every rates.yaml value tagged [E]/[S]/[B] with its source; derived tables in `data/derived/` |
| **A self-running book check** — priced vs declined counts, decline rate, price distribution, errored submissions with reason; must not crash or decline everything on thin-data carriers | Done | `rater/book.py` | `python -m rater.book <folders or files> [--csv] [--jsonl]` | Section 6; thin-data carriers go to refer with a price (R01/R02/R07/R09), not decline |

Bonus items are in section 8.

---

## 3. How the code works

### 3.1 Pipeline

`price(submission)` in `rater/price.py` runs six stages and returns one dict. Nothing in the chain raises on bad data; the outer try/except is the last line of defence and turns any unexpected exception into `decision: "error"` with the message and trace.

1. **Ingest** (`rater/ingest.py`, `normalise`). Resolves key aliases case-insensitively, coerces values (numeric strings, miles → radius band, `"1m"` → 1,000,000, bare counts), validates VINs against the 17-character pattern, defaults what is missing (radius → intermediate, commodity → unknown at 1.10, limit → $1m) and appends a flag for every assumption. Output: a normalised dict plus `ingest_flags`.
2. **Enrich** (`rater/enrich.py`). `fetch_carrier(usdot)` reads, in order, `data/cache/carrier/<dot>.json`, `samples/fixtures/carrier/<dot>.json`, then the live QCMobile API (carrier record, BASICs, authority, cargo, operation classification, docket numbers) if a webKey is set and `RATER_OFFLINE` is not 1. Live responses are cached. Fields the API does not expose (registration date, MCS-150 date and mileage, hazmat / passenger flags) come from the local census snapshot via a sqlite index built once from `data/raw/census.csv`. Any failure returns `degraded: True` instead of raising. `decode_vins` batches VINs to NHTSA vPIC (no key), caches each, and gates "decoded" on the fatal error codes so a garbage string is not treated as a truck. An unknown DOT is HTTP 200 with null content, which is recorded as `found: False` (→ D01), distinct from an API error (→ R02).
3. **Features** (`rater/features.py`, `build`). Merges submission and enrichment into one flat dict: power units (declared, else census, else 1), drivers, driver/unit ratio, unit-count mismatch, authority age from the registration date, MCS-150 age, for-hire / interstate status with positive-evidence logic, authority letters and BI/PD filing, crash counts, inspections and OOS ratios to segment averages, BASIC percentiles where public, mileage per unit with a plausibility floor, average vehicle age, share of non-commercial VINs.
4. **Loss cost and credibility** (`rater/losscost.py`). Base loss cost per power-unit-year = crash rate × claims per crash × limited mean severity at the submitted limit × trend. Severity is a three-component mixture (property-damage-only lognormal, injury lognormal, fatal Pareto) whose limited mean is computed by seeded Monte Carlo, so any limit can be priced. Credibility: Bühlmann Z = n/(n+25) with n = units × 2 years; the carrier's own 24-month crash rate (capped at 3× segment) is blended with the segment rate.
5. **Rules** (`rater/rules.py`, `config/rules.yaml`). Declarative conditions over the feature dict (`eq`, `gt`, `between`, `all`, `any`, ...). A missing field never fires a rule. Any decline wins; else any refer; else price. Every rule that fired is returned with its id and reason.
6. **Price** (`rater/price.py`). Relativities from `config/rates.yaml`: authority age, fleet size, radius, commodity, venue state, driver/unit ratio, driver experience, vehicle age, driver and vehicle OOS, BASICs, MCS-150 staleness, mileage intensity, own-experience credibility. A stack cap holds authority × venue × radius at 2.0 before the rest apply; the total product is clamped to [0.60, 3.25]. Loss cost × (1 + ALAE) ÷ (1 − expense − reinsurance − profit) → technical unit premium → max(floor, .) where the $8,000 floor is scaled by the experience relativity when that relativity is a surcharge, so an adverse crash record cannot fall back to the clean-risk floor (G25) → × units + $250 policy fee. A declined risk still carries `premium_if_written` so the book check can show what it would have cost.

**Book check** (`rater/book.py`). `run(paths)` globs `*.json` in each folder (or takes files), catches unreadable files as error rows, prices the rest; `summarise` prints the counts, rates, minimum-premium hits, premium distribution (total and per unit), rule histogram, error list and one line per submission; `--csv` / `--jsonl` write the same.

### 3.2 Modes

| Mode | Set | Behaviour |
|---|---|---|
| Offline | `RATER_OFFLINE=1` (env or `.env`) | Cache + fixtures only. Unknown DOT → degraded → refer R02 with a segment-default price |
| Live | `FMCSA_WEBKEY` set, `RATER_OFFLINE` unset or 0 | API first, cached afterwards. Unknown DOT → decline D01. API error → refer R02 |

### 3.3 Config as the manual

`config/rates.yaml` is the only place a number lives. Each value carries a tag and a comment with its evidence: **[E]** estimated from the census × crash file, **[S]** selected by judgment with the range considered, **[B]** anchored to a published benchmark. `python -m analysis.render_manual` writes `docs/RATING_MANUAL.md` from it, and `test_manual_matches_code` asserts the rendered limited severity equals what the rater uses. `config/rules.yaml` holds the decision rules in the same spirit: readable, diffable, no code change to tune a threshold.

---

## 4. Submission schema and input handling

Canonical fields: `usdot` (required), `submission_id`, `drivers[] {age, cdl_years, years_with_carrier}` or `driver_count`, `units[] {vin}`, `radius` (four bands), `commodity`, `garaging_state`, `limit`, `insurance_history {cancellation_24m}`. `config/schema.json` documents each, including aliases.

What happens to bad or missing input:

| Input problem | Handling | Flag |
|---|---|---|
| Key spelled differently (`dot_number`, `vins`, `state`, `cargo`, `State`) | Alias resolved | `alias:<key>-><canonical>` |
| Submission nested one level down (`{"carrier": {...}}`, `{"submission": {...}}`) | Merged over the parent; fields at both levels read | `unwrapped:<key>` |
| USDOT as a float (`9900001.0`, spreadsheet export) | Parsed as a number, not digit-stripped (G19) | — |
| USDOT with text (`"USDOT 1234"`, `"MC-429079"`) | Digits extracted, source shown | `usdot_parsed_from_text:<raw>` |
| No USDOT at all | Cannot enrich → decline D01 | `usdot_missing_or_invalid` |
| Units as VIN strings, one VIN string, or a bare count | Accepted; count and VIN list reconciled to the larger | `units_given_as_count_no_vins`, `unit_count_3_vs_1_vins_use_max` |
| Invalid VIN | Skipped, others decoded | `invalid_vin:<value>` |
| No units | FMCSA census power-unit count | `units_missing_use_census` |
| Drivers as a number or numeric string | Treated as a count | `drivers_given_as_count` |
| Radius as miles, `"300 miles"`, `"500+ mi"`, `regional` | Mapped to a band | `radius_miles:300->regional_201_500` |
| Radius as an object (`{"miles": 400}`) | Inner value taken, then mapped | `radius_object_unwrapped:400` |
| State as a full name (`"Iowa"`, `"New Jersey"`) | Mapped to the two-letter code | `state_name:IOWA->IA` |
| Split limits (`"1000/1000/1000"`) | Not invented into a CSL; priced at $1m and flagged | `limit_split_form_not_offered:...` |
| Radius missing or unparseable | Intermediate (neutral factor) | `radius_missing_default_intermediate` |
| Commodity missing | `unknown` at 1.10 | `commodity_missing_default_unknown` |
| Commodity in hazmat / tanker / passenger / HHG / auto-hauler / livestock / oilfield / garbage | Decline D11 | — |
| State missing | FMCSA physical state | `garaging_state_missing_use_census` |
| Limit as `"1m"`, `"750,000"`, missing | Parsed; default $1m | `limit_parsed:...` |
| Garbage types (`"drivers": "three"`, `"units": "two trucks"`) | Ignored with a flag; census values used | `drivers_not_a_list_ignored`, `units_not_a_list_ignored` |
| File is not JSON | Book check reports an error row; single-file CLI prints an error dict | — |
| API down / no key for an unknown DOT | Segment defaults, authority age assumed 0.5 y, refer | `enrichment_degraded_segment_defaults`, `authority_age_unknown_assumed_0.5y` |

---

## 5. Decline and refer rules

Any decline wins; otherwise any refer; otherwise price. Counts are from the current book checks (`data/derived/book_check.csv`, 31 synthetic incl. 6 edge cases; `book_check_real.csv`, 45 real carriers). The **Synthetic** and **Real** columns are those two sets; for what fired on the cold-start holdout — a different 68 carriers in different states — see section 6.1, where D11 appears on a real carrier for the first time. Status: **live** fires from live data; **dormant** cannot fire from public data today; **declared** relies on a submission field; **stub** not implemented.

### Declines

| Id | Fires when | Why we won't write it | Evidence / source | Synthetic | Real | Status |
|---|---|---|---|---|---|---|
| D01 | No FMCSA carrier record (USDOT missing, or API says not found) | The DOT is the identity; nothing can be verified | QCMobile returns null content for unknown DOTs (S1) | 1 | 0 | live |
| D02 | `allowedToOperate` = N | Federal revocation / OOS; illegal to run | QCMobile carrier record | 0 | 3 | live |
| D03 | Out-of-service order date present | Same as above, the explicit order | QCMobile `oosDate` | 1 | 3 | live |
| D04 | Safety rating Unsatisfactory | FMCSA's own conclusion after a compliance review | QCMobile `safetyRating` | 1 | 0 | live |
| D05 | USDOT registration inactive (`statusCode` ≠ A) | Not an operating carrier; `allowedToOperate` still says Y for these (real DOT 3456789) | Live finding 2026-09-09 | 0 | 5 | live |
| D10 | Power units outside 1–5 | Out of the segment the rates were built for | Brief scope | 1 | 0 | live |
| D11 | Hazmat / tanker / passenger / HHG / auto-hauler / livestock / oilfield / garbage (submission text, FMCSA HM or PC flag, cargo class) | Different severity, limits ($1m oil, $5m hazmat), and data; not priced here | 49 CFR 387.9 (S15); appetite | 1 | 0 | live |
| D12 | Positive evidence of private or intrastate-only operation | Different exposure and pricing; the segment rate is for-hire interstate | Census `carrier_operation`, QCMobile operation classification; empty classification is *unknown* (R09), not private | 1 | 0 | live |
| D20 | Own crash rate > 4× segment **on ≥ 3 crashes** in 24 months (uncapped ratio) | Repeated crashes at this fleet size are not noise | Rewritten 2026-09-10, G24. The old test — credibility-weighted relativity > 3.0 — was unreachable: that relativity's ceiling is 1 + 2Z = 1.571 at five units | 1 | 0 | live |
| D21 | A fatal crash plus at least one other crash in 24 months | One fatal can be bad luck; two events with a fatal is a pattern at this fleet size | Judgment [S] | 1 | 0 | live |
| D22 | Driver OOS rate > 3× segment average with ≥ 5 driver inspections | Driver compliance is the loss driver we can see; 3× with a real sample is not noise | Segment averages (A12, G9: averages are stale so this fires more than intended) | 3 | 3 | live |
| D23 | Insurance cancelled / coverage gap in last 24 months | Prior insurer's decision is information; gaps precede authority revocation | Submission field until L&I is automated (G10) | 1 | 0 | declared |
| D24 | Unsafe Driving BASIC ≥ 90th percentile | FMCSA intervention band | Percentiles "Not Public" for property carriers (G7) | 1 (fixture) | 0 | dormant |
| D25 | MC authority previously granted, now inactive, and no BI/PD filing on file | Revoked for insurance lapse; cannot legally run; distinct from a pending applicant (R07) | Real DOT 3987512 shape; 5 of 45 | 0 | 5 | live |
| D30 | More than half the submitted VINs decode to trailers, cars or light pickups | Submission does not describe rated power units | vPIC live strings (S8) | 1 | 0 | live |
| D31 | Declared units differ from census by > 3 or by > 2× | Gaming the exposure base downward, or a stale record we cannot trust | Census / QCMobile `totalPowerUnits` | 1 | 0 | live |
| D32 | Limit below the federal minimum ($750k) or above the top limit offered ($2m) | Below the minimum we cannot legally write it; above the top limit they want a layer we do not rate. A $5m CSL used to price 9.3% above $1m | Added 2026-09-10, G26 | 0 | 0 | live |

### Refers (priced, human review)

| Id | Fires when | Why refer rather than price or decline | Synthetic | Real | Status |
|---|---|---|---|---|---|
| R01 | Authority < 6 months and no inspection history | The public record is empty; the new-venture surcharge is applied but a human should look | 1 | 6 | live |
| R02 | Enrichment degraded (API down, no key for an unknown DOT) | Priced on segment defaults; must not bind unseen | 1 | 0 | live |
| R03 | Safety rating Conditional | Known deficiencies short of Unsatisfactory | 1 | 0 | live |
| R04 | MCS-150 not updated in > 2 years | Self-reported units / mileage are stale; 1.08 factor applied | 1 | 3 | live |
| R05 | Zero drivers declared | Inconsistent submission | 2 | 0 | live |
| R06 | Shared address / phone with a revoked carrier | Chameleon carrier signal | 0 | 0 | **stub** (G6) |
| R07 | No active common / contract for-hire authority on file | A new applicant cannot get authority until an insurer files the BMC-91: this is what a legitimate prospect looks like at quote time. 16 of 45 real carriers | 0 | 16 | live |
| R08 | DOT absent from the census snapshot | Registered after the monthly snapshot, or inactive | 0 | 0 | live |
| R09 | QCMobile has no operation classification yet | Registration too new to confirm for-hire status; refer, never a clean price, never D12 | 0 | 6 | live |
| R10 | ≥ 2 crashes in 24 months at > 3× segment rate | A *second* crash inside the window at this fleet size is not noise. Gated at 2, not 1: 16 of the 18 carriers with any crash across 113 real / holdout / operating carriers have exactly one, and at Z ≈ 0.07 the model's own position is that a single one is noise — gating at 1 made R10 the most-fired rule in the book and took the holdout refer rate to 50% | 4 | 1 | live |
| R11 | Any fatal crash in the 24-month window | D21 declines a fatal *plus* another crash; a fatal on its own reached no rule at all before 2026-09-10 | 1 | 0 | live |
| R12 | Limit above the $1m base (i.e. $2m) | Offered, but ILF(2m) = 1.058 against a market 1.3–1.5 (G13): price the excess by hand rather than bind a known-thin tail | 0 | 0 | live |
| R13 | Limit inside the writable band but not one of the three offered ($900k, $1,000,001) | Almost always a data-entry error, not a coverage request. Priced at the limit submitted and put in front of a human — hard-declining a good submission over a stray digit is the wrong answer to "sensible handling of bad inputs" | 0 | 0 | live |

Reading the real draw: the 11 declines are all status / authority (D02, D03, D05, D25) or driver OOS (D22); the 18 refers are almost entirely new applicants waiting on an insurance filing (R07 16, R09 6, R01 6), plus one adverse crash record (R10). No real carrier errored, and none was declined for thin data.

**Rules that cannot fire on live data today** — say these before they are found: D24 (BASIC percentiles are "Not Public", G7), R06 (chameleon, a stub, G6), D23 (reads a self-declared field until L&I is automated, G10). D20 was a fourth until 2026-09-10, when it turned out to be testing a statistic that could not reach its own threshold (G24).

---

## 6. Book check

Command: `python -m rater.book <folder or file> [...] [--csv out.csv] [--jsonl out.jsonl]`. Multiple folders can be given in one call, so the reviewers' submissions run alongside ours: `python -m rater.book samples/submissions samples/submissions_real their_folder`.

A file may hold **one** submission (JSON object) or **many** — a JSON array, a `.jsonl` feed, or a `.csv` with one row per carrier (header spellings go through the same alias table, so `dot_number,power_units,radius_miles,cargo,state` works). Each carrier becomes its own result row, tagged `<file>#<i>`. `python -m rater <folder>` runs the book check too.

Output blocks: counts (priced / referred / declined / errored), decline and refer rate, minimum-premium count; premium distribution min / p25 / median / p75 / max for total policy and per power unit; rules fired histogram; errored submissions with reason; one line per submission (file, DOT, decision, premium, rules).

Results, offline, run 2026-09-10 (`data/derived/book_check*.csv`; figures move slightly with run date, G17):

| Set | n | Priced | Referred | Declined | Errored | Decline rate | Policy premium min / median / max | At floor |
|---|---|---|---|---|---|---|---|---|
| Synthetic adversarial (one carrier per rule + 6 edge cases) | 31 | 12 | 5 | 13 | 1 (not JSON, by design) | 41.9% | $8,250 / $19,356 / $87,520 | 9 |
| Real, stratified census draw (15 each < 1 y / 1–3 y / 3 y+ authority, ten focus states) | 45 | 16 | 18 | 11 | 0 | 24.4% (refer 40.0%) | $8,250 / $13,803 / $76,583 | 5 |
| **Cold-start holdout, tracks A + B** (`samples/submissions_holdout`) — 19 states, none of the original ten | 30 | 12 | 8 | 10 | 0 | 33.3% (refer 26.7%) | $8,250 / $14,142 / $40,250 | 6 |
| **Operating draw, track C** (`samples/submissions_operating`) — active authority **and** BI/PD on file | 38 | 37 | 0 | 1 | 0 | 2.6% | $8,250 / $10,666 / $45,534 | 15 |
| **Curveball inputs** (`samples/submissions_curveball`) — 14 carriers in 6 files | 14 | 2 | 1 | 9 | 2 (by design) | n/a — see below | $8,250 / $21,572 / $24,250 | 4 |
| Market-benchmark mirrors (`samples/submissions_benchmark`) | 10 | 9 | 1 | 0 | 0 | 0% | per unit $8,000–$19,731; median gap to the observed liability-only estimate **+2.8%**, to the published figure −5.1% (was −1.2% before the 2026-09-10 credibility correction) | 3 |
| Reviewer formats (`samples/reviewer_formats`) — 16 carriers in 9 files, 4 container shapes | 16 | 12 | 3 | 0 | 1 (not JSON, by design) | 0% | $8,250 / $10,313 / $118,561 | 3 |

Figures regenerated 2026-09-10 after the crash-rule, floor and credibility fixes (G24–G27). **Decline rates did not move on any set** — those fixes changed what gets *referred* and what a surcharged risk *pays*, not the appetite. Refer rates rose a little (real 37.8% → 40.0%, holdout 23.3% → 26.7%) and written prices rose modestly (real per-unit median $11,808 → $12,655) because the credibility off-balance correction removed a systematic ~4% discount and the floor no longer absorbs surcharges.

The synthetic decline rate is high by construction (one carrier per decline rule). The real draw is the answer to "what book does this attract": a quarter declined on status, over a third referred as pending applicants, the rest priced between the $8k floor and about $16k per unit.

### 6.1 Cold start — carriers the rules were not written on

The rules in section 5 were tuned on the 45-carrier census draw, so that draw cannot also be the evidence that they generalise. Three further tracks were sourced afterwards, each excluding every DOT already in `data/cache/carrier/` or any `samples/` folder, and tracks A and B also excluding the ten focus states the original draw used. Build with `python -m analysis.build_holdout_set` and `python -m analysis.build_operating_set` (census + webKey); the resulting submissions and their enrichment are committed, so the book checks re-run offline.

| Track | What it tests | Result |
|---|---|---|
| **A** — 18 carriers, unit counts only, no VINs | The common case: a DOT, a fleet size, no vehicle identity | 5 price / 7 refer / 6 decline |
| **B** — 12 carriers, their own real VINs from the MCMIS crash file | The vPIC decode path on VINs never seen before | 7 price / 1 refer / 4 decline |
| **C** — 38 carriers filtered to *operating* | Whether the decline rate is a property of the book or of the sampling frame | 37 price / 1 decline |

**The track C finding is the one to volunteer.** The census `authorized_for_hire` flag is self-declared on the MCS-150 and goes stale, so a random census draw over-samples dormant shells no broker would ever submit. Applying track C's operating test — `common_authority_status == 'A'` (or contract authority active) **and** `bipd_insurance_on_file > 0` — to the original 45-carrier draw keeps only **23 of 45 (51%)**. Half of that draw is dormant. So the headline 24.4% decline rate is substantially a sampling artifact: on carriers that look like they are actually trading, the rater declines 1 in 38 (2.6%) and prices the rest at a median $9,943 per unit. Both numbers are honest; they answer different questions, and the operating figure is the one that predicts a real submission flow. See G22.

Twelve rules fire across the holdout tracks (R07 10, D25 6, R04 3, R01 3, D11 2, R09 2, D02 2, D03 2, D05 1, D22 1, R10 1, R11 1) — including **D11**, which had fired only on the synthetic set and never on a real carrier before, and R10 / R11, the crash rules added on 2026-09-10 (G24), which each caught one holdout carrier on their first run.

`samples/submissions_curveball/` is the presentation-day rehearsal: real holdout DOTs arriving in Corgi's shape rather than ours — a broker CSV with `DOT Number` / `# Trucks` / `Radius (mi)` headers, commas in numbers, `"1M"` as a limit, full state names; a doubly-nested `{"carrier": {...}}` array with a float DOT and `"USDOT 3989969"` as free text; a `.jsonl` feed containing an unparseable line, a negative unit count, `"drivers": "three"` and `"radius": "banana"`; a file whose VIN list and `power_units` disagree; and two empty files. 14 rows out of 6 files: 2 price, 1 refer, 9 decline (3 of them D01 on rows with no resolvable DOT, by design), 2 error rows, and one file reported as **read only in part** — the partial-read surfacing added in `rater/book.py`. Nothing crashes and no bad row is silently dropped.

`samples/reviewer_formats/` is the generalisation demo: the same cached carriers arriving as a spreadsheet export with a float DOT and a full state name, a broker's JSON array, an agency `.jsonl`, a CSV of DOTs, a wrapped `{"carrier": {...}}` object, a DOT on its own, a submission of nothing but nulls and junk keys, and one deliberately corrupt file. 14 price, the fake DOT refers on R02, the corrupt file is one error row, nothing crashes.

---

## 7. Reproducible pipeline

| Step | Command | Needs | Writes |
|---|---|---|---|
| Everything, offline | `python run_all.py` (or `./run_all.sh`) | nothing beyond `pip install -r requirements.txt` | samples, `docs/RATING_MANUAL.md`, `data/derived/{ilf_table,tornado,market_benchmark,book_check*}.csv`, test run. Runs all seven book checks: synthetic, market benchmark, reviewer formats, cold-start holdout, operating draw, curveball inputs, real census draw |
| Single submission | `python -m rater file.json` | webKey for an uncached DOT | stdout |
| Book check | `python -m rater.book folders... --csv --jsonl` | as above | stdout, CSV, JSONL |
| Frequency tables and GLM | `python -m analysis.build_frequency_tables --years 3` | `data/raw/census.csv`, `crash_2023..2026.csv` (SOURCES S3/S4 URLs; ~1 GB; gitignored) | `data/derived/crash_rate_by_segment.csv`, `crash_rate_by_state.csv`, `glm_relativities*.csv` |
| Real-carrier draw | `python -m analysis.build_sample_set --n 45` | census.csv + webKey | `samples/submissions_real/`, `data/cache/carrier/` |
| Cold-start holdout draw (tracks A + B, G23) | `python -m analysis.build_holdout_set` | census.csv + webKey | `samples/submissions_holdout/` (30), carrier + VIN cache |
| Operating draw (track C, G22) | `python -m analysis.build_operating_set` | census.csv + webKey | `samples/submissions_operating/` (38); prints the operating keep rate |
| Curveball inputs | `python samples/make_curveball_samples.py` | `samples/submissions_holdout/` | `samples/submissions_curveball/` (6 files, 4 container shapes) |
| Slim census (clean-clone parity, G20) | `python -m analysis.build_census_slim` | `data/raw/census.csv` | `data/census_slim.csv.gz` (19.3 MB, committed) |
| Severity / ILFs | `python -m analysis.fit_severity` | — | `ilf_table.csv` |
| Tornado | `python -m analysis.sensitivity [submission]` | — | `tornado.csv` |
| Synthetic backtest | `python -m analysis.synthetic_backtest --policies 20000` | — | stdout |
| Portfolio / capital | `python -m analysis.portfolio` | — | stdout |
| Manual | `python -m analysis.render_manual` | — | `docs/RATING_MANUAL.md` |
| Tests | `python -m pytest -q tests` | — | 32 tests |

Archived evidence committed in the repo: `data/raw/qcmobile_samples/` (all six endpoints for three DOTs plus a not-found DOT), `data/raw/vpic_sample.json`, `data/raw/census_readme.txt`, `data/raw/crash_data_dictionary.pdf`, `data/cache/carrier/` (53 live records), `data/cache/vin/`. Everything else is referenced by URL and pull date in `docs/SOURCES.md`.

Judgment calls: `docs/RATIONALE.md` §5 numbers them A1–A13 with value, basis, tag and one-at-a-time price impact; `config/rates.yaml` carries the same tags inline.

---

## 8. Bonus items

| Topic | Status | Where |
|---|---|---|
| Trends | Partial: severity trend 6% p.a. × 1.5 years [B] from ATRI settlement / verdict / premium series; no frequency trend by year yet (G12) | rates.yaml A8, RATIONALE §5, DEFEND §5.1 |
| Physical damage (comp / collision) | Design only (G11): vPIC year / make → stated value via depreciation table; comp and collision as % of value with vehicle-age and radius relativities; deductible credits | DEFEND §5.2 |
| Multi-limit pricing | Done: the rater prices any submitted limit through the limited mean; ILF table for $250k–$5m from the mixture vs a single lognormal; thinness at $2m+ flagged | `analysis/fit_severity.py`, `data/derived/ilf_table.csv`, RATIONALE §6 |
| Market comparison | Done for observed quotes: ten 2025–26 price points, before / after tables, three calibration changes applied; SERFF filings not pulled (G8) | `docs/MARKET_BENCHMARK.md`, `samples/submissions_benchmark/` |
| Margin / capital story | Done: 1,000-policy aggregate loss simulation → LR 0.52, 1-in-200 $18.1m, capital 25% of premium, ROC 27.9%; 20k-policy backtest confirms the plumbing; the 2k-policy volatility finding | `analysis/portfolio.py`, `analysis/synthetic_backtest.py`, DEFEND §5.5 |

---

## 9. Analysis scripts and derived tables

| Script | Input | Output | Used for |
|---|---|---|---|
| `analysis/build_frequency_tables.py` | census.csv, crash_*.csv | `crash_rate_by_segment.csv` (fleet × authority age: rate, SE, fatal / injury shares), `crash_rate_by_state.csv`, `glm_relativities.csv` (NB GLM, log unit-year offset, reference 2–5 units / 3 y+ / CA), `glm_relativities_operating.csv`, `proposed_venue_state.csv`, `authority_age_diagnostics.txt` | A1 crash rate 0.045 [E]; A7 severity shares [E]; the rejected authority-age and venue proposals (FREQUENCY_PROPOSAL) |
| `analysis/build_sample_set.py` | census.csv, webKey | `samples/submissions_real/`, carrier cache | Real-carrier book check |
| `analysis/build_holdout_set.py` | census.csv, crash_*.csv, webKey | `samples/submissions_holdout/` (18 track A + 12 track B), carrier + VIN cache | Cold-start book check on carriers and states the rules were not built on (G23) |
| `analysis/build_operating_set.py` | census.csv, webKey | `samples/submissions_operating/` (38); keep rate on stdout | Separating dormancy from appetite in the decline rate (G22) |
| `analysis/build_census_slim.py` | census.csv | `data/census_slim.csv.gz` | Registration dates on a machine without the 731 MB census (G20) |
| `analysis/fit_severity.py` | rates.yaml | `ilf_table.csv` | Multi-limit; tail diagnostics |
| `analysis/sensitivity.py` | rates.yaml, a submission | `tornado.csv` | "Where is it most likely wrong" |
| `analysis/synthetic_backtest.py` | rates.yaml | stdout | Pipeline sanity (simulated LR = rate-implied LR) |
| `analysis/portfolio.py` | rates.yaml | stdout | Capital and return |
| `analysis/render_manual.py` | rates.yaml | `docs/RATING_MANUAL.md` | Manual == code |
| `samples/make_synthetic_samples.py` | — | 25 carriers + 6 edge cases with fixtures | Adversarial book check |
| `samples/make_curveball_samples.py` | `samples/submissions_holdout/` | 6 files, 14 rows: broker CSV, nested array, jsonl with an unparseable line, VIN/count conflict, 2 empty files | Presentation-day input shapes; exercises partial-read reporting |
| `samples/make_benchmark_samples.py [--run]` | MARKET_BENCHMARK profiles | 10 mirrors; `market_benchmark.csv` | Market comparison |
