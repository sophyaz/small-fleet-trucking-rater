# Market benchmark — observed 2025–2026 price points vs our rater

Primary auto liability, $1,000,000 CSL, for-hire trucking, 1–5 power units. Collected 2026-09-09. Feeds SOURCES.md row S16.

**Status:** benchmark collected 2026-09-09; three calibration changes applied the same day (§ Applied changes). Before/after figures below. The frequency anchor was then re-based on the crash file (crash rate 0.0625 → 0.045 [E], claims per crash 1.20 → 2.0, severity shares from crash flags); the table after that change is in § After the frequency re-basing.

## Method and caveats

- Sources are limited to insurer-published figures (Progressive Commercial), trade press (Overdrive, CCJ, FleetOwner, Transport Topics, Land Line, FreightWaves) and ATRI's cost study as reported by that press. Reddit, TruckersReport and broker lead-generation sites were excluded by instruction. Overdrive and CCJ block automated fetches, so their figures come from search-index excerpts of the named articles; verify the wording against the live page before quoting externally.
- Almost nobody publishes a liability-only number. Where a figure bundles physical damage or cargo, the table shows the published figure and a **liability-only estimate** with the assumption stated. Those estimates are mine, not the source's.
- Published ranges are converted to a midpoint for the comparison. Ranges are wide (typically ±30%), so a gap inside ±20% is indistinguishable from noise.
- ATRI per-mile figures are converted at ATRI's 85,991 average annual miles per truck (2025 report). ATRI's insurance line is "liability and cargo premiums" and is dominated by fleets far larger than 5 units except where the small-fleet band is quoted.
- **Indexing to the 2026-09-01 effective date** uses ATRI's premium trend: 2024 data × 1.039 (2025) × 1.064 (Q1-2026 vs 2025); 2025 data × 1.064; 2026 data × 1.00. This is a level adjustment only. It says nothing about how the market's spread between profiles moves.
- Each observed point is mirrored by a synthetic submission in `samples/submissions_benchmark/` (fixtures under `samples/fixtures/`, fake USDOTs 9900101–9900110). Profiles that the source does not specify (inspection counts, OOS rates, truck model year) are filled with clean, average values so the comparison isolates the stated profile.

## Observed price points

