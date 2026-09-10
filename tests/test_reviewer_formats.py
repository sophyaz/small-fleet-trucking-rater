"""Submissions in shapes we were never given.

The brief judges the rater by running carriers through it, "including cases you won't have seen". These are the
input shapes a reviewer plausibly hands over: a spreadsheet export, an agency feed, a broker's array, a CSV of
DOTs, a wrapped object, half-empty fields. Every one must return a decision -- never a traceback, never a silent
misread of which carrier is being rated.
"""
import glob, json, os
os.environ["RATER_OFFLINE"] = "1"
from rater import book, ingest
from rater.price import price

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMATS = os.path.join(ROOT, "samples", "reviewer_formats")

# ---------------------------------------------------------------- value coercion

def test_float_usdot_is_not_a_different_carrier():
    """A DOT out of Excel/pandas arrives as 9900001.0. Stripping non-digits made that 99000010 -- a real, and
    wrong, carrier. Parse as a number first."""
    assert ingest.normalise({"usdot": 9900001.0})["usdot"] == 9900001
    assert ingest.normalise({"usdot": "9900001.0"})["usdot"] == 9900001
    assert ingest.normalise({"usdot": "3456789.00"})["usdot"] == 3456789
    assert price({"usdot": 9900001.0})["usdot"] == 9900001

def test_usdot_from_text_is_flagged():
    """Digits pulled out of free text are right often enough to use, but the source must be visible: MC-429079
    is a docket number, not a DOT."""
    n = ingest.normalise({"usdot": "MC-429079"})
    assert n["usdot"] == 429079 and any(f.startswith("usdot_parsed_from_text") for f in n["ingest_flags"])
    n = ingest.normalise({"usdot": "USDOT# 1,000,986"})
    assert n["usdot"] == 1000986
    # a clean integer is not flagged (the other flags here are the missing optional fields)
    assert not any("usdot" in f for f in ingest.normalise({"usdot": 1000986})["ingest_flags"])

def test_nested_submission_is_unwrapped():
    n = ingest.normalise({"producer": "Acme", "radius": "local", "carrier": {"usdot": 9900001, "commodity": "reefer"}})
    assert n["usdot"] == 9900001 and "unwrapped:carrier" in n["ingest_flags"]
    assert n["commodity"] == "reefer" and n["radius"] == "local_0_50"   # both levels are read
    # a top-level USDOT wins; nothing is unwrapped
    n = ingest.normalise({"usdot": 123, "carrier": {"usdot": 456}})
    assert n["usdot"] == 123 and not any(f.startswith("unwrapped") for f in n["ingest_flags"])

def test_full_state_names_and_radius_objects():
    n = ingest.normalise({"usdot": 1, "garaging_state": "New Jersey"})
    assert n["garaging_state"] == "NJ" and "state_name:NEW JERSEY->NJ" in n["ingest_flags"]
    assert ingest.normalise({"usdot": 1, "state": "iowa"})["garaging_state"] == "IA"
    n = ingest.normalise({"usdot": 1, "radius": {"miles": 400}})
    assert n["radius"] == "regional_201_500"

def test_near_miss_radius_bands_resolve_instead_of_defaulting_cheap():
    """A band name that is close but not exact must not fall through to the neutral default. "long_haul_501_plus"
    priced at 1.00 instead of 1.30 -- a long-haul risk 30% light, with only a flag to show for it."""
    for given in ("long_haul_501_plus", "LongHaul", "long haul", "501+", "500_plus", "500+ mi", "long_distance"):
        n = ingest.normalise({"usdot": 1, "radius": given})
        assert n["radius"] == "long_haul_500_plus", (given, n["radius"])
    assert ingest.normalise({"usdot": 1, "radius": "local_radius"})["radius"] == "local_0_50"
    assert ingest.normalise({"usdot": 1, "radius": "51_200"})["radius"] == "intermediate_51_200"
    # absent vs present-but-unreadable both price at the neutral band, but must not look alike in the flags
    assert "radius_missing_default_intermediate" in ingest.normalise({"usdot": 1})["ingest_flags"]
    bad = ingest.normalise({"usdot": 1, "radius": "banana"})
    assert bad["radius"] == "intermediate_51_200"
    assert "radius_unparseable:banana->default_intermediate" in bad["ingest_flags"]

def test_split_limits_are_flagged_not_invented():
    """We write CSL. A split-limit string must not be silently turned into a number."""
    n = ingest.normalise({"usdot": 1, "limit": "1000/1000/1000"})
    assert n["limit"] == 1000000 and any(f.startswith("limit_split_form_not_offered") for f in n["ingest_flags"])

# ---------------------------------------------------------------- never crash

def test_hostile_shapes_all_return_a_decision():
    cases = [
        {}, [], "not a dict", None,
        {"usdot": None}, {"usdot": "abc"}, {"usdot": -5, "power_units": -2, "drivers": -1},
        {"usdot": 9900001, "drivers": ["John D", "Ann B"]},                       # driver names, not objects
        {"usdot": 9900001, "units": [{"year": 2019, "make": "Freightliner"}]},    # units without VINs
        {"usdot": 9900001, "drivers": None, "units": None, "radius": None, "commodity": None, "limit": None},
        {"usdot": 9900001, "weird": {"a": [1, 2, {"b": None}]}, "commodity": "General Freight LTL"},
        {"usdot": 9900001, "power_units": 999},                                   # out of segment -> decline, not crash
        {"usdot": 9900001, "units": "1FUJGLDR00LLA6929", "truck_count": 1},       # single VIN string
        {"usdot": 9900001, "radius": "500+ miles", "commodity": ["reefer"]},
    ]
    for c in cases:
        r = price(c if isinstance(c, dict) else {})
        assert r["decision"] in ("price", "refer", "decline"), (c, r.get("error"))

