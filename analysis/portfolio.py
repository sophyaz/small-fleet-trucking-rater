"""Bonus: aggregate loss distribution for 1,000 policies -> 1-in-200, capital, return on capital. Run: python -m analysis.portfolio"""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rater.config import rates
from rater.losscost import limited_mean

def main(n_pol=1000, sims=5000, seed=5):
    cfg = rates(); rng = np.random.default_rng(seed); lc, L = cfg["loss_cost"], cfg["loadings"]
    limit = cfg["meta"]["base_limit_csl"]; sev = lc["severity"]
    units = rng.integers(1, 6, n_pol); expo = units.sum()
    lev = limited_mean(sev, limit)["limited_mean"]; trend = (1 + lc["severity_trend_annual"]) ** lc["trend_years"]
    freq = (lc["crash_rate_per_unit_year"] * lc["crash_to_claim_ratio"])
    prem_unit = max(freq * lev * trend * (1 + L["alae_ratio"]) / (1 - L["expense_ratio"] - L["reinsurance_ratio"] - L["profit_cost_of_capital"]), L["minimum_premium_per_unit"])
    premium = prem_unit * expo
    agg = np.zeros(sims)
    shares = [s["share"] for s in sev.values()]; keys = list(sev)
    for j in range(sims):
        k = rng.poisson(freq * expo * trend)          # trend applied to frequency*severity jointly here for simplicity
        comps = rng.choice(len(keys), k, p=shares); tot = 0.0
        for c in comps:
            s = sev[keys[c]]
            if s["dist"] == "lognormal":
                sig2 = math.log(1 + s["cv"]**2); x = rng.lognormal(math.log(s["mean"]) - sig2/2, math.sqrt(sig2))
            else:
                x = s["threshold"] * (1 - rng.random()) ** (-1/s["alpha"])
            tot += min(x, limit)
        agg[j] = tot
    p = np.percentile(agg, [50, 90, 99, 99.5]); mean = agg.mean()
    capital = p[3] - mean
    print(f"policies {n_pol}, unit-years {expo}, premium {premium:,.0f}, expected loss {mean:,.0f} (LR {mean/premium:.2f})")
    print(f"aggregate loss: p50 {p[0]:,.0f}  p90 {p[1]:,.0f}  p99 {p[2]:,.0f}  1-in-200 {p[3]:,.0f}")
    print(f"capital (1-in-200 minus mean): {capital:,.0f} = {capital/premium:.0%} of premium")
    profit = premium * L["profit_cost_of_capital"]
    print(f"profit load {profit:,.0f} -> return on capital {profit/capital:.1%}   (independence assumed: no systemic load — auto liability is less correlated than cyber, but severity trend IS correlated across the book)")

if __name__ == "__main__":
    main()