| # | Source and URL | Date | Carrier profile (units / years / state / radius / commodity) | Quoted annual premium | Per unit | What it includes | Liability-only estimate (assumption) | Indexed to 2026-09 |
|---|---|---|---|---|---|---|---|---|
| P1 | Progressive Commercial, "How much is truck insurance?" https://www.progressivecommercial.com/commercial-auto-insurance/truck-insurance/commercial-truck-insurance-cost/ | 2025 policy year (page live 2026-09) | For-hire **transport** truckers, national, per power unit, new Progressive policies sold in 2025, no violations; mixed tenure | $926/mo = **$11,112** | $11,112 | Liability + physical damage | ~$7,800 (PD on a ~$100k tractor ≈ $3,000–3,500; liability ≈ 70%) | $8,300 |
| P2 | Progressive Commercial, same page | 2025 policy year | For-hire **specialty** truckers (dump, tow, etc.; local/intermediate radius), national, per power unit, no violations | $734/mo = **$8,808** | $8,808 | Liability + physical damage | ~$6,200 (same 70% split) | $6,600 |
| P3 | Overdrive, "How independents can navigate trucking insurance to create savings" https://www.overdriveonline.com/business/article/15740305/how-independents-can-navigate-trucking-insurance-to-create-savings | 2025-03-21 | Michael Castaldi: 1 truck (2003 Peterbilt 379), Florida, authority since 1986, reefer, Florida↔Arizona direct-customer long haul, ~150k mi/yr, team with son, same insurer 20 years | "just north of **$15,000**" | ~$15,000 | Article context is liability polling; likely liability + cargo, little PD on a 2003 truck | ~$12,000 (cargo ≈ $2,000–3,000 for reefer) | $12,800 |
| P4 | Overdrive 2024 reader poll, reported in P3 article | Poll 2024, published 2025-03 | One-truck independents with authority, national | 24% pay **>$15,000**; 48% pay **<$10,000** for liability; modal band $10–15k | $12,500 (band midpoint) | Liability | $12,500 | $13,800 |
| P5 | Overdrive, "Trucking insurance guide: Owner-operator costs and coverages" https://www.overdriveonline.com/partners-in-business/trucking-other-insurance/article/15712025/trucking-insurance-guide-owneroperator-costs-and-coverages | 2025 edition | New authority, 1 truck: "quotes from **$8,000 to $20,000** or more"; "an owner-operator with a new truck and trailer and his own authority is likely to pay **$10,000 or more** a year for $1 million in primary liability" | $8,000–$20,000+ | $14,000 (midpoint) | Primary liability | $14,000 | $14,900 |
| P6 | FreightWaves Checkpoint, "Commercial truck insurance cost" https://www.freightwaves.com/checkpoint/commercial-truck-insurance-cost/ | 2026-03-26 | Experienced owner-operator, established authority, 1 tractor, home-state garaging, standard cargo, late-model tractor (~$120k) | Auto liability **$7,500–$15,000+** | $11,250 (midpoint) | Auto liability only | $11,250 | $11,250 |
| P7 | FreightWaves, "How to save on commercial truck insurance in 2025" https://www.freightwaves.com/news/how-to-save-on-commercial-truck-insurance-in-2025-without-cutting-corners (citing MarketWatch) | 2025-05-08 | One-truck operation, national | **$12,000–$17,000** in 2025 (was $11,000–16,000 late 2023/early 2024) | $14,500 (midpoint) | Primary liability + cargo | ~$12,500 (cargo ≈ $2,000) | $13,300 |
| P8 | ATRI 2025 Operational Costs of Trucking, as reported by CCJ, "Why safe trucking fleets are paying record-high insurance rates" https://www.ccjdigital.com/business/insurance/article/15825494/why-safe-trucking-fleets-are-paying-recordhigh-insurance-rates | 2026 (2024 data) | Fleets with **≤25 trucks**: **20.3¢/mile** liability premiums vs 10.4¢ for 101–250 trucks | 20.3¢ × 85,991 mi = **$17,456** (2024); +3.9% 2025 trend = **$18,137** | $18,137 | Liability premiums | $18,137 | $19,300 |
| P9 | ATRI 2026 update (2025 data), as reported by FleetOwner https://www.fleetowner.com/operations/article/55392569/atri-report-breaks-down-class-8-truck-operating-costs-by-region-and-expense-category and Transport Topics https://www.ttnews.com/articles/insurance-cost-mitigation | 2026-07-22 / 2026-04-23 | All-fleet industry average: **$0.106/mile** (+3.9%); Northeast $0.12, Midwest $0.10; Q1-2026 +6.4% | Midwest 10¢ × 85,991 = **$8,600**; national $9,115 | $8,600 | Liability + cargo premiums | $8,600 (large-fleet weighted; a floor for small fleets) | $9,150 |
| P10 | Geotab, "Commercial truck insurance cost" https://www.geotab.com/blog/commercial-truck-insurance-cost/ | 2026-08-20 | Owner-operator with authority: **$9,000–$17,000**; small fleet (2–10 trucks): **$10,800–$18,000+** per truck | $14,400 (small-fleet midpoint) | $14,400 | Bundled auto policy | ~$11,500 (80% liability) | $11,500 |

Supporting ranges not run (no profile detail): Truckstop.com 2026-07-09 https://truckstop.com/blog/owner-operator-expenses/ "$10,000–$20,000" all-in for owner-operators, new authority at the top; DAT https://www.dat.com/solutions/owner-operator-insurance-coverage "$8,000 and $15,000 per year for full coverage" for single owner-operators with authority. Trend context: Land Line 2026-05-21 https://landline.media/truck-insurance-costs-keep-climbing-even-as-crash-rates-fall/ (ATRI: liability premiums +19% 2021–2024 while crash rates fell); CCJ 2026-04-21 https://www.ccjdigital.com/business/insurance/article/15830169/why-truck-insurance-premiums-rose-in-2025-despite-fewer-crashes ($0.102/mi 2024, +12.5% 2023, +3% 2024).

## Applied changes (2026-09-09)

All three in `config/rates.yaml`; the second and third also needed a few lines in `rater/price.py`.

1. **Minimum premium per unit $6,500 → $8,000.** Every 2025–26 source puts clean established one-truck liability at $7,500 or more (P1, P6, P9, DAT low end). Tag [B].
2. **Stack cap:** the product of authority age × venue × radius is capped at 2.0 before the other factors apply. Uncapped it reached 2.75 on P5 ($20.9k against a published $8–20k band). Tag [S].
3. **Mileage intensity is not applied when radius is long haul.** Both proxy the same exposure and fired together on P1, P3, P5 and P10. Tag [S].

