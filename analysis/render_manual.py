"""Render docs/RATING_MANUAL.md from config/rates.yaml so manual == code by construction. Run: python -m analysis.render_manual"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rater.config import rates, rules
from rater.losscost import limited_mean

def band(t): return ", ".join(f"≤{r['max']}: {r['factor']}" for r in t)
def main():
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")   # Windows console is cp1252
    c = rates(); lc, R, L = c["loss_cost"], c["relativities"], c["loadings"]
    lev = limited_mean(lc["severity"], c["meta"]["base_limit_csl"])["limited_mean"]
    trend = (1 + lc["severity_trend_annual"]) ** lc["trend_years"]
    base = lc["crash_rate_per_unit_year"] * lc["crash_to_claim_ratio"] * lev * trend
    lines = [f"# Rating Manual — Small-Fleet Trucking Primary Auto Liability (v{c['meta']['version']})", "",
             "Rendered from `config/rates.yaml`. Do not edit by hand.", "",
             "## 1. Coverage and exposure base",
             f"- Primary auto liability, ${c['meta']['base_limit_csl']:,} CSL, occurrence, annual.",
             f"- Exposure base: **power-unit-year**. Premium = Σ units × unit premium + policy fee.", "",
             "## 2. Base loss cost (per power-unit-year, base segment)",
             f"- DOT-recordable crash rate: {lc['crash_rate_per_unit_year']} / unit-year (range {lc['crash_rate_range']}) × {lc['crash_to_claim_ratio']} claims per crash = {lc['crash_rate_per_unit_year']*lc['crash_to_claim_ratio']:.4f} claims / unit-year",
             f"- Limited severity at base limit: ${lev:,.0f} (mixture: " + "; ".join(f"{k} {v['share']:.1%} {v['dist']}" for k, v in lc['severity'].items()) + ")",
             f"- Trend: {lc['severity_trend_annual']:.0%} p.a. × {lc['trend_years']} yrs = {trend:.3f}",
             f"- **Base loss cost = ${base:,.0f} / unit-year**", "",
             "## 3. Relativities (multiplicative, product capped to " + f"[{R['total_cap']['min']}, {R['total_cap']['max']}])",
             f"- Authority age (yrs): {band(R['authority_age_years'])}",
             f"- Fleet size (units): {band(R['fleet_size_units'])}",
             "- Radius: " + ", ".join(f"{k} {v}" for k, v in R["radius_miles"].items()),
             "- Commodity: " + ", ".join(f"{k} {v}" for k, v in R["commodity"].items()),
             "- Venue (garaging state): " + "; ".join(f"{k} {v['factor']} ({' '.join(v['states'])})" for k, v in R["venue_state"].items()) + "; else 1.00",
             f"- Drivers per unit: {band(R['driver_unit_ratio'])}",
             f"- Min driver CDL years (if supplied): {band(R['driver_experience_years_min'])}",
             f"- Avg vehicle age (vPIC): {band(R['vehicle_age_years_avg'])}",
             f"- Driver OOS ratio to segment avg (≥{R['oos_ratio_to_segment_avg']['min_inspections']} inspections): {band(R['oos_ratio_to_segment_avg']['driver'])}",
             f"- Vehicle OOS ratio: {band(R['oos_ratio_to_segment_avg']['vehicle'])}",
             "- BASIC percentiles (**dormant on live data** — QCMobile returns \"Not Public\" for property carriers; applies only when a percentile is supplied another way): " + "; ".join(f"{k}: {band(v)}" for k, v in R["basic_percentile"].items()),
             f"- MCS-150 age (yrs): {band(R['mcs150_stale_years'])}",
             f"- MCS-150 mileage per unit: {band(R['mileage_intensity'])}; below {R.get('mileage_min_plausible_per_unit', 0):,} treated as unknown (1.00)"
             + (f"; not applied when radius is {', '.join(R['mileage_intensity_skip_radii'])}" if R.get("mileage_intensity_skip_radii") else ""),
             *([f"- Stack cap: product of {' × '.join(R['stack_cap']['factors'])} capped at {R['stack_cap']['max']} before the other factors apply"] if R.get("stack_cap") else []),
             f"- Own crash experience: Bühlmann Z = n/(n+{c['credibility']['k_unit_years']}), n = units × {c['credibility']['history_years']} yrs; own relativity capped at {c['credibility']['own_rate_cap_multiple']}×",
             *([f"  - Off-balanced: divided by its expectation at that fleet size under Poisson(segment rate), so the cap does not leak rate (E[rel] was {0.958} measured)"] if c['credibility'].get('offbalance_correction') else []), "",
             "## 4. Loss cost → premium",
             f"- ALAE {L['alae_ratio']:.0%} of loss; expense {L['expense_ratio']:.0%}, reinsurance {L['reinsurance_ratio']:.0%}, profit/capital {L['profit_cost_of_capital']:.0%} of premium",
             f"- Technical unit premium = loss cost × (1+ALAE) / (1 − expense − reinsurance − profit)",
             f"- **Minimum premium ${L['minimum_premium_per_unit']:,} per unit**; policy fee ${L['policy_fee']}",
             *([f"  - Scaled by the own-experience relativity when that relativity is a surcharge (never a discount), so an adverse crash record cannot fall back to the clean-risk floor"] if L.get('minimum_premium_experience_scaled') else []),
             f"- Implied permissible loss+ALAE ratio: {1 - L['expense_ratio'] - L['reinsurance_ratio'] - L['profit_cost_of_capital']:.0%}", "",
             "## 5. Limits offered", "- " + ", ".join(f"${x:,}" for x in c["limits"]["offered"]) + " — ILFs from `analysis/fit_severity.py`",
             f"- **Enforced**: a limit off this list declines (D32); above the ${c['limits'].get('base', c['meta']['base_limit_csl']):,} base refers for manual excess pricing (R12), because the tail is not calibrated at $2m+", "",
             "## 6. Decline / refer rules",
             "- See `config/rules.yaml`. " + ", ".join(sorted(r["id"] for r in rules() if r["action"] == "decline")) + " decline;",
             "  " + ", ".join(sorted(r["id"] for r in rules() if r["action"] == "refer")) + " refer."]
    os.makedirs("docs", exist_ok=True)
    with open("docs/RATING_MANUAL.md", "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")   # Σ, ≤ fail on cp1252
    print("\n".join(lines))

if __name__ == "__main__":
    main()
