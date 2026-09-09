"""Enrichment: FMCSA QCMobile (carrier) + NHTSA vPIC (VIN) + local census snapshot. Cache-first; never raises.

QCMobile schema VERIFIED 2026-09-09 against live responses for DOTs 2231000, 3456789, 1000986 (raw JSON in
data/raw/qcmobile_samples/). Summary of what the live API actually returns:
  /carriers/{dot}                  {"content": {"carrier": {...}, "_links": {...}}, "retrievalDate": ...}
                                   Unknown DOT -> HTTP 200 with {"content": null}  (NOT a 404).
  /carriers/{dot}/basics           {"content": [{"basic": {"basicsPercentile": "Not Public"|number-as-string,
                                     "basicsType": {"basicsCode": "Unsafe Driving", "basicsShortDesc": ..., "basicsCodeMcmis": null},
                                     "measureValue": "10.32", "totalViolation": 8, "totalInspectionWithViolation": 8, ...}}]}
                                   Property-carrier percentiles have been "Not Public" since the FAST Act (Dec 2015); every
                                   DOT probed (incl. Swift/Werner/Schneider) returns "Not Public".
  /carriers/{dot}/authority        {"content": [{"carrierAuthority": {"commonAuthorityStatus": "A", "contractAuthorityStatus": "N",
                                     "authorizedForProperty": "Y", "authorizedForPassenger": "N", "authorizedForHouseholdGoods": "N",
                                     "docketNumber": 429079, "prefix": "MC", ...}}]}
  /carriers/{dot}/cargo-carried    {"content": []} for EVERY DOT probed, including 12k-unit fleets. Path below is unverified.
  /carriers/{dot}/operation-classification  {"content": [{"operationClassDesc": "Authorized For Hire", "id": {...}}]}
  /carriers/{dot}/docket-numbers   {"content": [{"prefix": "MC", "docketNumber": 429079, ...}]}
  Carrier object fields present: allowedToOperate, statusCode, totalPowerUnits, totalDrivers, driverInsp, vehicleInsp, hazmatInsp,
    driverOosRate / vehicleOosRate / hazmatOosRate (PERCENT 0-100, with *NationalAverage strings alongside), crashTotal, fatalCrash,
    injCrash, towawayCrash, safetyRating (letter: S/C/U), safetyRatingDate, oosDate, mcs150Outdated, isPassengerCarrier,
    carrierOperation{carrierOperationCode, carrierOperationDesc}, common/contract/brokerAuthorityStatus, bipd* insurance fields.
  Carrier object fields ABSENT: addDate, mcs150Date, mcs150Mileage, any hazmat flag, pcFlag.  These come from the local
    FMCSA census snapshot (data/raw/census.csv, indexed once into data/cache/census.sqlite).

Set FMCSA_WEBKEY in env or in a .env file at repo root (gitignored). Offline mode (RATER_OFFLINE=1) reads only
samples/fixtures + data/cache (the census sqlite is local, so it is used in offline mode too)."""
import csv, json, os, sqlite3, time
from .config import DATA_DIR, ROOT

CACHE = os.path.join(DATA_DIR, "cache")
FIXTURES = os.path.join(ROOT, "samples", "fixtures")
QC_BASE = "https://mobile.fmcsa.dot.gov/qc/services/carriers"
QC_SUB_ENDPOINTS = ("basics", "authority", "cargo-carried", "operation-classification", "docket-numbers")
VPIC_BATCH = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVINValuesBatch/"
CENSUS_CSV = os.path.join(DATA_DIR, "raw", "census.csv")
CENSUS_DB = os.path.join(CACHE, "census.sqlite")
OFFLINE = os.environ.get("RATER_OFFLINE", "0") == "1"
WEBKEY = os.environ.get("FMCSA_WEBKEY", "")

def _cache_path(kind, key):
    os.makedirs(os.path.join(CACHE, kind), exist_ok=True)
    return os.path.join(CACHE, kind, f"{key}.json")

def _read(kind, key):
    for base in (CACHE, FIXTURES):
        p = os.path.join(base, kind, f"{key}.json")
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    return None