**Watch list, not applied** (one named renewal each, see RATIONALE.md §7): tenure credit above 3 years; vehicle age 1.20 on 20+ year trucks; 8% severity trend vs ATRI's 4–6% premium trend.

## Our price vs observed — before and after

Run: `python samples/make_benchmark_samples.py --run` (offline, fixtures). Our per-unit figure excludes the $250 policy fee. Gap = ours ÷ observed liability estimate − 1.

| # | Synthetic profile | Before / unit | After / unit | Floor binds (after)? | Rel. product before → after | Observed liab. est. | Gap before | Gap after | Gap after vs indexed | Gap after vs published |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 1 unit, 3 yrs, CO (neutral), long haul, dry van, MY2019, 100k mi | $11,719 | **$10,851** | no | 1.54 → 1.43 | $7,800 | +50% | **+39%** | +31% | −2% |
| P2 | 1 unit, 5 yrs, CO, local, building materials, MY2017, 40k mi | $6,500 | **$8,000** | yes | 0.77 | $6,200 | +5% | +29% | +21% | −9% |
| P3 | 1 unit, 39 yrs, FL, long haul, reefer, MY2003, 2 drivers, 150k mi | $16,858 | **$14,659** | no | 2.22 → 1.93 | $12,000 | +41% | +22% | +15% | −2% |
| P4 | 1 unit, 6 yrs, GA, regional, dry van, MY2018, 90k mi | $10,367 | **$10,367** | no | 1.37 | $12,500 | −17% | −17% | −25% | −17% |
| P5 | 1 unit, 0.3 yrs, TX, long haul, dry van, MY2020, no inspections (refer R01) | $20,883 | **$13,355** | no | 2.75 → 1.76 | $14,000 | +49% | **−5%** | −10% | −5% |
| P6 | 1 unit, 5 yrs, IN, intermediate, dry van, MY2023, 80k mi | $6,500 | **$8,000** | yes | 0.71 | $11,250 | −42% | **−29%** | −29% | −29% |
| P7 | 1 unit, 2 yrs, IL, regional, dry van, MY2019, 95k mi | $14,625 | **$14,625** | no | 1.93 | $12,500 | +17% | +17% | +10% | +1% |
| P8 | 5 units, 8 yrs, PA, long haul, general freight, 1 crash, 86k mi | $17,167 | **$17,167** | no | 2.26 | $18,137 | −5% | −5% | −11% | −5% |
| P9 | 3 units, 10 yrs, WI, regional, dry van, 86k mi | $6,500 | **$8,000** | yes | 0.83 | $8,600 | −24% | **−7%** | −13% | −7% |
| P10 | 3 units, 3 yrs, NC, long haul, dry van, 100k mi | $10,637 | **$9,849** | no | 1.40 → 1.30 | $11,500 | −8% | −14% | −14% | −32% |

| Statistic (vs liability estimate) | Before | After | After, vs indexed |
|---|---|---|---|
| Median gap | −0.3% | −5.0% | −10.7% |
| Mean gap | +6.5% | +3.0% | −2.5% |
| Range | −42% to +50% | −29% to +39% | −29% to +31% |
| Within ±20% | 5 of 10 | 6 of 10 | 6 of 10 |
| Within ±20% vs published figure | 6 of 10 | 8 of 10 | — |

**Book impact** (offline book check, before → after): synthetic set 17 priced, 7 up (floor), 5 down (stack cap / mileage skip), total −2.8%; real-carrier sample (n=45, 34 priced) 2 up, 13 down, 19 unchanged, total −2.3%. The real sample is dominated by new registrations on the R01 refer path, which is why the stack cap moves more of it than the floor does. Every referred new venture now prices at $13,605 instead of $15,124 (1 unit) or $18,619 (2 units).

## What the gaps say after the change

