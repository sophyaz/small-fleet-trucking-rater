"""Frequency x severity -> expected loss per power-unit-year, limited to the policy limit."""
import math
import numpy as np
from .config import rates

def limited_mean(sev_cfg: dict, limit: float, n: int = 200000, seed: int = 7) -> dict:
    """Monte-Carlo limited expected severity E[min(X, L)] for the mixture. Deterministic seed."""
    rng = np.random.default_rng(seed)
    parts, total = {}, 0.0
    for name, s in sev_cfg.items():
        share = s["share"]
        if s["dist"] == "lognormal":
            m, cv = s["mean"], s["cv"]
            sigma2 = math.log(1 + cv**2); mu = math.log(m) - sigma2 / 2
            x = rng.lognormal(mu, math.sqrt(sigma2), n)
        elif s["dist"] == "pareto":
            xm, a = s["threshold"], s["alpha"]
            x = xm * (1 - rng.random(n)) ** (-1 / a)
        else:
            raise ValueError(s["dist"])
        lm = float(np.minimum(x, limit).mean())
        parts[name] = {"share": share, "limited_mean": lm, "ground_up_mean_sample": float(x.mean())}
        total += share * lm
    return {"limited_mean": total, "components": parts}

def expected_loss_per_unit(features: dict, cfg=None) -> dict:
    cfg = cfg or rates()
    lc = cfg["loss_cost"]
    freq = lc["crash_rate_per_unit_year"] * lc["crash_to_claim_ratio"]
    sev = limited_mean(lc["severity"], features["limit"])
    trend = (1 + lc["severity_trend_annual"]) ** lc["trend_years"]
    base = freq * sev["limited_mean"] * trend
    return {"base_frequency": freq, "limited_severity": sev["limited_mean"], "trend_factor": trend,
            "base_loss_cost_per_unit": base, "severity_components": sev["components"]}

def credibility_relativity(features: dict, base_freq: float, cfg=None) -> dict:
    """Bühlmann-style blend of carrier-own crash rate with segment rate. Returns relativity to apply."""
    cfg = cfg or rates()
    cr = cfg["credibility"]
    units = max(1, features.get("power_units") or 1)
    n_unit_years = units * cr["history_years"]
    Z = n_unit_years / (n_unit_years + cr["k_unit_years"])
    crash_freq_seg = cfg["loss_cost"]["crash_rate_per_unit_year"]   # segment DOT-recordable crash rate
    own_rate = features.get("crashes_24m", 0) / n_unit_years
    own_rel = min(cr["own_rate_cap_multiple"], own_rate / crash_freq_seg) if crash_freq_seg else 1.0
    rel = Z * own_rel + (1 - Z) * 1.0
    return {"Z": Z, "unit_years": n_unit_years, "own_crash_rate": own_rate, "segment_crash_rate": crash_freq_seg,
            "own_relativity_capped": own_rel, "cred_rate_relativity": rel}