def _write(kind, key, obj):
    with open(_cache_path(kind, key), "w") as f:
        json.dump({"_fetched_at": time.time(), **obj}, f)

def _get(url, params=None, timeout=15):
    import requests
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

# ---------------- FMCSA census snapshot (local) ----------------
CENSUS_COLS = ("dot_number", "legal_name", "carrier_operation", "hm_flag", "pc_flag", "phy_state", "mcs150_date",
               "mcs150_mileage", "mcs150_mileage_year", "add_date", "nbr_power_unit", "driver_total",
               "authorized_for_hire", "exempt_for_hire", "private_only")
_CENSUS_CON = None

def _census_con():
    """sqlite index over data/raw/census.csv (2.1M rows, unsorted); built once, rebuilt if the CSV changes."""
    global _CENSUS_CON
    if _CENSUS_CON is not None:
        return _CENSUS_CON or None
    if not os.path.exists(CENSUS_CSV):
        _CENSUS_CON = False
        return None
    os.makedirs(CACHE, exist_ok=True)
    stamp = f"{os.path.getsize(CENSUS_CSV)}:{int(os.path.getmtime(CENSUS_CSV))}"
    con = sqlite3.connect(CENSUS_DB, check_same_thread=False)
    con.execute("create table if not exists meta (key text primary key, value text)")
    cur = con.execute("select value from meta where key='stamp'").fetchone()
    if not cur or cur[0] != stamp:
        con.execute("drop table if exists census")
        con.execute(f"create table census ({', '.join(CENSUS_COLS)}, primary key (dot_number))")
        with open(CENSUS_CSV, newline="", encoding="utf-8", errors="replace") as f:
            rdr = csv.DictReader(f)
            buf = []
            for row in rdr:
                try: buf.append((int(row["dot_number"]),) + tuple(row.get(c) for c in CENSUS_COLS[1:]))
                except (ValueError, TypeError): continue
                if len(buf) >= 50000:
                    con.executemany(f"insert or replace into census values ({','.join('?' * len(CENSUS_COLS))})", buf); buf = []
            if buf:
                con.executemany(f"insert or replace into census values ({','.join('?' * len(CENSUS_COLS))})", buf)
        con.execute("insert or replace into meta values ('stamp', ?)", (stamp,))
        con.commit()
    _CENSUS_CON = con
    return con

def census_row(usdot) -> dict | None:
    """Registration fields for a DOT from the local census snapshot, or None if the file/row is absent."""
    try:
        con = _census_con()
        if con is None: return None
        r = con.execute(f"select {', '.join(CENSUS_COLS)} from census where dot_number=?", (int(usdot),)).fetchone()
        return dict(zip(CENSUS_COLS, r)) if r else None
    except Exception:
        return None

# ---------------- FMCSA carrier ----------------
def fetch_carrier(usdot: int) -> dict:
    """Returns dict with keys: found, raw, degraded, source, and parsed fields."""
    cached = _read("carrier", str(usdot))
    if cached:
        return {**_parse_carrier(cached), "source": "cache_or_fixture", "degraded": False}
    if OFFLINE or not WEBKEY:
        return {"found": None, "degraded": True, "source": "none", "raw": None}
    try:
        raw = {"carrier": _get(f"{QC_BASE}/{usdot}", {"webKey": WEBKEY})}
        # Verified 2026-09-09: unknown DOT -> HTTP 200 {"content": null}; sub-endpoints -> {"content": []}.
        # An actual HTTP 4xx/5xx is raised by _get and lands in the degraded branch below (an API failure must not
        # be mistaken for "carrier does not exist", which would trigger decline rule D01).
        if _g(raw, "carrier", "content") is None:
            _write("carrier", str(usdot), {"carrier": raw["carrier"], "_not_found": True})
            return {"found": False, "degraded": False, "source": "live_not_found", "raw": raw}
        for ep in QC_SUB_ENDPOINTS:
            try:
                raw[ep] = _get(f"{QC_BASE}/{usdot}/{ep}", {"webKey": WEBKEY})
            except Exception as e:  # sub-endpoints optional
                raw[ep] = {"_error": str(e)}
        raw["census"] = census_row(usdot)   # registration dates / mileage / HM+PC flags are not in QCMobile
        _write("carrier", str(usdot), raw)
        return {**_parse_carrier(raw), "source": "live", "degraded": False}
    except Exception as e:
        return {"found": None, "degraded": True, "source": f"error:{e}", "raw": None}

