# Defend — the 45–60 minute walkthrough

Structure follows the brief's four questions, then the bonus topics, anticipated challenges, a demo script, and the open research list. Sections marked **[TO RESEARCH]** are deliberately blank or thin: they are the facts still to pull before the session.

**Opening line (3 min):** "Submission in, one of three decisions out. Enrichment from FMCSA and NHTSA, a segment crash rate from the census and crash files, credibility-weighted for the carrier's own record, relativities on top, gross-up, floor. Every number is in one YAML file and the manual is rendered from it."

---

## 1. Method: sources, mental model, process

### 1.1 Problem framing

The brief asks for a *system*: any conforming submission → bindable price or defensible decline, judged on unseen carriers. Three consequences shaped everything:

- **The public record is the underwriting file.** A 1–5 unit carrier has no loss runs worth reading and no MVRs we can pull without consent. What exists publicly is the FMCSA record (registration, authority, inspections, out-of-service rates, crashes, safety rating) and the vehicle identity from the VIN. The rater is built to extract everything those carry and to be honest about what they do not (drivers).
- **Thin data must not become a decline.** Half the segment is under three years old. A rater that declines every new registration declines the market, so the decision is three-way: price, refer (priced, human looks), decline.
- **Selection is where the margin is.** Industry commercial auto has run above 100% combined for most of a decade, and small fleets are the worst of it. The decline list and the new-venture treatment carry more of the profit story than the base rate.

### 1.2 Mental model

```
premium per policy = Σ_units  max( floor ,  base loss cost × relativities × credibility × (1 + ALAE) ÷ (1 − expense − reinsurance − profit) )  + fee

base loss cost / power-unit-year = crash rate (census × crash file, [E]) × claims per crash ([S]) × limited severity at limit (mixture, Monte Carlo) × trend
```

- **Exposure base: power-unit-year.** Market convention, verifiable against the census, collectable in a 60-second form, not gameable downward (fewer declared units than census → D31). Alternatives in §1.4.
- **Frequency** is DOT-recordable crashes per unit-year for the segment, measured with a real denominator (every active for-hire interstate carrier with 1–5 units, 394,864 of them) and numerator (three years of the MCMIS crash file, federally recordable rows). Converted to liability claims by a claims-per-crash ratio. Only the product is identified; the ratio is the single most price-moving assumption.
- **Severity** is a three-part mixture on the flags the crash file does carry: property-damage-only (lognormal, mean $18k), injury (lognormal, mean $140k, CV 2.5), fatal (Pareto above $250k, α 1.6). Limited at the policy limit numerically, so any limit prices consistently.
- **Carrier's own experience** enters through Bühlmann credibility, Z = n/(n+25) with n = units × 2 years. A one-truck carrier with one crash gets Z ≈ 0.07 and about a 21% surcharge. Single crashes on tiny fleets are mostly noise and the model says so, so the crash *rules* gate on the raw count instead: R10 refers a second crash in the window, D20 declines a third at > 4× segment. Two corrections on 2026-09-10 sit behind that wording — the relativity is now off-balanced (it averaged 0.958, a systematic discount) and the minimum premium is scaled by it, because a flat floor used to erase the surcharge entirely. RATIONALE §4.
- **Relativities** are multiplicative and tagged. Authority age is the largest (new venture 1.65), then venue (1.35 high), radius (1.30 long haul), then OOS ratios, driver/unit ratio, vehicle age, commodity, MCS-150 staleness, mileage. Two stacking controls came out of the market benchmark: authority × venue × radius capped at 2.0, and mileage intensity skipped when radius is already long haul.
- **Gross-up and floor.** 14% ALAE, 22% expense, 6% reinsurance, 7% profit / cost of capital → 65% permissible loss + ALAE ratio. Floor $8,000 per unit, set from every 2025–26 published figure for a clean one-truck liability policy. The floor binds for roughly half of a clean synthetic book: for clean established owner-operators the market floor, not the model, sets the price. Say this before they find it.

### 1.3 Sources: what was used, what each fed, what was distrusted

Have `docs/SOURCES.md` open. The core is S3 + S4: a denominator and a numerator, which turns the frequency anchor from a remembered benchmark into an estimate with a standard error.

