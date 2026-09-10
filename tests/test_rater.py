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

def test_vpic_live_shapes_classify_correctly():
    """Field strings copied from live vPIC batch responses 2026-09-09 (data/raw/vpic_sample.json)."""
    from rater import enrich, features
    C8 = "Class 8: 33,001 lb and above (14,969 kg and above)"
    live = {
        "1FUJGLDR3CLBP8834": {"Make": "FREIGHTLINER", "Model": "Cascadia", "ModelYear": "2012", "GVWR": C8, "BodyClass": "Truck-Tractor", "VehicleType": "TRUCK", "ErrorCode": "0"},
        "1XKYDP9XXFJ440749": {"Make": "KENWORTH", "Model": "T680", "ModelYear": "2015", "GVWR": C8, "BodyClass": "Truck-Tractor", "VehicleType": "TRUCK", "ErrorCode": "0"},
        "1JJV532D9JL178490": {"Make": "WABASH VANS", "Model": "Dry Van Duraplate", "ModelYear": "2018", "GVWR": "", "BodyClass": "Trailer", "VehicleType": "TRAILER", "ErrorCode": "0"},
        "1FTFW1ET9DFC10312": {"Make": "FORD", "Model": "F-150", "ModelYear": "2013", "GVWR": "Class 2F: 7,001 - 8,000 lb (3,175 - 3,629 kg)", "BodyClass": "Pickup", "VehicleType": "TRUCK", "ErrorCode": "0"},
        # garbage string: vPIC still returns a Make and VehicleType=TRAILER, with code 400 (invalid characters)
        "12345678901234567": {"Make": "SHERMAN + REILLY", "Model": "", "ModelYear": "", "GVWR": "", "BodyClass": "", "VehicleType": "TRAILER", "ErrorCode": "1,11,14,400"},
    }
    p = {v: enrich._parse_vin(v, r) for v, r in live.items()}
    assert [p[v]["decoded"] for v in live] == [True, True, True, True, False]
    assert not features._is_non_commercial(p["1FUJGLDR3CLBP8834"]) and not features._is_non_commercial(p["1XKYDP9XXFJ440749"])
    assert features._is_non_commercial(p["1JJV532D9JL178490"]) and features._is_non_commercial(p["1FTFW1ET9DFC10312"])
    # check-digit-only error (typo'd VIN) still decodes; class 3+ pickups stay commercial; SUVs (MPV) do not
    assert enrich._parse_vin("X", {"Make": "PETERBILT", "ErrorCode": "1"})["decoded"]
    assert not features._is_non_commercial({"vehicle_type": "TRUCK", "body_class": "Pickup", "gvwr": "Class 3: 10,001 - 14,000 lb (4,536 - 6,350 kg)"})
    assert features._is_non_commercial({"vehicle_type": "MULTIPURPOSE PASSENGER VEHICLE (MPV)", "body_class": "Sport Utility Vehicle (SUV)/Multi-Purpose Vehicle (MPV)", "gvwr": "Class 1D: 5,001 - 6,000 lb (2,268 - 2,722 kg)"})