# ---------------------------------------------------------------- container shapes

def test_book_reads_array_jsonl_and_csv():
    """One file may carry many carriers. Each becomes its own row, tagged <file>#<i>."""
    res = book.run([FORMATS])
    by_file = {r["_file"]: r for r in res}
    assert len(res) == 16, sorted(by_file)
    for stem, n in (("02_broker_array.json", 3), ("03_agency_feed.jsonl", 3), ("04_dot_list.csv", 4)):
        rows = [r for r in res if r["_file"].startswith(stem)]
        assert len(rows) == n, (stem, len(rows))
        assert all(r["decision"] != "error" for r in rows), stem
    # the deliberately broken file is one error row, and does not stop the run
    errs = [r for r in res if r["decision"] == "error"]
    assert len(errs) == 1 and errs[0]["_file"] == "09_broken.json"

def test_reviewer_formats_folder_prices_and_never_errors_unexpectedly():
    res = book.run([FORMATS])
    live = [r for r in res if r["_file"] != "09_broken.json"]
    assert all(r["decision"] in ("price", "refer", "decline") for r in live)
    assert sum(1 for r in live if r["decision"] == "price") >= 11
    # Nothing here refers or declines for a reason other than one of the known ones: R02 (the fake DOT, priced on
    # segment defaults), R10 (adverse own crash record) and R12 ($2m limit, ILF too thin to bind automatically).
    # Guards the count above against drifting downward for a reason nobody looked at.
    for r in live:
        if r["decision"] != "price":
            assert {x["id"] for x in r["rules_fired"]} <= {"R02", "R10", "R12"}, (r["_file"], r["rules_fired"])
    # an unknown DOT is referred on segment defaults, never an error or a thin-data decline
    unknown = next(r for r in res if str(r.get("usdot")) == "9999999999")
    assert unknown["decision"] == "refer" and unknown["premium"] and any(x["id"] == "R02" for x in unknown["rules_fired"])
    assert "Decline rate" in book.summarise(res)

def test_partially_read_file_is_named_in_the_printed_summary(tmp_path):
    """A corrupt line in a feed is counted and skipped, but it used to appear only in a flags column. Hand over
    20 carriers, get 19 on screen, nobody notices. The summary has to say which file lost rows."""
    fp = tmp_path / "feed.jsonl"
    fp.write_text(json.dumps({"usdot": 9900001, "power_units": 1}) + "\n"
                  + "{ not json at all\n"
                  + json.dumps({"usdot": 9900001, "power_units": 2}) + "\n")
    res = book.run([str(fp)])
    assert len(res) == 2 and all(r["decision"] != "error" for r in res)
    out = book.summarise(res)
    assert "Files read only in part (1)" in out
    assert "feed.jsonl: 1 unparseable line skipped" in out, out
    # a clean file adds no such section
    assert "Files read only in part" not in book.summarise(book.run([FORMATS]))

def test_every_format_file_parses():
    """Guards against a demo file being edited into something unreadable."""
    files = glob.glob(os.path.join(FORMATS, "*.*"))
    assert len(files) >= 9
    for fp in files:
        subs, err = book._load(fp)
        if os.path.basename(fp) == "09_broken.json":
            assert err and not subs
        else:
            assert subs and err is None, (fp, err)

# ---------------------------------------------------------------- clean-clone parity

def test_slim_census_fallback_supplies_registration_dates():
    """QCMobile returns no addDate. Without a census snapshot every live carrier would look 0.5 years old and
    refer on R01, so a fresh clone must fall back to the committed slim extract and get the same dates."""
    import importlib
    from rater import enrich
    assert os.path.exists(enrich.CENSUS_SLIM), "run: python -m analysis.build_census_slim"
    mod = importlib.reload(enrich)
    try:
        mod.CENSUS_CSV = os.path.join(ROOT, "data", "raw", "__absent__.csv")   # simulate a clean clone
        row = mod.census_row(1000986)
        assert row and row["add_date"] == "28-JAN-02" and row["mcs150_date"] == "09-MAY-26"
        assert mod.CENSUS_SOURCE == "slim" and mod.census_is_complete() is False
    finally:
        importlib.reload(enrich)

def test_absent_row_is_unknown_not_a_dead_registration():
    """A >6-unit carrier is legitimately missing from the slim extract. Absence must not fire R08."""
    from rater import enrich, features, rules
    sub = ingest.normalise({"usdot": 1})
    car = {"found": True, "power_units": 3, "drivers": 3, "allowed_to_operate": True, "status_code": "A",
           "active_for_hire_authority": True, "in_census": None, "add_date": "28-JAN-02",
           "operation_classification": ["authorized for hire"], "basics": {}, "cargo": []}
    f = features.build(sub, car, [])
    assert f["in_census"] is True   # None = no signal, treated as no finding
    assert not any(x["id"] == "R08" for x in rules.evaluate(f)["rules_fired"])