| Source | Used for | Notes |
|---|---|---|
| S1 FMCSA QCMobile API | Runtime enrichment: carrier record, BASICs, authority, operation classification, dockets | Schema verified live; raw responses archived. Unknown DOT is HTTP 200 with null content. Property-carrier BASIC percentiles are "Not Public" (all 53 live carriers). addDate, MCS-150 and HM/PC flags are absent and come from the census snapshot |
| S3 FMCSA census (SMS input, 2.1M rows) | Denominator; registration date; MCS-150 mileage; sample draw | Pulled 2026-09-09 via Socrata. Cannot distinguish registered from operating, which is why the GLM's authority-age relativity was rejected |
| S4 MCMIS crash file 2023–2026 (648k rows) | Numerator; severity flag shares; state frequencies | ~20% of rows carry no DOT and drop out; last ~3 months under-reported; both handled as a gross-up and a range |
| S8 NHTSA vPIC | Vehicle year, class, body; trailer / pickup detection (D30) | Verified live; decode gated on fatal error codes |
| S15 49 CFR 387.9 | $750k federal minimum; $1m as the shipper standard | Confirmed by the API's `bipdRequiredAmount` |
| S16 ten observed 2025–26 price points | Floor $8k, stack cap, mileage skip; claims-per-crash back-out | Insurer-published and trade-press only; Reddit and lead-gen sites excluded |
| S11/S12 ATRI (via trade press) | Severity trend 6%; per-mile premium anchors | PDFs not yet archived → §8 |
| S14 SERFF filings | Intended for relativity structure | **Not pulled** → §8 |

What I did **not** trust: national OOS averages for small carriers (2009–10 figures in the API; live small carriers average three times higher); headline "average truck insurance cost" numbers that bundle physical damage and cargo; any single vendor figure; the census GLM's authority-age and venue coefficients (they measure dormancy and domicile-state frequency, not risk and legal venue).

### 1.4 Exposure base: alternatives considered

| Base | For | Against | Used as |
|---|---|---|---|
| Power-unit-year | Market standard; verifiable vs census; not gameable down | Ignores utilisation | **Base** |
| Mileage (MCS-150) | Closest to true exposure | Self-reported, stale, per fleet not per truck; placeholders (1, 2, 30 miles) seen on 6 of 45 real carriers | Relativity, discounted; skipped on long haul |
| Revenue | Correlates with contract exposure | Unverifiable for a two-truck company | Not used |
| Drivers | Loss is driver loss | Turnover; not what is insured | Ratio relativity |

### 1.5 Process: how it was built (from the commit history, 2026-09-09 → 10)

1. **Baseline** (`87f899d`): pipeline skeleton, config-driven manual, synthetic adversarial sample (one carrier per rule), tests that assert never-crash and manual == code. Numbers were remembered benchmarks, all tagged [S]/[B] with VERIFY markers.
2. **Bulk data first** (`a4dfc3e`): census and three years of crash files pulled by Socrata; frequency tables by fleet size × authority age × state; negative-binomial GLM with a unit-year offset. Written up as *proposals*, not applied.
3. **Live API verification** (`4a0a55b`): every QCMobile endpoint hit for three DOTs plus a not-found DOT; parser rewritten to the real field names; census fallback for fields the API lacks; inactive-registration rules (D05) from a real case where `allowedToOperate` said Y and `statusCode` said I.
4. **Real sample** (`4a6ea1d`): 45 carriers drawn stratified from the census, enriched, book-checked. This is what turned the rules from a list into a defensible list.
5. **Rules refined on what the real draw showed** (`2a5c072`): D12 needs positive evidence (empty classification is a new registration, not a private carrier); D25 separates a lapsed authority from a pending applicant; R09 refers unknown classification; mileage placeholders no longer earn a low-mileage discount.
6. **VIN edge cases** (`dd768e6`): live vPIC strings; a garbage VIN still returns a Make, so "decoded" is gated on error codes.
7. **Market benchmark** (`20a6917`): ten observed price points; three calibration changes (floor $8k, stack cap 2.0, mileage skip); gaps before and after recorded.
8. **Re-basing on data** (`eaa851b`): crash rate 0.0625 [S/B] → 0.045 [E]; claims per crash 1.2 → 2.0 [S] chosen so the product stays inside the market back-out; severity shares from crash flags [E]. Base loss cost moved −1.4%.
9. **Honesty passes** (`dd6de6f`, `94b4343`, `90c1cce`): BASIC factors marked dormant; trend cut from 8% to 6% because 8% sat above every published series; stale VERIFY markers retired.
10. **Packaging** (2026-09-10): input aliases so unseen file formats run; caches committed so a fresh clone reproduces; cross-platform runner; these two documents.
11. **Cold start** (`e9692a8`, `0162245`): the rules had been tuned on the 45-carrier draw, so a fresh 68 carriers were sourced across three tracks — none previously cached, tracks A and B from 19 states the original draw never touched — plus a curveball folder in the file shapes a broker actually sends. Run once, no retuning. It is what turned "it generalises" from a design claim into a measurement, and it produced the dormancy finding in §2.1.