def test_input_aliases_and_numeric_radius():
    """A reviewer's file that does not follow config/schema.json to the letter must still be priced, not declined D01."""
    canon = json.load(open(os.path.join(SUBS, "00_established_clean_ia.json")))
    alt = {"DOT_NUMBER": " USDOT 9900001 ", "vins": [u["vin"] for u in canon["units"]], "State": "ia",
           "radius": 300, "cargo": "Dry Van", "drivers": "3", "limit": "1m"}
    r = price(alt)
    assert r["decision"] == "price" and r["usdot"] == 9900001, r
    b = r["breakdown"]
    assert b["relativities"]["radius"]["band"] == "regional_201_500" and b["limit"] == 1000000 and b["units"] == 3
    fl = set(r["flags"])
    assert {"alias:DOT_NUMBER->usdot", "alias:vins->units", "alias:State->garaging_state", "alias:cargo->commodity",
            "drivers_given_as_count", "radius_miles:300->regional_201_500", "limit_parsed:1m->1000000"} <= fl, fl
    # the canonical file still produces no alias flags, and identical radius/units handling
    assert not any(f.startswith("alias:") for f in price(canon)["flags"])
    # bare unit count, VIN string, miles-as-text, list commodity
    n = ingest.normalise({"usdot": 1, "power_units": 2, "radius": "500+ miles", "commodity": ["reefer"], "units": None})
    assert n["declared_units"] == 2 and n["vins"] == [] and n["radius"] == "long_haul_500_plus" and n["commodity"] == "reefer"
    n = ingest.normalise({"usdot": 1, "units": "1FUJGLDR00LLA6929", "radius": "regional", "limit": "750,000"})
    assert n["vins"] == ["1FUJGLDR00LLA6929"] and n["declared_units"] == 1 and n["limit"] == 750000

def test_book_summary_runs():
    from rater import book
    res = book.run([SUBS])
    txt = book.summarise(res)
    assert "Decline rate" in txt and "Errored submissions (1)" in txt and "55_edge_not_json.json: unreadable json" in txt
    assert {r["decision"] for r in res} == {"price", "refer", "decline", "error"}

def test_monotone_new_venture_costs_more():
    base = json.load(open(os.path.join(SUBS, "00_established_clean_ia.json")))
    cfg = rates(); import copy
    p0 = price(base, cfg)["breakdown"]["relativity_product_raw"]
    c2 = copy.deepcopy(cfg); c2["relativities"]["authority_age_years"][0]["factor"] = 2.0
    assert price(base, c2)["breakdown"]["relativity_product_raw"] >= p0

# --- 2026-09-10 fixes: dead crash rule, credibility off-balance, unenforced limits ------------------------

def _crash_carrier(crashes, fatal=0, units=None):
    """A real cached carrier with its crash counts overridden, so the crash rules can be exercised offline."""
    from rater import enrich
    real = enrich.fetch_carrier(1000986)
    return {**real, "crashes_total": crashes, "fatal_crashes": fatal, "injury_crashes": 0,
            "safety_rating": None, "power_units": units}

def _price_with(carrier, **sub):
    from rater import enrich
    orig = enrich.fetch_carrier
    enrich.fetch_carrier = lambda dot: carrier
    try:
        return price({"usdot": 1000986, "commodity": "dry_van", **sub})
    finally:
        enrich.fetch_carrier = orig

def test_d20_threshold_is_reachable_in_the_1_to_5_unit_segment():
    """D20 used to test cred_rate_relativity > 3.0. That relativity caps the own rate at 3x and then credibility-
    weights it, so its ceiling is 1 + 2Z = 1.571 at five units: the rule could not fire for any carrier in
    appetite, and a 2-unit carrier with 12 crashes in 24 months priced clean at the minimum premium."""
    cfg = rates(); cr = cfg["credibility"]
    ceiling = max((u * cr["history_years"] / (u * cr["history_years"] + cr["k_unit_years"])) * (cr["own_rate_cap_multiple"] - 1) + 1
                  for u in range(1, 6))
    d20 = next(r for r in rules.load_rules() if r["id"] == "D20")
    assert d20["when"]["all"][0]["field"] == "own_crash_rate_ratio", "D20 must test the uncapped ratio"
    assert d20["when"]["all"][0]["value"] > 1.0
    assert ceiling < 3.0, "sanity: the old threshold really was unreachable"
    r = _price_with(_crash_carrier(12), power_units=2, driver_count=2, garaging_state="IA", radius="local_0_50")
    assert r["decision"] == "decline" and any(x["id"] == "D20" for x in r["rules_fired"])