- **The spread narrowed and the worst cells moved most.** P5 (new venture, TX, long haul) went from +49% to −5%. P6 and P9 (clean, low-venue, floor-bound) went from −42%/−24% to −29%/−7%. Range narrowed from 92 points to 68.
- **Half the residual is the Progressive split assumption.** P1 and P2 are the two largest overshoots at +39% and +29%, and both depend on my 70% liability share of a bundled premium. Against the published figures they are −2% and −9%. If Progressive's liability share is 80%, P1 is +22% and P2 is +13%. That single assumption moves the P1/P2 conclusion more than any factor in the config, so do not tune further to those two.
- **P6 is the remaining honest miss.** A five-year, late-model, Indiana, intermediate-radius, clean owner-operator prices at the $8,000 floor against a published $7,500–$15,000 range. The floor is inside the range now, but at its bottom. A higher floor would fix P6 and break P2 and P9.
- **Indexing to 2026-09 shifts everything about 5 points cheaper relative to market.** Median −5% becomes −11%. That is the ATRI premium trend still running at 6%; the config's own 8% severity trend already carries part of it, so this is not an argument for a further increase on its own.
- **Small fleets still fit** (P8 −5%, P9 −7%, P10 −14%).
- **P3 still reads high at +22%,** driven by vehicle age 1.20, two drivers 1.10 and venue 1.35 on a 39-year carrier with no tenure credit. That is the watch-list case, not a config change.

## After the frequency re-basing (2026-09-09, later the same day)

`config/rates.yaml`: `crash_rate_per_unit_year` 0.0625 → 0.045 [E], `crash_to_claim_ratio` 1.20 → 2.0 [S], severity shares 73.5 / 25 / 1.5 → 81.7 / 17.0 / 1.35 [E]. Rationale in `docs/RATIONALE.md` §4. The claims-per-crash value was chosen from this table: backing claim frequency out of the liability estimates (premium × 65% permissible ÷ 1.14 ALAE ÷ limited severity ÷ relativity product, at the measured crash rate for the profile's fleet size and tenure) gives 1.17 (P1), 1.95 (P4), 3.39 (P6), 2.32 (P7) and 2.82 (P9) claims per crash, median 2.3; because the industry runs above 100% combined those are floors. 2.0 holds the base loss cost within 1.4% of its pre-change value ($4,269 vs $4,328).

| # | Per unit before re-basing | Per unit after | Floor binds? | Rel. product | Observed liab. est. | Gap vs liab. est. | Gap vs published |
|---|---|---|---|---|---|---|---|
| P1 | $10,851 | **$10,703** | no | 1.43 | $7,800 | +37% | −4% |
| P2 | $8,000 | **$8,000** | yes | 0.77 | $6,200 | +29% | −9% |
| P3 | $14,659 | **$14,459** | no | 1.93 | $12,000 | +21% | −4% |
| P4 | $10,367 | **$10,225** | no | 1.37 | $12,500 | −18% | −18% |
| P5 | $13,355 | **$13,173** | no | 1.76 | $14,000 | −6% | −6% |
| P6 | $8,000 | **$8,000** | yes | 0.71 | $11,250 | −29% | −29% |
| P7 | $14,625 | **$14,425** | no | 1.93 | $12,500 | +15% | −1% |
| P8 | $17,167 | **$19,503** | no | 2.26 → 2.60 | $18,137 | +8% | +8% |
| P9 | $8,000 | **$8,000** | yes | 0.83 | $8,600 | −7% | −7% |
| P10 | $9,849 | **$9,714** | no | 1.30 | $11,500 | −16% | −33% |

| Statistic (vs liability estimate) | Before re-basing | After |
|---|---|---|
| Median gap | −5.0% | +0.8% |
| Mean gap | +3.0% | +3.4% |
| Range | −29% to +39% | −29% to +37% |
| Within ±20% | 6 of 10 | 6 of 10 |
| Within ±20% vs published figure | 8 of 10 | 8 of 10 |

Nine profiles moved by −1.4% (the base loss cost change). P8 is the exception: it carries one crash in 24 months, and the credibility surcharge measures that crash against the expected crash rate, which fell from 0.0625 to 0.045 — the same crash is now more surprising, so its own-experience relativity rose from 1.17 to 1.35. That is the intended behaviour of a lower, estimated base rate, and P8 stays inside the band.

**Book impact** (offline book check): synthetic set −1.4% on clean risks, 86,512 max policy (was 76,182; a crash-surcharged 5-unit carrier); real-carrier sample total written premium $561k → $555k (−1.0%), floor binds on 2 of 34 written, unchanged.

## Reproduce

```
python samples/make_benchmark_samples.py --run            # writes data/derived/market_benchmark.csv
python samples/make_benchmark_samples.py --run out.csv    # or a path of your choice
RATER_OFFLINE=1 python -m rater samples/submissions_benchmark/04_B05_overdrive_new_authority_tx.json
python -m analysis.render_manual                          # docs/RATING_MANUAL.md picks up the floor, stack cap and mileage skip
```