Tools: Python (pandas, numpy, scipy, statsmodels for the NB GLM), seeded Monte Carlo for limited severity and the portfolio, Socrata SODA for the bulk pulls, QCMobile and vPIC REST, pytest. Claude Code was used as the build assistant; the prompts that drove each live-data step are archived in `docs/CLAUDE_CODE_PROMPTS.md` with their status, so the process is inspectable.

---

## 2. If this went live tomorrow: what book, and would it make money?

### 2.1 The book it attracts

From the 45-carrier census draw (`data/derived/book_check_real.csv`, regenerated 2026-09-10): 16 priced, 18 referred, 11 declined.

- **Priced:** small, mostly newer general-freight carriers in mid-venue states, $8k–$18k per unit; clean established owner-operators at the $8k floor (bottom of the published $7.5k–$11k range); median written policy ≈ $13.8k, median written unit premium $12,655.
- **Referred (40%):** almost entirely new applicants waiting on a BMC-91 insurance filing (R07, R09, R01). That is the front door of this market: they cannot get authority until an insurer files. They are priced with the 1.65 new-venture factor and the stack cap holds a first-year Texas long-hauler to about $13k against a published $8k–$20k band.
- **Declined (24%):** status and authority (inactive registration, OOS order, lapsed authority with no filing) and driver OOS three times the segment. Nothing declined for thin data.
- **Where the market beats us:** high-venue long-haul new ventures and 20-year-old iron with two drivers (P3 in the benchmark, +17%). That is fine; we do not want them at our price.

**Volunteer the sampling caveat before they find it.** The 24% decline rate is partly an artifact of how the sample was drawn. The census `authorized_for_hire` flag is self-declared on the MCS-150 and goes stale, so a random census draw over-samples dormant shells no broker would ever submit. Of the 45 drawn carriers, only **23 (51%)** have active for-hire authority *and* BI/PD insurance on file. `analysis/build_operating_set.py` re-draws the same segment with that operating test applied, and on those 38 carriers the rater declines **1 (2.6%)** and prices 37 at a median $9,038 per unit (`book_check_operating.csv`). Both numbers are true and they answer different questions: 24% is what a census draw declines, 2.6% is what a submission flow declines, and the gap is dormancy, not appetite. The honest planning number for a real quote flow is nearer the second.

### 2.1a Cold start: it was tested on carriers it was not built on

The decline and refer rules were tuned on that 45-carrier draw, so that draw cannot also be the evidence that they generalise. Three further tracks were sourced afterwards — 68 carriers in total, every one excluded from `data/cache/carrier/` and every `samples/` folder at draw time, and tracks A and B drawn from 19 states outside the original ten. **No rule was changed after seeing the results.**

| Track | n | What it tests | Price / refer / decline |
|---|---|---|---|
| A — unit counts, no VINs | 18 | The common case: a DOT and a fleet size, no vehicle identity | 5 / 7 / 6 |
| B — carriers' own real VINs from the crash file | 12 | The vPIC decode path on VINs never seen before | 7 / 1 / 4 |
| C — filtered to operating carriers | 38 | Whether the decline rate is a property of the book or the sampling frame | 37 / 0 / 1 |

Holdout tracks A+B: 12 priced, 8 referred, 10 declined, **0 errors**, median policy $14,142, twelve rules firing (R07 10, D25 6, R04 3, R01 3, D11 2, R09 2, D02 2, D03 2, D05 1, D22 1, R10 1, R11 1). D11 (out-of-appetite commodity) fired on a real carrier for the first time. The premium distribution holds its shape on unseen geography — median $11,181 per unit against $12,655 on the tuning draw — which is the claim worth making: this is a rater, not a lookup table for 45 carriers.

