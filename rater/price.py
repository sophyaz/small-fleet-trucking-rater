"""price(submission) -> dict. Never raises for bad input; errors are returned in the dict."""
import traceback
from . import ingest, enrich, features as feat, losscost, rules
from .config import rates

def _band(table, x):
    if x is None: return 1.0, "n/a"
    for row in table:
        if x <= row["max"]:
            return float(row["factor"]), f"<= {row['max']}"
    return float(table[-1]["factor"]), "top"

def relativities(f: dict, cfg: dict) -> dict:
    R = cfg["relativities"]; out = {}
    out["authority_age"] = _band(R["authority_age_years"], f["authority_age_years"])
    out["fleet_size"] = _band(R["fleet_size_units"], f["power_units"])
    out["radius"] = (float(R["radius_miles"].get(f["radius"], 1.0)), f["radius"])
    out["commodity"] = (float(R["commodity"].get(f["commodity"], R["commodity"]["unknown"])), f["commodity"])
    vf, vlab = 1.0, "neutral"
    for tier, spec in R["venue_state"].items():
        if f.get("state") in spec["states"]:
            vf, vlab = float(spec["factor"]), f"{tier}:{f['state']}"
    out["venue_state"] = (vf, vlab)
    out["driver_unit_ratio"] = _band(R["driver_unit_ratio"], f["driver_unit_ratio"])
    out["driver_experience"] = _band(R["driver_experience_years_min"], f.get("driver_experience_min"))
    out["vehicle_age"] = _band(R["vehicle_age_years_avg"], f.get("vehicle_age_avg"))
    oos = R["oos_ratio_to_segment_avg"]
    if f["total_inspections"] >= oos["min_inspections"]:
        out["driver_oos"] = _band(oos["driver"], f["driver_oos_ratio"])
        out["vehicle_oos"] = _band(oos["vehicle"], f["vehicle_oos_ratio"])
    else:
        out["driver_oos"] = (1.0, "insufficient inspections"); out["vehicle_oos"] = (1.0, "insufficient inspections")
    for b, table in R["basic_percentile"].items():
        key = "basic_" + b
        if f.get(key) is not None:
            out[key] = _band(table, f[key])
    out["mcs150_stale"] = _band(R["mcs150_stale_years"], f["mcs150_age_years"])
    if f["radius"] in (R.get("mileage_intensity_skip_radii") or []):
        out["mileage_intensity"] = (1.0, f"skipped: radius {f['radius']} already prices mileage")
    else:
        out["mileage_intensity"] = _band(R["mileage_intensity"], f.get("mileage_per_unit"))
    out["experience_credibility"] = (f["cred_rate_relativity"], f"Z={f['cred_Z']:.2f}")
    # stack cap: the product of the named factors (authority x venue x radius) is capped before anything else applies
    sc = R.get("stack_cap")
    if sc:
        prod = 1.0
        for k in sc["factors"]:
            prod *= out[k][0]
        if prod > float(sc["max"]):
            out["stack_cap"] = (float(sc["max"]) / prod, f"{'x'.join(sc['factors'])}={prod:.3f} capped at {sc['max']}")
    return out

def price(submission: dict, cfg=None) -> dict:
    cfg = cfg or rates()
    try:
        sub = ingest.normalise(submission)
        car = enrich.fetch_carrier(sub["usdot"]) if sub["usdot"] else {"found": False, "degraded": False}
        vins = enrich.decode_vins(sub["vins"])
        f = feat.build(sub, car, vins, cfg)
        lc = losscost.expected_loss_per_unit(f, cfg)
        cred = losscost.credibility_relativity(f, lc["base_frequency"], cfg)
        f["cred_rate_relativity"] = cred["cred_rate_relativity"]; f["cred_Z"] = cred["Z"]
        # D20 tests the uncapped ratio, not the priced relativity - see losscost.credibility_relativity
        f["own_crash_rate_ratio"] = cred["own_crash_rate_ratio"]
        verdict = rules.evaluate(f)
        rel = relativities(f, cfg)
        product = 1.0
        for k, (fac, _) in rel.items():
            product *= fac
        cap = cfg["relativities"]["total_cap"]
        product_capped = min(cap["max"], max(cap["min"], product))
        L = cfg["loadings"]
        loss_cost_unit = lc["base_loss_cost_per_unit"] * product_capped
        alae = loss_cost_unit * L["alae_ratio"]
        loaded_loss = loss_cost_unit + alae
        denom = 1 - L["expense_ratio"] - L["reinsurance_ratio"] - L["profit_cost_of_capital"]
        tech_unit = loaded_loss / denom
        # The floor is the market price for a CLEAN risk. Scaled by the experience relativity when that is a
        # surcharge, so an adverse crash record cannot fall back to the clean-risk floor (never scaled by a
        # discount: max(1.0, .) keeps every clean risk at the $8,000 anchor). config/rates.yaml loadings.
        min_unit_base = L["minimum_premium_per_unit"]
        exp_scale = max(1.0, cred["cred_rate_relativity"]) if L.get("minimum_premium_experience_scaled") else 1.0
        min_unit = min_unit_base * exp_scale
        unit_premium = max(tech_unit, min_unit)
        units = f["power_units"]
        premium = unit_premium * units + L["policy_fee"]
        breakdown = {
            "units": units, "limit": f["limit"],
            "base_loss_cost_per_unit": round(lc["base_loss_cost_per_unit"], 2),
            "relativity_product_raw": round(product, 4), "relativity_product_capped": round(product_capped, 4),
            "relativities": {k: {"factor": round(v[0], 4), "band": v[1]} for k, v in rel.items()},
            "loss_cost_per_unit": round(loss_cost_unit, 2), "alae_per_unit": round(alae, 2),
            "technical_premium_per_unit": round(tech_unit, 2), "minimum_premium_per_unit": round(min_unit, 2),
            "minimum_premium_base": min_unit_base, "minimum_premium_experience_scale": round(exp_scale, 4),
            "min_premium_binding": tech_unit < min_unit, "unit_premium": round(unit_premium, 2),
            "policy_fee": L["policy_fee"], "implied_loss_ratio": round(loaded_loss / unit_premium, 3),
            "loadings": {k: L[k] for k in ("alae_ratio", "expense_ratio", "reinsurance_ratio", "profit_cost_of_capital")},
            "credibility": cred, "loss_cost_inputs": {k: lc[k] for k in ("base_frequency", "limited_severity", "trend_factor")},
        }
        return {"submission_id": sub["submission_id"], "usdot": sub["usdot"], "decision": verdict["decision"],
                "premium": round(premium, 2) if verdict["decision"] != "decline" else None,
                "premium_if_written": round(premium, 2), "rules_fired": verdict["rules_fired"],
                "flags": f["flags"], "enrichment_source": car.get("source"), "breakdown": breakdown,
                "features": {k: v for k, v in f.items() if k not in ("flags",)}, "error": None}
    except Exception as e:   # last line of defence: never crash the book run
        # `submission` is not necessarily a dict here - book.py guards its own call, but a caller using price()
        # directly can pass anything, and .get() on a str/list would raise *inside the handler*, taking out the
        # one guarantee this function makes. Not reachable today (ingest.normalise absorbs non-dicts before
        # anything can throw), which is exactly why it is worth pinning: the safety net must not need luck.
        sub = submission if isinstance(submission, dict) else {}
        return {"submission_id": str(sub.get("submission_id", "?")), "usdot": sub.get("usdot"),
                "decision": "error", "premium": None, "rules_fired": [], "flags": [], "breakdown": {},
                "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()}