def _g(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
    return d if d is not None else default

# basicsType.basicsCode (live) / basicsShortDesc -> key used by config/rates.yaml relativities.basic_percentile
BASIC_KEYS = {
    "unsafe driving": "unsafe_driving",
    "hos compliance": "hos_compliance", "hours-of-service compliance": "hos_compliance",
    "driver fitness": "driver_fitness",
    "drugs/alcohol": "controlled_substances", "controlled substances/alcohol": "controlled_substances",
    "vehicle maint.": "vehicle_maintenance", "vehicle maintenance": "vehicle_maintenance",
    "hazmat": "hazmat", "hm compliance": "hazmat", "hazardous materials compliance": "hazmat",
    "crash indicator": "crash_indicator",
}

def _yn(v) -> bool:
    return str(v if v is not None else "").strip().lower() in ("y", "yes", "true", "t", "1")

def _num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def _parse_carrier(raw: dict) -> dict:
    c = _g(raw, "carrier", "content", "carrier") or _g(raw, "carrier", "content") or _g(raw, "carrier") or {}
    if not c or not isinstance(c, dict) or not (c.get("dotNumber") or c.get("legalName")):
        return {"found": False, "raw": raw}
    # --- BASICs: content[].basic.{basicsType.basicsCode, basicsPercentile, measureValue, totalViolation, ...}
    basics, basics_detail = {}, {}
    for b in (_g(raw, "basics", "content") or []):
        bb = b.get("basic", b) if isinstance(b, dict) else {}
        bt = bb.get("basicsType") or {}
        label = str(bt.get("basicsCode") or bt.get("basicsShortDesc") or bt.get("basicsCodeMcmis") or "").replace("&#8203;", "").strip().lower()
        key = BASIC_KEYS.get(label) or label.replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "")
        if not key: continue
        pct = _num(bb.get("basicsPercentile"))          # "Not Public" -> None (property carriers, post-FAST Act)
        if pct is not None: basics[key] = pct
        basics_detail[key] = {
            "percentile": pct, "percentile_public": pct is not None,
            "measure": _num(bb.get("measureValue")),
            "violations": bb.get("totalViolation"), "inspections_with_violation": bb.get("totalInspectionWithViolation"),
            "threshold": _num(bb.get("basicsViolationThreshold")),
            "exceeded_intervention_threshold_raw": bb.get("exceededFMCSAInterventionThreshold"),
            "serious_violation_12m": _yn(bb.get("seriousViolationFromInvestigationPast12MonthIndicator")),
            "run_date": bb.get("basicsRunDate"),
        }
    # --- cargo: live API returns [] for every DOT probed; path mirrors operation-classification + fixtures (unverified)
    cargo = [s for s in (str(_g(x, "cargoClassDesc") or _g(x, "cargoClassification", "cargoClassDesc") or "").lower()
                         for x in (_g(raw, "cargo-carried", "content") or [])) if s]
    # --- operation classification: content[].operationClassDesc  ("Authorized For Hire", "Private Property", ...)
    opclass = [s for s in (str(_g(x, "operationClassDesc") or _g(x, "operationClassification", "operationClassDesc") or "").lower()
                           for x in (_g(raw, "operation-classification", "content") or [])) if s]
    # --- authority: content[].carrierAuthority.{commonAuthorityStatus, contractAuthorityStatus, authorizedFor*, docketNumber, prefix}
    auth = [(_g(x, "carrierAuthority") or x) for x in (_g(raw, "authority", "content") or []) if isinstance(x, dict)]
    dockets = [f"{x.get('prefix') or ''}-{x.get('docketNumber')}".strip("-")
               for x in (_g(raw, "docket-numbers", "content") or []) if isinstance(x, dict) and x.get("docketNumber")]
    dockets = dockets or [f"{a.get('prefix') or ''}-{a.get('docketNumber')}".strip("-") for a in auth if a.get("docketNumber")]
    # --- census snapshot for fields QCMobile does not expose (addDate, mcs150Date, mcs150Mileage, hm/pc flags)
    cen = raw.get("census")
    if cen is None and c.get("dotNumber"):
        cen = census_row(c["dotNumber"])
    cen = cen or {}
    def first(*vals):
        for v in vals:
            if v not in (None, ""): return v
        return None
    passenger = (_yn(c.get("isPassengerCarrier")) or _yn(c.get("pcFlag")) or _yn(cen.get("pc_flag"))
                 or any(_yn(a.get("authorizedForPassenger")) for a in auth))
    hazmat = _yn(c.get("hazmatFlag")) or _yn(c.get("hmFlag")) or _yn(cen.get("hm_flag"))
    common, contract = str(c.get("commonAuthorityStatus") or ""), str(c.get("contractAuthorityStatus") or "")
    # None = unknown (synthetic fixture / no authority fields at all); features treat None as "no signal"
    active_auth = None
    if common or contract or auth:
        active_auth = (common.upper() == "A" or contract.upper() == "A"
                       or any(str(a.get("commonAuthorityStatus", "")).upper() == "A"
                              or str(a.get("contractAuthorityStatus", "")).upper() == "A" for a in auth))
    # None = census not consulted (synthetic fixture, or no census file on this machine)
    in_census = None if (raw.get("_synthetic") or not os.path.exists(CENSUS_CSV)) else bool(cen)
    return {
        "found": True, "raw": raw,
        "legal_name": c.get("legalName"), "state": c.get("phyState") or cen.get("phy_state"),
        "allowed_to_operate": (str(c.get("allowedToOperate", "Y")).upper() == "Y"),
        "status_code": c.get("statusCode"),
        "power_units": c.get("totalPowerUnits"), "drivers": c.get("totalDrivers"),
        "driver_oos_rate": _pct(c.get("driverOosRate")), "vehicle_oos_rate": _pct(c.get("vehicleOosRate")),
        "hazmat_oos_rate": _pct(c.get("hazmatOosRate")),
        "driver_oos_rate_national_avg": _pct(c.get("driverOosRateNationalAverage")),
        "vehicle_oos_rate_national_avg": _pct(c.get("vehicleOosRateNationalAverage")),
        "driver_inspections": c.get("driverInsp"), "vehicle_inspections": c.get("vehicleInsp"),
        "hazmat_inspections": c.get("hazmatInsp"),
        "driver_oos_inspections": c.get("driverOosInsp"), "vehicle_oos_inspections": c.get("vehicleOosInsp"),
        "crashes_total": c.get("crashTotal"), "fatal_crashes": c.get("fatalCrash"),
        "injury_crashes": c.get("injCrash"), "towaway_crashes": c.get("towawayCrash"),
        "safety_rating": _safety_rating(c.get("safetyRating")), "safety_rating_date": c.get("safetyRatingDate"),
        "safety_review_date": c.get("safetyReviewDate") or c.get("reviewDate"),
        "oos_date": c.get("oosDate"), "mcs150_outdated": _yn(c.get("mcs150Outdated")),
        "mcs150_date": first(c.get("mcs150Date"), cen.get("mcs150_date")),
        "mcs150_mileage": first(c.get("mcs150Mileage"), cen.get("mcs150_mileage")),
        "mcs150_mileage_year": cen.get("mcs150_mileage_year"),
        # addDate = date the record was added to MCMIS (registration), the best available proxy for authority age;
        # QCMobile's /authority carries no grant date.
        "add_date": first(c.get("addDate"), cen.get("add_date")),
        "carrier_operation": _g(c, "carrierOperation", "carrierOperationDesc"),
        "carrier_operation_code": _g(c, "carrierOperation", "carrierOperationCode") or cen.get("carrier_operation"),
        "hazmat_flag": hazmat, "passenger_flag": passenger,
        "common_authority_status": common or None, "contract_authority_status": contract or None,
        "broker_authority_status": c.get("brokerAuthorityStatus"),
        "active_for_hire_authority": active_auth, "in_census": in_census,
        "bipd_insurance_on_file_k": _num(c.get("bipdInsuranceOnFile")), "bipd_required_k": _num(c.get("bipdRequiredAmount")),
        "docket_numbers": dockets,
        "census_power_units": _num(cen.get("nbr_power_unit")), "census_drivers": _num(cen.get("driver_total")),
        "census_authorized_for_hire": _yn(cen.get("authorized_for_hire")) if cen else None,
        "basics": basics, "basics_detail": basics_detail, "cargo": cargo,
        "operation_classification": opclass, "authority": auth,
    }