`samples/submissions_curveball/` is the presentation-day rehearsal: real holdout DOTs in Corgi's file shapes rather than ours — a broker CSV with `DOT Number` / `# Trucks` / `Radius (mi)` headers, commas in numbers, `"1M"` limits and full state names; a nested `{"carrier": {...}}` array with a float DOT and `"USDOT 3989969"` as free text; a `.jsonl` feed with an unparseable line, a negative unit count, `"drivers": "three"` and `"radius": "banana"`; a file whose VIN list contradicts `power_units`; two empty files. 14 rows from 6 files: 2 price, 1 refer, 9 decline (3 of them D01 on rows with no resolvable DOT), 2 error rows with reasons, and one file reported as *read only in part*. Nothing crashes; no bad row is silently dropped. **If they hand you a file at the table, this is the rehearsal for it.**

### 2.2 Would it make money?

Only if selection works. `analysis/portfolio.py`: 1,000 policies, 2,950 unit-years → premium $23.6m, expected loss $12.2m (loss ratio 0.52, below the 57% permissible pure loss ratio because the floor binds), 1-in-200 aggregate $18.1m, capital (1-in-200 minus mean) $5.9m = 25% of premium, profit load $1.65m → return on capital ≈ 28%. The 20k-policy synthetic backtest reproduces the rate-implied loss ratio (0.464 vs 0.473), so the plumbing is sound; at 2,000 policies the same simulation swings ±10 loss-ratio points on a handful of limit losses, which is the honest volatility of a small book.

All of it is conditional on the claim-frequency anchor: crash rate (now estimated, SE 0.0003) × claims per crash (selected at 2.0 inside a 1.2–3.4 market back-out). At 3.4 the reference carrier is $9k dearer and the loss ratio story breaks.

**Adverse selection is the real question.** An instant-quote entrant sees new ventures and carriers other insurers dropped. The metric: census share of < 1-year carriers vs our quote and bind mix, weekly. If < 1-year carriers exceed their census share by 2×, the new-venture factor is too low.

---

## 3. Where it is most likely wrong, and what to watch in force

Ranking (have the tornado up, `data/derived/tornado.csv`, reference carrier new venture / GA / long haul / one unit, $13,059):

| Rank | Assumption | Swing on reference carrier | Why it is uncertain |
|---|---|---|---|
| 1 | Claims per recordable crash (2.0) | −$4.8k / +$9.0k over [1.2, 3.4] | Selected, not observed; only the product with crash rate is identified |
| 2 | Segment crash rate (0.045) | −$2.6k / +$2.8k over [0.036, 0.055] | Estimated; range is unmatched-DOT gross-up and reporting lag |
| 3 | Injury mean severity ($140k) | −$2.1k / +$2.9k over [$90k, $220k] | ATRI small-case figures via trade press |
| 4 | Fatal share of claims (1.35%) | −$0.8k / +$2.4k over [0.8%, 3%] | Crash-file share ÷ claims per crash |
| 5 | Expense ratio (22%) | −$0.9k / +$1.8k over [17%, 30%] | Corgi thesis vs 28–30% incumbent |
| 6 | Severity trend (6%) | −$0.5k / +$1.5k over [3%, 14%] | Published series 3.9–6.4% |
| 7 | Fatal tail α (1.6) | +$0.2k / −$0.3k | Truncated by the $1m limit; becomes the risk at $2m+ |

New-venture factor, high-venue factor and the floor show zero swing on this carrier because the stack cap binds and the technical premium sits above the floor; their uncapped swings are ±$2.2k and ±$1.6k (RATIONALE §5).

Weak points in order, with what to watch:

1. **No driver data.** Small-fleet loss is driver loss; we see a count and whatever the submission declares. Watch: nothing we can, until MVR + PSP pulls at bind (first in-force addition).
2. **Crash → claim conversion.** Watch claims per recordable crash on the bound book from month one; compare to 2.0 quarterly.
3. **Severity tail and venue.** ILFs are thin (1.058 at $2m vs market 1.3–1.5). Watch large-loss emergence by state; any $500k+ claim in year one is a data point that moves α.
4. **Self-reported MCS-150 fields.** Cross-checked against VIN count and inspections, but a carrier that never gets inspected is invisible. Watch inspection and MCS-150 update behaviour post-bind.
5. **Adverse selection.** Quote-to-bind mix by authority-age bucket, weekly, against the census share.
6. **Insurance-cancellation signal** is self-declared. Watch insurance-filing churn on L&I; automate before go-live.
7. **Segment OOS averages** are stale, so D22 probably fires too often. Watch D22's share of declines once the inspection file is in.

