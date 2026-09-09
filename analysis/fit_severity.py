"""Severity mixture -> limited means and ILFs; lognormal-only vs mixture-with-Pareto-tail comparison.
Run: python -m analysis.fit_severity"""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rater.config import rates
from rater.losscost import limited_mean

def lognormal_only(sev, limit, n=200000, seed=7):
    """Single lognormal matched to the mixture's ground-up mean and CV (the naive alternative)."""
    rng = np.random.default_rng(seed)
    # moments of mixture by simulation
    xs = []
    for s in sev.values():
        if s["dist"] == "lognormal":
            sig2 = math.log(1 + s["cv"]**2); mu = math.log(s["mean"]) - sig2/2
            xs.append((s["share"], rng.lognormal(mu, math.sqrt(sig2), n)))
        else:
            xs.append((s["share"], s["threshold"] * (1 - rng.random(n)) ** (-1/s["alpha"])))
    pick = rng.choice(len(xs), n, p=[w for w, _ in xs]); mix = np.array([xs[i][1][j] for j, i in enumerate(pick)])
    mix = np.minimum(mix, 5e7)   # truncate simulated Pareto for a finite CV
    m, sd = mix.mean(), mix.std(); cv = sd / m
    sig2 = math.log(1 + cv**2); mu = math.log(m) - sig2/2
    x = rng.lognormal(mu, math.sqrt(sig2), n)
    return float(np.minimum(x, limit).mean())

def main():
    cfg = rates(); sev = cfg["loss_cost"]["severity"]
    limits = [250000, 500000, 750000, 1000000, 2000000, 5000000]
    base = 1000000
    print(f"{'limit':>10} {'mixture LEV':>14} {'ILF(mix)':>9} {'lognormal LEV':>14} {'ILF(ln)':>9}")
    lm_base = limited_mean(sev, base)["limited_mean"]; ln_base = lognormal_only(sev, base)
    rows = []
    for L in limits:
        lm = limited_mean(sev, L)["limited_mean"]; ln = lognormal_only(sev, L)
        rows.append((L, lm, lm/lm_base, ln, ln/ln_base))
        print(f"{L:>10,} {lm:>14,.0f} {lm/lm_base:>9.3f} {ln:>14,.0f} {ln/ln_base:>9.3f}")
    print("\nComponents at $1m:", {k: round(v['limited_mean']) for k, v in limited_mean(sev, base)['components'].items()})
    os.makedirs("data/derived", exist_ok=True)
    with open("data/derived/ilf_table.csv", "w") as f:
        f.write("limit,mixture_lev,ilf_mixture,lognormal_lev,ilf_lognormal\n")
        for r in rows: f.write(",".join(str(round(x, 4)) for x in r) + "\n")
    print("\nSlide line: the tail assumption is what separates the $2m/$5m price; at $1m primary the limit does most of the truncation.")

if __name__ == "__main__":
    main()
