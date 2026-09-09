import os, json, glob
os.environ["RATER_OFFLINE"] = "1"
from rater.price import price
from rater import ingest, rules
from rater.losscost import limited_mean
from rater.config import rates

SUBS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "submissions")

def test_never_crashes_on_any_sample():
    for fp in glob.glob(os.path.join(SUBS, "*.json")):
        try: sub = json.load(open(fp))
        except Exception: continue
        r = price(sub); assert r["decision"] in ("price", "refer", "decline"), (fp, r.get("error"))

def test_garbage_input():
    for sub in ({}, {"usdot": None}, {"usdot": "abc", "units": 5, "drivers": {"a": 1}}, {"usdot": 12, "limit": -3}):
        r = price(sub); assert r["decision"] != "error", r.get("error")

def test_breakdown_reconciles():
    r = price(json.load(open(os.path.join(SUBS, "00_established_clean_ia.json"))))
    b = r["breakdown"]; assert r["decision"] == "price"
    assert abs(b["unit_premium"] * b["units"] + b["policy_fee"] - r["premium"]) < 0.01
    assert b["unit_premium"] >= b["minimum_premium_per_unit"]

def test_manual_matches_code():
    cfg = rates(); lc = cfg["loss_cost"]
    lev = limited_mean(lc["severity"], cfg["meta"]["base_limit_csl"])["limited_mean"]
    r = price(json.load(open(os.path.join(SUBS, "00_established_clean_ia.json"))))
    assert abs(r["breakdown"]["loss_cost_inputs"]["limited_severity"] - lev) < 1e-6

def test_decline_rules_fire():
    r = price(json.load(open(os.path.join(SUBS, "09_unsat_rating_mo.json"))))
    assert r["decision"] == "decline" and any(x["id"] == "D04" for x in r["rules_fired"])

def test_thin_data_is_referred_not_declined():
    r = price(json.load(open(os.path.join(SUBS, "02_new_venture_ga.json"))))
    assert r["decision"] == "refer" and r["premium"] is not None

def test_monotone_new_venture_costs_more():
    base = json.load(open(os.path.join(SUBS, "00_established_clean_ia.json")))
    cfg = rates(); import copy
    p0 = price(base, cfg)["breakdown"]["relativity_product_raw"]
    c2 = copy.deepcopy(cfg); c2["relativities"]["authority_age_years"][0]["factor"] = 2.0
    assert price(base, c2)["breakdown"]["relativity_product_raw"] >= p0