---

## 4. How this improves

Sequenced by value per day of work:

1. **L&I automation** (S6): authority grant date replaces the registration date as authority age; cancellation history replaces the self-declared field; enables the chameleon flag.
2. **Inspection file** (S5): true small-carrier OOS averages; re-tune D22 and the OOS bands.
3. **SERFF filings** (S14): check every relativity against how Progressive, Sentry, Great West and Canal structure the same problem; fix anything more than 20% apart or explain why.
4. **MVR + PSP at bind**: driver factors with real content; today's driver-experience band is the placeholder.
5. **Claims-per-crash and severity from the bound book**: the two [S] halves of the anchor become [E] after 12 months.
6. **Solo-fleet relativity 1.18 [E]** (proposed, not applied) and a tenure credit beyond three years (watch-list).
7. **Physical damage** on vPIC stated value; **telematics discount**; **price elasticity by segment** for the retention model.
8. **Re-fit everything** on 12 months of quote-to-bind and claims data.

---

## 5. Bonus topics

### 5.1 Trends

Severity trend 6% p.a. applied for 1.5 years (trend factor 1.091), tagged [B]: ATRI serious-case settlements +5.7% p.a., median nuclear verdict ≈ +4.6% p.a. 2013–22, liability premium trend +3.9% (2025) and +6.4% (Q1-2026). 8% was above every published series, so it was cut. Frequency trend is not applied: Land Line / CCJ report crash rates falling while premiums rise, and the crash file could confirm this by year (G12). The market benchmark also indexes observed 2024–25 quotes to the 2026-09 effective date with the ATRI premium trend, which shifts the comparison about 5 points cheaper for us.

### 5.2 Physical damage (design, not built)

Stated value per unit from vPIC year / make / model through a depreciation table (config); comp and collision rates as a percentage of value with vehicle-age and radius relativities; deductible credits; exposed as `price_physdam(submission)` and a `--with-pd` flag on the book check. Watch-list evidence: vehicle age matters more for physical damage than for third-party liability, which is why the 1.20 liability factor on 20-year trucks is on the watch list rather than raised. Data need: a used-tractor value curve (auction indices) and comp / collision loss costs by age, neither public in the way FMCSA data is. **[TO RESEARCH]** value curve and rate anchors.

### 5.3 Multi-limit pricing

The rater prices whatever limit is submitted through the limited mean of the mixture; ILFs relative to $1m: $750k 0.966, $2m 1.058, $5m 1.094 (`data/derived/ilf_table.csv`). A single lognormal matched to the same mean and CV gives almost the same curve, which says the Pareto tail is too light: market trucking ILFs sit around 1.3–1.5 at $2m. At $1m primary the limit does the truncation and this does not bite; for $2m+ or excess layers the fatal share and α need real severity data. Flagged, not hidden.

### 5.4 Market comparison

`docs/MARKET_BENCHMARK.md`: ten 2025–26 price points (Progressive published averages, Overdrive, FreightWaves, CCJ / ATRI, FleetOwner, Geotab) mirrored as synthetic submissions. After the three calibration changes and the re-basing: median gap −1.2%, 6 of 10 within ±20% of the liability-only estimate, 7 of 10 within ±20% of the published figure. The two largest overshoots (P1, P2) depend on my 70% liability share of Progressive's bundled premium, so they were not tuned further. The honest miss is P6: a five-year, late-model, Indiana, intermediate-radius owner-operator at the $8k floor against a $7.5k–$15k published range.

### 5.5 Margin and capital

§2.2. Independence between policies is assumed; auto liability events are far less correlated than cyber, but severity *trend* is fully correlated across the book and is the systemic risk. Reinsurance at 6% of premium is a placeholder for an excess-of-loss layer above $1m; the 1-in-200 figure is net of the $1m per-claim limit only.

---

## 6. Anticipated challenges

