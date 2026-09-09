# Rationale — Small-Fleet Trucking Primary Auto Liability Rater

**Author:** Sophia · **Status:** v0.1 built offline against synthetic fixtures; all live-data steps flagged VERIFY

## 1. The answer

The system prices for-hire trucking carriers with 1–5 power units for $1m CSL primary auto liability on a **power-unit-year** exposure base, enriched from FMCSA (QCMobile) and NHTSA (vPIC), and returns one of **price / refer / decline** with a full breakdown. At current parameters the base loss cost is **$4,328 per unit-year** (0.0625 crashes × 1.20 claims per crash × $51,419 limited mean × 1.122 trend; the crash-rate anchor is still the selected 0.0625 against 0.036 measured / 0.045 grossed-up from the census × crash file, §5 A1). Written unit premiums run from the **$8,000 floor to ≈$17–18k** (max $17,228 on the real draw, $18,143 on the synthetic sample); the median written unit premium is **≈$12,300 on the real draw** and ≈$9,300 on the synthetic sample. The floor binds for 2 of 34 written real carriers, 8 of 17 written synthetic ones and 75% of the synthetic backtest book — for clean established one-truck risks the floor, not the rate model, sets the price. On the deliberately adversarial 31-submission synthetic sample the book check prints 12 priced / 5 referred / 13 declined / 1 unreadable file. On the 45-carrier stratified census draw (15 each at <1y / 1–3y / 3y+ authority, ten focus states; `analysis/build_sample_set.py` → `data/derived/book_check_real.csv`) it prints **17 priced / 17 referred / 11 declined: decline rate 24.4%, refer rate 37.8%** — declines inside the 15–30% I expected; the refer rate is R07 (no active for-hire authority, 16 carriers) and R09 (classification not yet on file, 6), i.e. new applicants waiting on a BMC-91 filing, not data failures (R02 fired zero times).

Would it make money? Only if selection works. The margin is in the decline list and the new-venture surcharge, not in the base rate: industry commercial auto has run above 100% combined for most of a decade, and the small-fleet segment is where the worst experience sits. Section 6 gives the implied loss ratio (≈54% on the 1,000-policy portfolio, ≈47% on the 20k-policy backtest — both below the 57% permissible pure loss ratio because the floor binds), the 1-in-200 capital (≈26% of premium under independence) and the return on capital (≈27%) — all of which are conditional on the crash-rate anchor in §5 being right.

## 2. Scope and definitions

- **Coverage:** primary auto liability, $1,000,000 combined single limit, occurrence, annual term. Federal minimum is $750k (49 CFR 387.9) but shippers and brokers require $1m; ILFs for $750k / $2m are produced by `analysis/fit_severity.py`.
- **Not priced:** physical damage, cargo, GL, non-trucking liability, hazmat, passenger, HHG, auto-hauler. These route to decline D11 (appetite), not to an error.
- **Segment:** interstate authorised-for-hire property carriers, 1–5 power units, Class 7–8, general freight (dry van / reefer / flatbed and similar). Private carriers and intrastate-only are declined (D12) — they need different data and different pricing. D12 needs positive evidence: a registration under ~60 days old comes back from QCMobile with an empty operation-classification list, and that is treated as unknown (refer R09), not as private. No active MC authority with no BI/PD filing on record refers (R07): a new applicant cannot get authority until an insurer files the BMC-91, so that is what a legitimate prospect looks like at quote time. Authority that was granted and is now inactive, with no filing, is a lapse and declines (D25).
- **Submission schema:** `config/schema.json`. Only `usdot` is required; everything else is coerced, defaulted, and flagged. Defaults are conservative (unknown radius → intermediate, unknown commodity → 1.10).
- **Decision policy:** decline rules are hard; refer rules return a price but flag for human review. Refer is what stops thin-data carriers from being declined wholesale.

## 3. Data and enrichment

