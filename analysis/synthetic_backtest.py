"""Pipeline check: simulate a book under the rater's OWN frequency/severity truth, price it, confirm loss ratio ~ target.
Tests the plumbing (not the assumptions). Run: python -m analysis.synthetic_backtest --policies 2000"""
import argparse, os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rater.config import rates
from rater.losscost import limited_mean

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--policies", type=int, default=20000); ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args(); cfg = rates(); rng = np.random.default_rng(a.seed)
    lc, L = cfg["loss_cost"], cfg["loadings"]
    units = rng.integers(1, 6, a.policies)
    rel = np.exp(rng.normal(0, 0.25, a.policies))            # true risk relativity, which the rater is assumed to know exactly here
    lam = (lc["crash_rate_per_unit_year"] * lc["crash_to_claim_ratio"]) * units * rel
    n_claims = rng.poisson(lam)
    sev = lc["severity"]; limit = cfg["meta"]["base_limit_csl"]
    losses = np.zeros(a.policies)
    for i, k in enumerate(n_claims):
        for _ in range(k):
            comp = rng.choice(list(sev), p=[s["share"] for s in sev.values()]); s = sev[comp]
            if s["dist"] == "lognormal":
                sig2 = math.log(1 + s["cv"]**2); x = rng.lognormal(math.log(s["mean"]) - sig2/2, math.sqrt(sig2))
            else:
                x = s["threshold"] * (1 - rng.random()) ** (-1/s["alpha"])
            losses[i] += min(x, limit)
    lev = limited_mean(sev, limit)["limited_mean"]; trend = (1 + lc["severity_trend_annual"]) ** lc["trend_years"]
    loss_cost = (lc["crash_rate_per_unit_year"] * lc["crash_to_claim_ratio"]) * lev * rel * units
    prem = np.maximum(loss_cost * (1 + L["alae_ratio"]) / (1 - L["expense_ratio"] - L["reinsurance_ratio"] - L["profit_cost_of_capital"]),
                      L["minimum_premium_per_unit"] * units)
    target_lr = (1 + L["alae_ratio"]) * 0 + (loss_cost.sum() / prem.sum())   # pure loss cost / premium ignoring trend (sim is untrended)
    print(f"policies {a.policies}, unit-years {units.sum()}, claims {n_claims.sum()}")
    print(f"simulated loss ratio (pure, untrended): {losses.sum()/prem.sum():.3f}   expected from rates: {target_lr:.3f}")
    print(f"share of policies at minimum premium: {(prem == L['minimum_premium_per_unit']*units).mean():.1%}")
    print("If simulated != expected by more than ~0.02 at 20k policies the pipeline is broken. NB at 2,000 policies the noise is ~+/-0.10 — a real 2k-policy book swings 10+ LR points on a handful of limit losses. That is a finding for the margin story.")

if __name__ == "__main__":
    main()