def test_adverse_crash_record_cannot_price_at_the_clean_floor():
    """The $8,000 floor is the market price for a clean risk. Applied flat it levelled the book: a carrier with
    three crashes in 24 months paid exactly what a crash-free one paid, because its surcharge sat under the floor."""
    clean = _price_with(_crash_carrier(0), power_units=1, driver_count=1, garaging_state="IA", radius="local_0_50")
    crashed = _price_with(_crash_carrier(1), power_units=1, driver_count=1, garaging_state="IA", radius="local_0_50")
    assert clean["breakdown"]["unit_premium"] == clean["breakdown"]["minimum_premium_base"]
    assert clean["breakdown"]["min_premium_binding"] and crashed["breakdown"]["min_premium_binding"]
    # both sit under the technical premium, i.e. both are floor-priced - and they must still differ
    assert crashed["breakdown"]["unit_premium"] > clean["breakdown"]["unit_premium"]
    # one crash on one truck is priced, not referred: at Z = 0.07 the model's own position is that it is noise
    assert clean["decision"] == "price" and crashed["decision"] == "price"
    # A second crash cannot show up in PRICE on a one-truck fleet: own_rate_cap_multiple = 3.0 is already saturated
    # by the first (1 crash / 2 unit-years = 11x segment), so 1 and 5 crashes cost the same. That saturation is
    # deliberate - the cap is what stops a noisy one-truck record dominating - but it is exactly why the crash
    # rules gate on the raw COUNT as well as the ratio: past the cap, only the rules can tell the two apart.
    twice = _price_with(_crash_carrier(2), power_units=1, driver_count=1, garaging_state="IA", radius="local_0_50")
    assert twice["breakdown"]["unit_premium"] == crashed["breakdown"]["unit_premium"]
    assert twice["decision"] == "refer" and any(x["id"] == "R10" for x in twice["rules_fired"])
    assert _price_with(_crash_carrier(3), power_units=1, driver_count=1,
                       garaging_state="IA", radius="local_0_50")["decision"] == "decline"

def test_credibility_is_balanced():
    """The 3x cap truncates the upside of the own-experience relativity but nothing truncates the downside, so
    without the off-balance divisor E[cred_rel] < 1 and the whole procedure is a 4-7% discount on every risk."""
    from rater.losscost import credibility_relativity, _expected_relativity
    import copy
    cfg = rates(); cr = cfg["credibility"]; seg = cfg["loss_cost"]["crash_rate_per_unit_year"]
    off = copy.deepcopy(cfg); off["credibility"]["offbalance_correction"] = False
    for units in (1, 2, 3, 5):
        n = units * cr["history_years"]; Z = n / (n + cr["k_unit_years"])
        expected_uncorrected = _expected_relativity(n, seg, cr["own_rate_cap_multiple"], Z)
        assert expected_uncorrected < 0.98, (units, expected_uncorrected)   # the leakage this fixes
        # with the correction on, a carrier whose record IS the segment average prices at 1.00
        cred = credibility_relativity({"power_units": units, "crashes_24m": 0}, None, cfg)
        cred_off = credibility_relativity({"power_units": units, "crashes_24m": 0}, None, off)
        assert cred["cred_rate_relativity"] > cred_off["cred_rate_relativity"]
        assert abs(cred["offbalance_divisor"] - expected_uncorrected) < 1e-9

def test_offered_limits_are_enforced():
    """limits.offered was documentation, not a rule: a $5m CSL bound at 9.3% above the $1m price."""
    cfg = rates()
    base = dict(power_units=2, driver_count=2, garaging_state="TX", radius="long_haul_500_plus")
    at_1m = _price_with(_crash_carrier(0), limit=1000000, **base)
    at_2m = _price_with(_crash_carrier(0), limit=2000000, **base)
    at_5m = _price_with(_crash_carrier(0), limit=5000000, **base)
    assert 5000000 not in cfg["limits"]["offered"]
    assert at_1m["decision"] == "price"
    assert at_2m["decision"] == "refer" and any(x["id"] == "R12" for x in at_2m["rules_fired"])
    assert at_5m["decision"] == "decline" and any(x["id"] == "D32" for x in at_5m["rules_fired"])
