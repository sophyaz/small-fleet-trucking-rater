# Rationale — Small-Fleet Trucking Primary Auto Liability Rater

**Author:** Sophia · **Status:** v0.1 built offline against synthetic fixtures; all live-data steps flagged VERIFY

## 1. The answer

The system prices for-hire trucking carriers with 1–5 power units for $1m CSL primary auto liability on a **power-unit-year** exposure base, enriched from FMCSA (QCMobile) and NHTSA (vPIC), and returns one of **price / refer / decline** with a full breakdown. At current (unverified) parameters the base loss cost is **≈$5,000 per unit-year**, technical unit premiums run **≈$6,500 (floor) to $24,000**, median ≈$10,000, and the minimum premium binds for roughly 40% of clean small risks. On the deliberately adversarial 31-submission sample the book check prints 12 priced / 5 referred / 13 declined / 1 unreadable file. On a representative census draw I expect a decline rate of 15–30% — **VERIFY with `analysis/build_sample_set.py`**.

Would it make money? Only if selection works. The margin is in the decline list and the new-venture surcharge, not in the base rate: industry commercial auto has run above 100% combined for most of a decade, and the small-fleet segment is where the worst experience sits. Section 6 gives the implied loss ratio (≈57%), the 1-in-200 capital (≈27% of premium under independence) and the return on capital (≈26%) — all of which are conditional on the crash-rate anchor in §5 being right.

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

**Relativities.** Multiplicative, product capped to [0.60, 3.25]. Authority age is the largest (new venture 1.65×), then venue state (high 1.35×), radius (long haul 1.30×), then OOS ratios, BASICs, driver/unit ratio, vehicle age, commodity, MCS-150 staleness, mileage intensity. Each is tagged [S] selected or [B] benchmark-anchored in `config/rates.yaml`; the GLM output replaces the first three with [E].

**Gross-up.** Loss cost × (1 + 14% ALAE) ÷ (1 − 22% expense − 6% reinsurance − 7% profit/capital) → technical unit premium; floored at **$6,500 per unit**; + $250 policy fee. The floor binds for ~40% of a synthetic book — for one-truck clean risks the rate model is not what sets the price.

## 5. Numbered assumptions

| # | Assumption | Value | Basis | Impact if wrong (ref. carrier, new venture GA) |
|---|---|---|---|---|
| A1 | Segment crash rate / unit-yr | 0.0625 | [S/B] LTBCF order of magnitude; **replace with GLM** | ±$7–8.5k on $19.6k (largest) |
| A2 | Crash → claim ratio | 1.20 | [S] | ±$5–6k |
| A3 | New-venture factor (<1 yr) | 1.65 | [S] SERFF new-venture surcharges 1.3–2.0 | ±$4–5k |
| A4 | Injury mean severity | $140k | [S/B] ATRI small cases | ±$4–5k |
| A5 | High-venue factor | 1.35 | [S/B] ATRI verdict geography | ±$3–5k |
| A6 | Expense ratio | 22% | [S] Corgi thesis vs ~28–30% incumbent | ±$1.5–2.7k |
| A7 | Fatal share of crashes | 1.5% | [B] LTBCF | ±$1.3–2.7k |
| A8 | Severity trend | 8% p.a. | [B] ATRI | ±$1.5k |
| A9 | Fatal tail α | 1.6 | [S] | ≈$0.3k at $1m — **truncated by the limit; matters at $2m+** |
| A10 | Minimum premium / unit | $6,500 | [B] observed market floor | 0 on ref. carrier; sets price for ~40% of book |
| A11 | Credibility k | 25 unit-years | [S] | governs how fast own crashes bite |
| A12 | Segment OOS averages | 6.2% / 21.5% | [B] national averages; VERIFY for small carriers | small |

## 6. Sensitivity, backtest, portfolio

- **Tornado** (`analysis/sensitivity.py`): crash rate ≫ crash→claim ≫ new-venture factor ≈ injury severity ≈ venue. Tail α barely moves the $1m price — the limit truncates it. Say this out loud: *at primary $1m the frequency anchor is the risk; the tail becomes the risk at $2m+.*
- **ILFs** (`analysis/fit_severity.py`): mixture gives ILF(2m) ≈ 1.06, ILF(5m) ≈ 1.10. **That is thinner than market trucking ILFs (~1.3–1.5 at $2m)** — a signal that the fatal share or tail is too light. Flagged for calibration, not hidden.
- **Synthetic backtest** (`analysis/synthetic_backtest.py`): at 20k policies the simulated loss ratio matches the rate-implied one (0.53–0.54) — pipeline is sound. At 2k policies it swings ±0.10: a real 2,000-policy book moves 10 LR points on a handful of limit losses.
- **Portfolio** (`analysis/portfolio.py`): 1,000 policies → premium ≈ $22m, expected loss ≈ $12.8m (LR 0.57), 1-in-200 ≈ $18.9m, capital ≈ 27% of premium, ROC ≈ 26%. Independence assumed — auto liability events are far less correlated than cyber, but severity *trend* is fully correlated across the book and is the systemic risk here.

## 7. Where it is most likely wrong, and what to watch in force

1. **No driver data.** Small-fleet trucking loss is mostly driver loss; I only see driver count and whatever the submission declares. First in-force addition: MVR + PSP pulls on bind.
2. **Crash → claim conversion is assumed, not observed.** Watch claims-per-crash on the bound book from month one.
3. **Severity tail and venue** — ILFs look thin (§6). Watch large-loss emergence by state.
4. **Self-reported MCS-150 fields** (units, drivers, mileage). Cross-checked against VIN count and inspection activity, but a carrier that never gets inspected is invisible.
5. **Adverse selection.** An instant-quote entrant sees new ventures and carriers other insurers dropped. Watch quote-to-bind mix by authority-age bucket weekly; if <1-year carriers exceed their census share by 2×, the new-venture factor is too low.
6. **Insurance-cancellation signal** currently comes from the submission, not L&I. Automate L&I before go-live.

## 8. What this attracts, and roadmap

**Book attracted:** small, mostly newer, general-freight carriers in mid-venue states, priced $7–15k per unit; high-venue long-haul new ventures priced $20k+ where the market will often beat us; clean established owner-operators at the $6.5k floor where we are competitive but the census share is small. Declines concentrate on authority/status, appetite and data-integrity rules.

**Roadmap:** (1) replace A1/A3/A5 with GLM estimates; (2) L&I automation; (3) MVR/PSP at bind; (4) telematics discount; (5) physical damage using vPIC stated value; (6) re-fit relativities on 12 months of quote-to-bind and claims; (7) price elasticity by segment.