- *"Your decline rate on your own sample is 42%."* The synthetic sample is adversarial by design, one carrier per rule. On the real draw the figure is 24%, and even that is inflated by the sampling frame: only 23 of those 45 (51%) have active authority and BI/PD insurance on file, so half the draw is dormant registrations no broker would send. Re-drawn to carriers that look like they are operating, the decline rate is 1 in 38 (2.6%) (section 2.1). In full: 45 real carriers, 24% declined, 40% referred (almost all pending applicants), 36% priced, none errored.
- *"You tuned the rules on the same 45 carriers you are showing me."* True of the first draw, which is exactly why there is a second. 68 carriers were sourced afterwards across three tracks — none previously cached, tracks A and B from 19 states the original draw never touched — and run once with **no retuning afterwards**: 12 priced, 8 referred, 10 declined, 0 errors, median $11,181 per unit against $12,655 on the tuning draw. Ten rules fired, including D11 on a real carrier for the first time. Section 2.1a.
- *"Show me a carrier with a bad crash record — what does it pay?"* **Volunteer this one before they ask it.** Until 2026-09-10 the answer was embarrassing: a two-truck carrier with twelve crashes in 24 months priced at the clean $8,000-per-unit floor with no rule fired, while a carrier with one fatal and one minor declined on D21. Two separate defects. First, D20 declined on `cred_rate_relativity > 3.0`, but that relativity caps the own rate at 3× and then credibility-weights it, so its ceiling is 1 + 2Z — 1.148 at one unit, **1.571 at five**. The rule could not fire for any carrier in appetite. Second, the minimum premium was applied flat, so any surcharge landing under $8,000 vanished — and the floor binds on about 40% of the operating draw. Both are fixed: D20 now tests the uncapped ratio gated on the raw count, R10 refers a second crash, R11 refers any fatal, and the floor is scaled by the experience relativity when that is a surcharge. Same carrier now declines on D20; a one-truck carrier with one crash pays $9,719 rather than $8,000. Found by asking what the maximum attainable value of a rule's own test statistic was — a question worth asking of every threshold in the file (DELIVERABLES G24, G25).
- *"What is the premium-weighted mean of your experience relativity? Is the credibility procedure balanced?"* It was **0.958** — a systematic 4% discount on 84% of the book — and that was a defect, not a feature. The 3× cap truncates the upside while a crash-free carrier gets `own_rel` = 0 on the downside, so E[cred_rel] < 1 by construction. Since the segment crash rate was measured across all carriers *including* the crash-free majority, the base loss cost already contained them and crediting them again leaked roughly $1m of premium on the $23.6m portfolio, against a $1.65m profit load. The relativity is now divided by its own expectation at that fleet size under Poisson(segment rate), so the procedure is balanced by construction (DELIVERABLES G27, RATIONALE A14).
- *"What happens if we ask for a $2m or $5m limit?"* $750k / $1m / $2m are offered and **`limits.offered` is now enforced**: anything off the list declines on D32, and $2m refers on R12 rather than binding, because ILF(2m) = 1.058 against a market 1.3–1.5 and I am not going to auto-bind a tail I know is thin. Until 2026-09-10 it was not enforced at all and a $5m CSL priced 9.3% above $1m — a bindable mispricing that had been filed as a cosmetic gap. Being wrong about the *severity* of your own known gaps is its own lesson (DELIVERABLES G26).
- *"Your 1-in-200 says you need 25% of premium in capital."* Treat that as a rate-adequacy check, not capital adequacy. It is process risk only: Poisson frequency, independent policies, every policy priced at base with no relativities — so it is not this book — and **no parameter uncertainty**, when the top of my own tornado says claims-per-crash could be 3.4 instead of 2.0, which is +70% on losses and swamps the $5.9m. Fixing it properly means simulating the anchor as a distribution and adding a systemic severity-trend load; it is the first thing I would do to the capital story (RATIONALE §7 item 8).
- *"Your BASIC factors never fire."* Correct: percentiles are "Not Public" for 53 of 53 live property carriers. They are marked dormant in the config; the API does return the measure and the intervention threshold, and a measure-based band is the replacement.
- *"Why refer instead of decline new ventures?"* Half the segment is under three years old; declining them is declining the market. Surcharge, refer, watch the bind mix.
- *"ILFs look thin."* Agreed and flagged. The fatal share or α is light. It is exactly the parameter I would buy data for, and it does not bite at $1m primary.
- *"Why is credibility k = 25?"* Selected so a 5-truck, 2-year record gets Z ≈ 0.29 and a 1-truck record ≈ 0.07. Would fit from crash-file variance components given a day.
- *"You didn't use L&I."* Correct; scraping was the time sink. D23 reads the declared field; L&I is roadmap item 1.
- *"Why 2.0 claims per crash?"* Only the product with the crash rate is identified. Backing claim frequency out of the ten market prices gives 1.2–3.4, median 2.3; industry combined ratios above 100% make those floors; 2.0 keeps the base loss cost within 1.4% of the pre-re-basing value, so the anchor moved onto data without moving prices. It is the top of the tornado and the first thing to measure in force.
- *"The floor binds on most clean risks, so what is the model for?"* The model prices the risks the market disagrees about: new ventures, high venue, long haul, crashes, OOS. For a clean established one-truck carrier the published market floor is the price, and pretending a model can go below it would be adverse selection against ourselves.
- *"What happens when the FMCSA API is down?"* The carrier prices on segment defaults with authority age assumed 0.5 years and is referred (R02). Nothing errors, nothing binds unseen.
- *"What does this do on our machine, not yours?"* The same thing, and that took work. QCMobile returns no `addDate`, so authority age — the largest relativity — comes from the FMCSA census, which is 731 MB and cannot be committed. A clone without it would have assumed every carrier was six months old, applied the 1.65 new-venture factor and referred the book on R01: a different book from the one in these docs. The repo therefore ships `data/census_slim.csv.gz`, the same columns for the 1.95 M carriers with ≤ 6 power units, 19.3 MB, and `rater/enrich.py` indexes it when the full file is absent. A row missing from the slim file is treated as *unknown* rather than "not in the snapshot", so R08 does not misfire on a large carrier.
- *"Will it read the file format we send?"* Object, array, JSONL or CSV; keys through a case-insensitive alias table; a submission nested inside `{"carrier": {...}}` is unwrapped; DOTs as integers, floats, or free text; radius as a band, a number of miles, `"500+ mi"` or `{"miles": 400}`; states as codes or full names; limits as `1000000`, `"1m"`, `"750k"`. Run `python -m rater.book samples/reviewer_formats` — 16 carriers, 9 files, four container shapes, one deliberately corrupt file that reports as a single error row. Every coercion is listed in the result's `flags`, so nothing is assumed silently.
- *"Have you tested it on inputs you didn't write?"* That fuzzing is where the last round of fixes came from, and one was a real bug worth owning: a DOT arriving as `9900001.0` — a spreadsheet export — had its decimal point stripped and became `99000010`, a different and possibly real carrier, with no flag raised. Numbers are now parsed as numbers, digit-extraction from text is flagged, and `test_float_usdot_is_not_a_different_carrier` holds it (gap register G19).
- *"Why $8,000?"* Every 2025–26 published source puts clean established one-truck liability at $7,500 or more; $8k is the bottom of that band. A higher floor would fix P6 and break P2 and P9 in the benchmark.
- *"Why decline private carriers and intrastate?"* Different exposure, different rates, different data; the frequency anchor is for-hire interstate. Note the rule needs positive evidence; an empty classification on a new registration is unknown (R09), not private.
- *"A file with no USDOT is declined, not referred."* By design: the DOT is the carrier's identity and every enrichment hangs off it; a submission without one is not a submission we can underwrite.
- *"The census GLM says new ventures crash less. Why 1.65?"* The census cannot separate registered from operating: 80% of carriers under a year old have never filed mileage, and dropping them moves the 1–3 year relativity from 0.66 to 0.90. The residual is still dormancy and reporting lag. The 1.65 comes from insured-loss experience and SERFF-style new-venture surcharges (1.3–2.0) and is not contradicted by usable public data. **[TO RESEARCH]** confirm the SERFF range.