def _safety_rating(v):
    """QCMobile returns a letter (S/C/U/N); fixtures and rules use the word."""
    s = str(v or "").strip().upper()
    return {"S": "SATISFACTORY", "C": "CONDITIONAL", "U": "UNSATISFACTORY", "N": None, "": None}.get(s, s)

def _pct(v):
    """QCMobile OOS rates are percentages (0-100; national average '5.51' alongside). Return a fraction."""
    v = _num(v)
    return None if v is None else v / 100.0

# ---------------- NHTSA vPIC ----------------
# vPIC batch schema VERIFIED 2026-09-09 (raw JSON in data/raw/vpic_sample.json: 2 Class 8 tractors, 1 trailer, 1 pickup,
# 1 malformed string). Field values seen live:
#   VehicleType  UPPER: "TRUCK", "TRAILER" (also "PASSENGER CAR", "MULTIPURPOSE PASSENGER VEHICLE (MPV)", "MOTORCYCLE", "BUS", ...)
#   BodyClass    Title: "Truck-Tractor", "Trailer", "Pickup"
#   GVWR         "Class 8: 33,001 lb and above (14,969 kg and above)", "Class 2F: 7,001 - 8,000 lb (...)"; EMPTY for trailers
#   ErrorCode    comma-separated, "0" clean. A GARBAGE string ("12345678901234567") still returns Make="SHERMAN + REILLY",
#                VehicleType="TRAILER" with ErrorCode "1,11,14,400" -- so Make alone must not mean "decoded".
# Error codes that mean the decode is not trustworthy (per vPIC error-code list): 5 errors in several positions,
# 6 incomplete VIN, 7 manufacturer not registered with NHTSA, 8 no detailed data, 400 invalid characters.
# 1 (check digit), 11 (model-year char), 14 (some positions unknown) are warnings; the WMI/VDS decode is still usable.
VPIC_FATAL_CODES = {"5", "6", "7", "8", "400"}

