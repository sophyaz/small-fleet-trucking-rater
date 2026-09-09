# Proposed [E] values from census × crash file — 2026-09-09 (NOT applied to config/rates.yaml)

Inputs: `data/raw/census.csv` (S3, SMS census input, 2,113,851 carriers) and `data/raw/crash_2023..2026.csv` (S4, 648,193 rows).
Segment: interstate (`carrier_operation = A`), `authorized_for_hire`, not HM, not passenger, 1–5 power units → **394,864 carriers**.
Window: 3 years back from the last report date (2023-09-03 → 2026-09-03), federally recordable crashes only → **522,657 crash rows**, of which 80.2% carry a DOT number and 14.0% of those match the segment.
Outputs: `data/derived/crash_rate_by_segment.csv`, `crash_rate_by_state.csv`, `glm_relativities.csv` (NB GLM, alpha 3.16 by Cameron–Trivedi, offset log unit-years, reference fleet 2-5 / authority 3y+ / state CA), `glm_relativities_operating.csv` (sensitivity), `proposed_venue_state.csv`, `authority_age_diagnostics.txt`.
Flag rule: any segment / state with **< 200 crashes** is marked ⚠.

## 1. loss_cost.crash_rate_per_unit_year

| Basis | Rate / unit-year | SE | Crashes |
|---|---|---|---|
| Base segment (2–5 units, authority 3y+), as measured | 0.0363 | 0.0002 | 30,775 |
| Same, grossed up for the 19.8% of recordable crash rows with no DOT number (÷ 0.802) | **0.0452** | 0.0003 | — |
| All 1–5 unit carriers pooled, as measured | 0.0375 | 0.0002 | 58,765 |
| Operating carriers only (MCS-150 mileage > 0), lag-truncated window | 0.0334 | 0.0002 | 28,167 |

Current: 0.0625, range [0.04, 0.09]. **Proposed: 0.045 (SE 0.0003), range [0.036, 0.055].** The measured 0.036 is a floor: unmatched crashes (no DOT) are excluded from the numerator but nothing is excluded from the denominator, the last ~3 months are under-reported, and census power units are self-reported and often overstated. Severity flags for reference: fatal share 2.7%, injury share 34% of recordable crashes (manual severity mix is per *claim*, so not directly comparable).

## 2. relativities.authority_age_years — **do not replace from this data**

| Bucket | Current | GLM, full census | SE | GLM, operating carriers¹ | SE | Crashes |
|---|---|---|---|---|---|---|
| max 1 (<1y) | 1.65 | 0.411 | 0.016 | 0.596 | 0.056 | 680 (2–5 unit cell: 184 ⚠) / 120 ⚠ |
| max 3 (1–3y) | 1.25 | 0.662 | 0.010 | 0.902 | 0.017 | 6,652 / 4,586 |
| max 99 (3y+) | 1.00 | 1.000 | ref | 1.000 | ref | 51,433 / 47,302 |

¹ carriers with MCS-150 mileage > 0, window ending 4 months before the last report date (see `authority_age_diagnostics.txt`).

The census cannot distinguish *registered* from *operating*. 80% of carriers registered < 1 year ago have never filed mileage, and simply dropping them moves the 1–3y relativity from 0.66 to 0.90; a finer cut shows the rate climbing monotonically from 0.003 (<3 months) to 0.044 (5–10 years). The residual < 1.0 is still dominated by dormant registrations, worse DOT matching for new carriers, and reporting lag concentrated in their exposure. The manual's 1.65 / 1.25 come from insured-loss experience and should stay tagged [S]; if anything, record the finding in `docs/RATIONALE.md` as "not contradicted by usable public data". A defensible public-data proxy would need the L&I authority-grant date (S6) or a first-inspection date as the "started operating" marker.

## 3. relativities.fleet_size_units

| Bucket | Current | GLM, full census | SE | GLM, operating carriers | SE |
|---|---|---|---|---|---|
| max 1 (solo) | 0.95 | **1.176** | 0.013 | 1.224 | 0.014 |
| max 5 (2–5) | 1.00 | 1.000 | ref | 1.000 | ref |

Stable across cuts (raw 3y+ rates: 0.0462 vs 0.0363 = 1.27). **Proposed: max 1 → 1.18 (SE 0.013), max 5 → 1.00.** Caveat: part of the gap may be 2–5 unit carriers overstating units in the census (dilutes their per-unit rate), so 1.18 is an upper bound on the true per-unit relativity; 1.10–1.18 is the honest range.

## 4. relativities.venue_state — frequency by domicile state (US only, unit-year-weighted mean = 1.00)

Important: the GLM measures **crash frequency by carrier domicile state**; the manual's venue tiers are a **severity / legal-environment** factor (ATRI verdict geography). These are different things. Recommended use: either keep `venue_state` as a severity factor and add a separate `domicile_state` frequency relativity from the table below, or blend explicitly and say so in RATIONALE §A5. Do not just overwrite the tiers.

| Tier | Current factor | Proposed factor | SE | Crashes | States (rebased relativity) |
|---|---|---|---|---|---|
| high (≥1.235) | 1.35 | **1.32** | 0.030 | 4,675 | IN 1.36, NJ 1.29 |
| medium (1.06–1.235) | 1.12 | **1.12** | 0.012 | 21,220 | OH 1.18, IL 1.17, FL 1.14, VA 1.12, MI 1.11, NC 1.09, MO 1.09, PA 1.08, GA 1.07 |
| neutral (0.95–1.06) | 1.00 | 1.02 | 0.009 | 18,755 | TX 1.06, OK 1.02, DE 1.02, CA 1.00, MN 1.00, AR 0.99, MD 0.97, AL 0.96, LA 0.95 |
| low (<0.95) | 0.90 | **0.78** | 0.009 | 13,446 | TN 0.94, SC 0.93, KS 0.92, MS 0.91, ME 0.90 ⚠, KY 0.89, MA 0.86, NV 0.85, WA 0.84, WI 0.80, AZ 0.79, CO 0.78, CT 0.77, OR 0.76, IA 0.76, NY 0.73, UT 0.73, NE 0.72, WV 0.69 ⚠, RI 0.68 ⚠, ID 0.65, ND 0.59 ⚠, NH 0.57 ⚠, SD 0.56 ⚠, WY 0.53 ⚠, NM 0.52, MT 0.51 ⚠, HI 0.48 ⚠, VT 0.45 ⚠, AK 0.14 ⚠, DC 0.13 ⚠ |

Per-state SEs are 0.02–0.05 for large states and 0.05–0.10 for the ⚠ states (full list in `proposed_venue_state.csv`). The low tier spans 0.13–0.94; if adopted as a frequency factor, split it at 0.85 (TN–NV → 0.90; the rest → 0.70) rather than using 0.78 for all.

Largest disagreements with the current tiers: CA, TX, LA (high → neutral); NY, WA, NV (high → low); IN (low → high); OH, VA, NC (low → medium). That pattern (Sun Belt / coastal nuclear-verdict states are *not* high-frequency; Midwest corridor states are) is exactly the frequency-vs-severity distinction above.

## Segments / states with fewer than 200 crashes ⚠
- Segment cell: 2–5 units, authority < 1y — 184 crashes (full census); < 1y total 120 in the operating cut.
- States: ME 151, WV 163, RI 111, ND 190, NH 107, SD 192, WY 120, MT 142, HI 4, VT 49, AK 4, DC 2.