---

## 7. Live demo script

1. `python -m rater.book samples/submissions_real` — the book: counts, rates, distribution, rules histogram. Point at R07 and D25.
2. `python -m rater samples/submissions_real/4529032.json` — a pending applicant: R07, priced $13k, flags show what was defaulted.
3. `python -m rater samples/submissions/07_fatal_plus_one_tx.json` — a decline with `premium_if_written` still shown.
4. `python -m rater their_carrier.json` — live enrichment with the webKey; show the cached response landing in `data/cache/carrier/`.
5. `python -m rater.book samples/reviewer_formats` — the same carriers arriving as a spreadsheet export, a broker's array, an agency JSONL, a CSV of DOTs and a wrapped object, plus one corrupt file. This is the "runs on submissions you haven't seen" evidence; have it ready **before** they hand anything over.
6. `python -m rater.book samples/submissions their_folder` — their cases alongside ours, whatever shape their file is in.
7. `python -m rater.book samples/submissions_holdout samples/submissions_operating` — the cold-start evidence: 68 carriers in states the rules were never tuned on, run once with no retuning. Use it the moment anyone asks whether this generalises.
8. `python -m rater.book samples/submissions_curveball` — the hostile-input rehearsal: a broker CSV, a nested array, a JSONL with an unparseable line, a VIN/count conflict, two empty files. Point at the *files read only in part* block — the row that could not be parsed is reported, not silently dropped.
9. `config/rates.yaml` open on the loss-cost block; `data/derived/tornado.csv`; `docs/MARKET_BENCHMARK.md` after table.