| Need | Source | Status |
|---|---|---|
| Carrier record: units, drivers, authority, OOS rates, 24-month crashes, safety rating, MCS-150 date/mileage | FMCSA QCMobile API (cache-first) | Client written; **field names VERIFY** against live response |
| BASIC percentiles (where public) | QCMobile `/basics` | as above |
| Vehicle year, class, body | NHTSA vPIC batch | Client written; VERIFY |
| Population and crash frequency by segment | FMCSA Census + MCMIS Crash files | Script written; **files TO PULL** |
| Insurance cancellations, authority history | FMCSA L&I | Not automated; rule D23 currently reads the submission's declared field |
| Driver records | None public (MVR / PSP are paid, consent-based) | Uses submitted driver fields only — see §7 |

Enrichment never raises. Order: API → disk cache → fixture → segment defaults with `enrichment_degraded=True` (→ refer R02).

## 4. Method

**Exposure base.** Power-unit-year. It is the market convention, verifiable against the census record, collectable in a 60-second form, and not gameable downward (fewer declared units than census → D31). Mileage is self-reported and often stale, so it enters as a discounted relativity; revenue is unverifiable for a two-truck company. Alternatives table in `docs/DEFENCE_NOTES.md`.

**Frequency.** DOT-recordable crashes per power-unit-year for the segment, from census × crash file, via a negative-binomial GLM with `log(unit-years)` offset and factors fleet size / authority age / state (`analysis/build_frequency_tables.py`). Converted to liability claims by a crash-to-claim ratio (1.20: adds non-recordable third-party claims, removes clearly not-at-fault crashes). The crash rate is the single most price-moving assumption (§5) and the one I most want to replace with the estimated value.

**Carrier-own experience.** Bühlmann credibility, Z = n/(n+25) with n = units × 2 years. A one-truck carrier with one crash gets Z ≈ 0.07 and a ~15% surcharge; the decline rule D20 (credibility-weighted rate > 3× segment) can only fire for larger fleets with repeated crashes. This is deliberate: single crashes on tiny fleets are noise.

**Severity.** Three-component mixture on the crash flags the public data does carry — property-damage-only (lognormal, mean $18k), injury (lognormal, mean $140k, CV 2.5), fatality (Pareto above $250k, α = 1.6) — limited at the policy limit by Monte Carlo (`rater/losscost.py`). Limited mean at $1m ≈ $51k. Severity trended at 8% p.a. for 1.5 years (ATRI verdict inflation; VERIFY).

**Relativities.** Multiplicative, product capped to [0.60, 3.25]. Authority age is the largest (new venture 1.65×), then venue state (high 1.35×), radius (long haul 1.30×), then OOS ratios, BASICs, driver/unit ratio, vehicle age, commodity, MCS-150 staleness, mileage intensity. Each is tagged [S] selected or [B] benchmark-anchored in `config/rates.yaml`; the GLM output replaces the first three with [E]. Two stacking controls added 2026-09-09 after the market benchmark (`docs/MARKET_BENCHMARK.md`): the product of authority × venue × radius is capped at 2.0 (uncapped it reached 2.75 on a first-year Texas long-hauler, $20.9k against a published $8–20k band), and mileage intensity is not applied when radius is already long haul (both proxy the same exposure and fired together on 4 of 10 benchmark profiles).

**Gross-up.** Loss cost × (1 + 14% ALAE) ÷ (1 − 22% expense − 6% reinsurance − 7% profit/capital) → technical unit premium; floored at **$8,000 per unit** (raised from $6,500 on 2026-09-09: every 2025–26 published source puts clean established one-truck liability at $7,500 or more, `docs/MARKET_BENCHMARK.md`); + $250 policy fee. The floor binds for roughly half of a synthetic book — for one-truck clean risks the rate model is not what sets the price.

## 5. Numbered assumptions

Impact column: one-at-a-time swing on the reference carrier (new venture, GA, long haul, one unit: **$13,605** with the stack cap binding — authority × venue × radius = 1.65 × 1.35 × 1.30 = 2.90, capped to 2.0), from `analysis/sensitivity.py` → `data/derived/tornado.csv`. Where the cap zeroes a swing, the swing on an uncapped carrier is given instead.

