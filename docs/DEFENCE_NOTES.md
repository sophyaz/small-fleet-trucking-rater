# Defence notes — 45–60 min walkthrough

## Opening (3 min)
"Submission in, one of three decisions out. Enrichment from FMCSA and NHTSA, a segment crash rate from the census and crash files, credibility-weighted for the carrier's own record, relativities on top, gross-up, floor. Every number is in one YAML file and the manual is rendered from it."

## Exposure base — alternatives considered
| Base | For | Against | Used as |
|---|---|---|---|
| Power-unit-year | Market standard; verifiable vs census; not gameable down | Ignores utilisation | **Base** |
| Mileage (MCS-150) | Closest to true exposure | Self-reported, stale, per-fleet not per-truck | Relativity, discounted |
| Revenue | Correlates with contract exposure | Unverifiable for a 2-truck company | Not used |
| Drivers | Loss is driver loss | Turnover; not what's insured | Ratio relativity |

## "Sourcing is part of the test" — what I used and why (have SOURCES.md open)
- Census + crash file = denominator + numerator → a real GLM with an offset. That is the core.
- QCMobile = the same record, live, for any DOT they type in.
- vPIC = catches trailers and pickups submitted as power units.
- SERFF filings = how Progressive structures the same problem; my relativity skeleton mirrors theirs.
- What I did NOT trust: national OOS averages for small carriers; IBM-style headline numbers; any single vendor figure.

## "What book would it attract, would it make money?"
- Adverse selection is the real question. Census share of <1-yr carriers vs our quote mix is the metric.
- Money comes from selection (decline list + refer) and the floor, not the base rate. Show portfolio.py: LR 0.53, capital 23% of premium, ROC ~30% — conditional on A1 × A2 (crash rate is now estimated; claims per crash is the selected half).
- Where the market beats us: high-venue long-haul new ventures. That's fine — we don't want them at our price.

## "Where is it most likely wrong?"
Drivers → crash-to-claim → tail/venue → self-reported MCS-150 → selection. Have the tornado up.

## "What would you watch in force?"
Quote-to-bind mix by authority age; claims per recordable crash; large-loss emergence by state; inspection and MCS-150 update behaviour post-bind; insurance-filing churn.

## Anticipated challenges
- *"Your decline rate on your own sample is 42%."* — Sample is adversarial by design (one carrier per rule). Show the census draw: 45 real carriers, 24% declined, 38% referred (almost all new applicants waiting on a BMC-91 filing), 38% priced.
- *"Your BASIC factors never fire."* — Correct: percentiles are "Not Public" for 53 of 53 live property carriers. They are marked dormant; the API does return the measure and threshold, which is the replacement.
- *"Why refer instead of decline new ventures?"* — Half the segment is <3 years old; declining them is declining the market. Surcharge + refer + watch.
- *"ILFs look thin."* — Agree; flagged in §6. Fatal share or α is light. That is exactly the parameter I'd buy data for.
- *"Why is credibility k = 25?"* — Selected so a 5-truck, 2-year record gets Z≈0.29 and a 1-truck record ≈0.07. Would fit from the crash file variance components given a day.
- *"You didn't use L&I."* — Correct; scraping was the time sink. Rule D23 reads the declared field; automation is roadmap item 2.

## Bonus items status
Trends (A8, trend factor in config), multi-limit (fit_severity ILF table), margin/capital (portfolio.py), market comparison (S16 collected: ten 2025–26 price points in MARKET_BENCHMARK.md, median gap +0.8% after the frequency re-basing; S14 SERFF filings still to pull), physical damage (design only: vPIC year/make → stated value, comp/coll rate on value with age relativity).