def decode_vins(vins: list) -> list:
    """Returns list of dicts per VIN: vin, model_year, make, model, gvwr, body_class, vehicle_type, error_code, decoded(bool)."""
    out, todo = {}, []
    norm = {v: str(v or "").strip().upper() for v in vins}
    for v in set(norm.values()):
        c = _read("vin", v)
        if c: out[v] = c
        else: todo.append(v)
    if todo and not OFFLINE:
        try:
            import requests
            for i in range(0, len(todo), 50):
                batch = todo[i:i+50]
                r = requests.post(VPIC_BATCH, data={"format": "json", "data": ";".join(batch)}, timeout=20)
                r.raise_for_status()
                for res in r.json().get("Results", []):
                    v = str(res.get("VIN") or "").strip().upper()
                    parsed = _parse_vin(v, res)
                    _write("vin", v, parsed); out[v] = parsed
        except Exception as e:
            pass  # degrade below
    return [out.get(norm[v], {"vin": v, "decoded": False}) for v in vins]

def _parse_vin(v, res):
    gvwr = str(res.get("GVWR") or "")
    codes = {c.strip() for c in str(res.get("ErrorCode") or "").split(",") if c.strip()}
    decoded = bool(res.get("Make")) and not (codes & VPIC_FATAL_CODES)
    return {"vin": v, "decoded": decoded, "make": res.get("Make"), "model": res.get("Model"),
            "model_year": _int(res.get("ModelYear")), "gvwr": gvwr, "body_class": res.get("BodyClass"),
            "vehicle_type": res.get("VehicleType"), "error_code": res.get("ErrorCode")}

def _int(x):
    try: return int(x)
    except (TypeError, ValueError): return None