| # | Assumption | Value | Basis | Impact if wrong (ref. carrier $13,605, swing range) |
|---|---|---|---|---|
| A1 | Segment crash rate / unit-yr | 0.0625 | [S/B] LTBCF order of magnitude. Census × crash file (`data/derived/crash_rate_by_segment.csv`) measures **0.0363 (SE 0.0002, 30,775 crashes)** for the base segment (2–5 units, 3y+), 0.0462 for one-unit 3y+, and **0.0452 grossed up** for the 19.8% of recordable crash rows with no DOT; proposed 0.045 [0.036, 0.055], **not yet applied** (`FREQUENCY_PROPOSAL_2026-09-09.md`) | −$4.8k / +$5.9k over [0.04, 0.09] (largest) |
| A2 | Crash → claim ratio | 1.20 | [S] | −$3.3k / +$4.5k over [0.9, 1.6] |
| A3 | New-venture factor (<1 yr) | 1.65 | [S] SERFF new-venture surcharges 1.3–2.0; census GLM gives 0.41–0.60 but that is dormant registrations, not contradicting evidence (FREQUENCY_PROPOSAL §2) | 0 on ref. carrier (stack cap binds); ±$2.3k over [1.3, 2.2] on an uncapped new venture (neutral venue, intermediate radius, $11.3k) |
| A4 | Injury mean severity | $140k | [S/B] ATRI small cases | −$2.6k / +$3.6k over [$90k, $220k] |
| A5 | High-venue factor | 1.35 | [S/B] ATRI verdict geography (severity); census crash *frequency* by domicile puts GA 1.07, TX 1.06, CA 1.00 — a different quantity, not blended | 0 on ref. carrier (stack cap binds); −$1.6k / +$1.6k over [1.15, 1.7] on an established GA long-hauler ($11.4k) |
| A6 | Expense ratio | 22% | [S] Corgi thesis vs ~28–30% incumbent | −$1.0k / +$1.9k over [17%, 30%] |
| A7 | Fatal share of crashes | 1.5% | [B] LTBCF; crash file shows fatal 2.7% and injury 34% of recordable crashes in the base segment (per crash, not per claim — the mixture is per claim) | −$0.9k / +$1.9k over [0.8%, 3%] |
| A8 | Severity trend | 8% p.a. | [B] ATRI | −$0.9k / +$1.1k over [3%, 14%] |
| A9 | Fatal tail α | 1.6 | [S] | +$0.2k / −$0.3k over [1.3, 2.2] — **truncated by the limit; matters at $2m+** |
| A10 | Minimum premium / unit | $8,000 | [B] observed market floor (was $6,500; 2025–26 sources, MARKET_BENCHMARK.md) | 0 on ref. carrier over [$5k, $9k] (technical unit premium $13.4k); binds on 2 of 34 written real carriers, 8 of 17 written synthetic, 75% of the backtest book |
| A13 | Stack cap authority × venue × radius | 2.0 | [S] MARKET_BENCHMARK.md P5 | **binds on ref. carrier: −$6.0k** (uncapped 2.90 → $19.6k, capped → $13.6k) |
| A11 | Credibility k | 25 unit-years | [S] | governs how fast own crashes bite |
| A12 | Segment OOS averages | 6.2% / 21.5% | [B] national averages; VERIFY for small carriers (S5 not pulled) | small |

## 6. Sensitivity, backtest, portfolio

