# Rating Manual — Small-Fleet Trucking Primary Auto Liability (v0.1.0)

Rendered from `config/rates.yaml`. Do not edit by hand.

## 1. Coverage and exposure base
- Primary auto liability, $1,000,000 CSL, occurrence, annual.
- Exposure base: **power-unit-year**. Premium = Σ units × unit premium + policy fee.

## 2. Base loss cost (per power-unit-year, base segment)
- DOT-recordable crash rate: 0.045 / unit-year (range [0.036, 0.055]) × 2.0 claims per crash = 0.0900 claims / unit-year
- Limited severity at base limit: $42,265 (mixture: pdo 81.7% lognormal; injury 17.0% lognormal; fatal 1.4% pareto)
- Trend: 8% p.a. × 1.5 yrs = 1.122
- **Base loss cost = $4,269 / unit-year**

## 3. Relativities (multiplicative, product capped to [0.6, 3.25])
- Authority age (yrs): ≤1: 1.65, ≤3: 1.25, ≤99: 1.0
- Fleet size (units): ≤1: 0.95, ≤5: 1.0
- Radius: local_0_50 0.8, intermediate_51_200 1.0, regional_201_500 1.15, long_haul_500_plus 1.3
- Commodity: dry_van 1.0, reefer 1.05, flatbed 1.1, general_freight 1.0, building_materials 1.1, machinery_heavy 1.15, grain_feed 1.0, logs_lumber 1.2, intermodal 1.05, unknown 1.1
- Venue (garaging state): high 1.35 (LA GA FL TX CA IL NY NJ PA MO NV WA); medium 1.12 (AL MS SC NM OK AZ MD MI OR MN); low 0.9 (IA NE KS ND SD WI ID UT WY MT IN KY TN VA NC OH); else 1.00
- Drivers per unit: ≤0.99: 0.9, ≤1.2: 1.0, ≤2.0: 1.1, ≤99: 1.25
- Min driver CDL years (if supplied): ≤2: 1.3, ≤5: 1.1, ≤99: 1.0
- Avg vehicle age (vPIC): ≤5: 0.95, ≤12: 1.0, ≤20: 1.1, ≤99: 1.2
- Driver OOS ratio to segment avg (≥3 inspections): ≤0.5: 0.95, ≤1.5: 1.0, ≤3.0: 1.15, ≤99: 1.3
- Vehicle OOS ratio: ≤0.5: 0.95, ≤1.5: 1.0, ≤3.0: 1.1, ≤99: 1.2
- BASIC percentiles (**dormant on live data** — QCMobile returns "Not Public" for property carriers; applies only when a percentile is supplied another way): unsafe_driving: ≤50: 1.0, ≤65: 1.1, ≤100: 1.3; hos_compliance: ≤50: 1.0, ≤65: 1.08, ≤100: 1.2; vehicle_maintenance: ≤50: 1.0, ≤80: 1.05, ≤100: 1.12; driver_fitness: ≤50: 1.0, ≤80: 1.03, ≤100: 1.08; controlled_substances: ≤50: 1.0, ≤80: 1.1, ≤100: 1.3
- MCS-150 age (yrs): ≤2: 1.0, ≤99: 1.08
- MCS-150 mileage per unit: ≤30000: 0.9, ≤90000: 1.0, ≤140000: 1.08, ≤9000000000: 1.15; below 5,000 treated as unknown (1.00); not applied when radius is long_haul_500_plus
- Stack cap: product of authority_age × venue_state × radius capped at 2.0 before the other factors apply
- Own crash experience: Bühlmann Z = n/(n+25), n = units × 2 yrs; own relativity capped at 3.0×

## 4. Loss cost → premium
- ALAE 14% of loss; expense 22%, reinsurance 6%, profit/capital 7% of premium
- Technical unit premium = loss cost × (1+ALAE) / (1 − expense − reinsurance − profit)
- **Minimum premium $8,000 per unit**; policy fee $250
- Implied permissible loss+ALAE ratio: 65%

## 5. Limits offered
- $750,000, $1,000,000, $2,000,000 — ILFs from `analysis/fit_severity.py`

## 6. Decline / refer rules
- See `config/rules.yaml` (IDs D01–D31 decline, R01–R09 refer).
