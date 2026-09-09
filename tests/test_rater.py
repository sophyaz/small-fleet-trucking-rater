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

def _live_shaped_carrier(**over):
    """Mimics enrich._parse_carrier output for a live QCMobile response (see rater/enrich.py docstring)."""
    car = {"found": True, "degraded": False, "power_units": 3, "drivers": 3, "allowed_to_operate": True, "status_code": "A",
           "active_for_hire_authority": True, "in_census": True, "census_power_units": 3.0, "add_date": "28-JAN-02",
           "mcs150_date": "09-MAY-26", "operation_classification": ["authorized for hire"], "carrier_operation": "Interstate",
           "basics": {}, "cargo": [], "hazmat_flag": False, "passenger_flag": False}
    car.update(over); return car

def test_inactive_registration_and_authority_rules():
    from rater import features
    sub = ingest.normalise(json.load(open(os.path.join(SUBS, "00_established_clean_ia.json"))))
    ok = rules.evaluate(features.build(sub, _live_shaped_carrier(), []))
    assert not any(r["id"] in ("D05", "D31", "R07", "R08") for r in ok["rules_fired"])
    # statusCode "I" with allowedToOperate "Y" (real case: DOT 3456789) must decline on D05
    r = rules.evaluate(features.build(sub, _live_shaped_carrier(status_code="I"), []))
    assert r["decision"] == "decline" and any(x["id"] == "D05" for x in r["rules_fired"])
    # no active MC authority / absent from census -> refer, not decline
    r = rules.evaluate(features.build(sub, _live_shaped_carrier(active_for_hire_authority=False, in_census=False), []))
    assert r["decision"] == "refer" and {x["id"] for x in r["rules_fired"]} >= {"R07", "R08"}
    # census 0 units vs 3 declared is a mismatch (was silently skipped because 0 is falsy)
    f = features.build(sub, _live_shaped_carrier(power_units=0, census_power_units=0.0), [])
    assert f["unit_count_mismatch"] is True and "census_units_zero" in f["flags"]
    assert any(x["id"] == "D31" for x in rules.evaluate(f)["rules_fired"])
    # unknown signals (synthetic fixtures carry None) must not fire the new rules
    f = features.build(sub, _live_shaped_carrier(active_for_hire_authority=None, in_census=None), [])
    assert f["active_for_hire_authority"] is True and f["in_census"] is True

def test_empty_operation_classification_is_unknown_not_private():
    """Real DOTs 4634703, 5509576, ... (June-July 2026 registrations): QCMobile returns [] for operation-classification.
    That must not fire D12; positive evidence of private / intrastate operation still must."""
    from rater import features
    sub = ingest.normalise(json.load(open(os.path.join(SUBS, "00_established_clean_ia.json"))))
    f = features.build(sub, _live_shaped_carrier(operation_classification=[], common_authority_status=None,
                                                 census_authorized_for_hire=True), [])
    assert f["for_hire_interstate"] is True and "operation_classification_missing" in f["flags"]
    r = rules.evaluate(f); ids = {x["id"] for x in r["rules_fired"]}
    assert "D12" not in ids and "R09" in ids and r["decision"] == "refer"
    f = features.build(sub, _live_shaped_carrier(operation_classification=["private property"]), [])
    assert f["for_hire_interstate"] is False
    f = features.build(sub, _live_shaped_carrier(carrier_operation="Intrastate Non-Hazmat"), [])
    assert f["for_hire_interstate"] is False   # was never caught before: desc is title-case, check was lower-case
    f = features.build(sub, _live_shaped_carrier(operation_classification=[], census_authorized_for_hire=False), [])
    assert f["for_hire_interstate"] is False

def test_lapsed_authority_declines_pending_applicant_refers():
    from rater import features
    sub = ingest.normalise(json.load(open(os.path.join(SUBS, "00_established_clean_ia.json"))))
    # real DOT 3987512 shape: common I, contract N, bipdInsuranceOnFile 0 -> authority revoked, decline
    lapsed = _live_shaped_carrier(bipd_insurance_on_file_k=0.0, bipd_required_k=750.0, active_for_hire_authority=False,
                                  common_authority_status="I", contract_authority_status="N")
    r = rules.evaluate(features.build(sub, lapsed, []))
    assert r["decision"] == "decline" and any(x["id"] == "D25" for x in r["rules_fired"])
    # real DOT 4529032 shape: N/N with no filing = applicant waiting on a BMC-91 -> refer only
    pending = _live_shaped_carrier(bipd_insurance_on_file_k=0.0, bipd_required_k=750.0, active_for_hire_authority=False,
                                   common_authority_status="N", contract_authority_status="N")
    r = rules.evaluate(features.build(sub, pending, []))
    assert r["decision"] == "refer" and not any(x["id"] == "D25" for x in r["rules_fired"])
    # inactive authority but a filing IS on record (reinstatement in progress) -> not D25
    r = rules.evaluate(features.build(sub, _live_shaped_carrier(bipd_insurance_on_file_k=750.0, common_authority_status="I"), []))
    assert not any(x["id"] == "D25" for x in r["rules_fired"])
    # unknown filing (synthetic fixture) never fires
    r = rules.evaluate(features.build(sub, _live_shaped_carrier(bipd_insurance_on_file_k=None, common_authority_status="I"), []))
    assert not any(x["id"] == "D25" for x in r["rules_fired"])

def test_placeholder_mileage_gets_no_discount():
    from rater import features
    from rater.price import relativities
    sub = ingest.normalise(json.load(open(os.path.join(SUBS, "00_established_clean_ia.json"))))
    cfg = rates()
    f = features.build(sub, _live_shaped_carrier(mcs150_mileage=1), [], cfg)
    assert f["mileage_per_unit"] is None and "mcs150_mileage_implausible" in f["flags"]
    f["cred_rate_relativity"], f["cred_Z"] = 1.0, 0.0
    assert relativities(f, cfg)["mileage_intensity"] == (1.0, "n/a")
    f = features.build(sub, _live_shaped_carrier(mcs150_mileage=60000), [], cfg)   # 20k per unit on 3 units: real low mileage
    assert f["mileage_per_unit"] == 20000 and "mcs150_mileage_implausible" not in f["flags"]

def test_monotone_new_venture_costs_more():
    base = json.load(open(os.path.join(SUBS, "00_established_clean_ia.json")))
    cfg = rates(); import copy
    p0 = price(base, cfg)["breakdown"]["relativity_product_raw"]
    c2 = copy.deepcopy(cfg); c2["relativities"]["authority_age_years"][0]["factor"] = 2.0
    assert price(base, c2)["breakdown"]["relativity_product_raw"] >= p0