Slides (8): system picture; scope; data; loss cost; relativities and credibility; rules with counts; sensitivity and validation; where wrong / watch / roadmap (`docs/PRESENTATION_OUTLINE.md`).

---

## 8. Open research items **[TO RESEARCH]**

Each is a fact to pull, where to get it, and what it changes. Leave blank until done; fill in the finding under each heading.

### 8.1 SERFF rate filings (SOURCES S14, Prompt 5)
Pull 2–3 public trucking filings (Progressive County Mutual / Progressive Casualty, Sentry, Great West, Canal, Northland) from a state portal (Texas TDI, Florida OIR, Illinois DOI). Extract exposure base, radius classes and factors, GVW classes, new-venture / years-in-business factors, driver factors, territory factors for TX / FL / GA / LA / CA, minimum premiums. Tabulate against `config/rates.yaml`; flag anything > 20% apart. Changes: A3 new-venture evidence, A5 venue tiers, floor.
*Finding:*

### 8.2 ATRI PDFs (S11, S12)
Verify against the source documents: serious-case settlement trend +5.7% p.a., median nuclear verdict growth 2013–22, small-case severity anchors ($140k injury mean), per-mile insurance cost for ≤25-truck fleets (20.3¢). Changes: A4, A8; retires the VERIFY on A8.
*Finding:*

### 8.3 Large Truck and Bus Crash Facts (S9)
Confirm the injury / fatal shares of police-reported large-truck crashes against the crash-file shares used (34% / 2.7% per recordable crash). Changes: A7.
*Finding:*

### 8.4 Industry combined ratio (S13)
One chart: commercial auto combined ratio by year, 2011–2025 (III / AM Best / NAIC). Supports the "money is in selection" claim and the claims-per-crash floor argument.
*Finding:*

### 8.5 MCMIS inspection file (S5, G9)
Inspection-weighted driver and vehicle OOS rates for 1–5 unit for-hire interstate carriers. Changes: `segment_averages`, D22 threshold, OOS bands. Expected direction: D22 fires less.
*Finding:*

### 8.6 SMS methodology 2025–26 (S7)
Confirm which compliance categories replaced the BASICs, whether any percentile is public for property carriers, and the intervention thresholds returned as `basicsViolationThreshold`. Changes: the replacement measure-based band for the dormant BASIC factors.
*Finding:*

### 8.7 L&I sample (S6)
For ten of the 45 real carriers: authority grant date vs census add date (how wrong is authority age?), insurance history, cancellation reasons. Changes: authority-age feature, D23 automation design.
*Finding:*

### 8.8 Expense ratio 22%
What supports 22% against the 28–30% incumbent ratio: acquisition channel, no agent commission, servicing cost per policy. This is the Corgi thesis; be ready to say what breaks if it is 28%.
*Finding:*

### 8.9 Competitor landscape
Who writes 1–5 unit for-hire liability today (Progressive, Sentry, Great West, Canal, Northland, National Interstate, the MGAs and insurtechs), their appetite statements, and where they are withdrawing. Frames "what book would it attract".
*Finding:*

### 8.10 Physical damage anchors
Used Class 8 tractor value curve by age; comp / collision loss cost benchmarks; typical deductibles. Changes: §5.2 from design to numbers.
*Finding:*