- **Tornado** (`analysis/sensitivity.py` → `data/derived/tornado.csv`, reference carrier $13,605): crash rate (−$4.8k / +$5.9k) ≫ crash→claim (−$3.3k / +$4.5k) > injury severity (−$2.6k / +$3.6k) > expense ratio ≈ fatal share ≈ severity trend (each ≈ −$1k / +$1–2k). Tail α moves the $1m price by +$0.2k / −$0.3k — the limit truncates it. New-venture factor, high-venue factor and the $8k floor all show **zero** swing on this carrier because the stack cap binds (2.90 → 2.0) and the technical unit premium ($13.4k) sits above the floor; their uncapped swings are in §5 (±$2.3k, ±$1.6k). Say this out loud: *at primary $1m the frequency anchor is the risk; the tail becomes the risk at $2m+.*
- **ILFs** (`analysis/fit_severity.py` → `data/derived/ilf_table.csv`): limited mean at $1m $51,419; mixture gives ILF(750k) 0.962, ILF(2m) 1.064, ILF(5m) 1.103 (single lognormal: 0.965 / 1.061 / 1.100). **That is thinner than market trucking ILFs (~1.3–1.5 at $2m)** — a signal that the fatal share or tail is too light. Flagged for calibration, not hidden.
- **Synthetic backtest** (`analysis/synthetic_backtest.py`): 20k policies, 59,862 unit-years, 4,564 claims → simulated pure loss ratio 0.469 vs rate-implied 0.477 — pipeline is sound (>0.02 apart would mean it is broken). 74.8% of policies sit at the minimum premium, which is why both are below the 57% permissible pure loss ratio (65% loss+ALAE ÷ 1.14). At 2k policies it swings ±0.10: a real 2,000-policy book moves 10 LR points on a handful of limit losses.
- **Portfolio** (`analysis/portfolio.py`): 1,000 policies, 2,950 unit-years → premium $23.6m, expected loss $12.8m (LR 0.54); aggregate loss p50 $12.7m, p90 $15.6m, p99 $18.3m, 1-in-200 $18.9m; capital (1-in-200 minus mean) $6.1m = 26% of premium; profit load $1.65m → ROC 27.1%. Independence assumed — auto liability events are far less correlated than cyber, but severity *trend* is fully correlated across the book and is the systemic risk here.

## 7. Where it is most likely wrong, and what to watch in force

1. **No driver data.** Small-fleet trucking loss is mostly driver loss; I only see driver count and whatever the submission declares. First in-force addition: MVR + PSP pulls on bind.
2. **Crash → claim conversion is assumed, not observed.** Watch claims-per-crash on the bound book from month one.
3. **Severity tail and venue** — ILFs look thin (§6). Watch large-loss emergence by state.
4. **Self-reported MCS-150 fields** (units, drivers, mileage). Cross-checked against VIN count and inspection activity, but a carrier that never gets inspected is invisible.
5. **Adverse selection.** An instant-quote entrant sees new ventures and carriers other insurers dropped. Watch quote-to-bind mix by authority-age bucket weekly; if <1-year carriers exceed their census share by 2×, the new-venture factor is too low.
6. **Insurance-cancellation signal** currently comes from the submission, not L&I. Automate L&I before go-live.
7. **Market-benchmark watch list (not applied, evidence too thin — one named renewal each):** a tenure credit above 3 years (authority age gives no credit beyond 3 yrs, so a 39-year carrier prices like a 4-year one); vehicle age 1.20 on 20+ year trucks (old iron matters more for physical damage than third-party loss); and the 8% severity trend against ATRI's 4–6% premium trend (premium lags loss trend, so not evidence of over-trending on its own). Revisit with bound-book data.

## 8. What this attracts, and roadmap

**Book attracted:** small, mostly newer, general-freight carriers in mid-venue states, priced $7–15k per unit; high-venue long-haul new ventures priced ~$15–16k after the stack cap (was $20k+), inside the published $8–20k band; clean established owner-operators at the $8k floor, at the bottom of the published $7.5–11k range. Declines concentrate on authority/status, appetite and data-integrity rules.

**Roadmap:** (1) replace A1/A3/A5 with GLM estimates; (2) L&I automation; (3) MVR/PSP at bind; (4) telematics discount; (5) physical damage using vPIC stated value; (6) re-fit relativities on 12 months of quote-to-bind and claims; (7) price elasticity by segment.
