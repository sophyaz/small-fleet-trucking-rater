"""Enrichment: FMCSA QCMobile (carrier) + NHTSA vPIC (VIN). Cache-first; never raises.
VERIFY: field names below are from the QCMobile response schema as I recall it — confirm against a live
response (docs: https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcApi) and fix in _parse_carrier().
Set FMCSA_WEBKEY in env or in a .env file at repo root (gitignored). Offline mode (RATER_OFFLINE=1) reads only samples/fixtures + data/cache."""
import json, os, time, hashlib
from .config import DATA_DIR, ROOT

CACHE = os.path.join(DATA_DIR, "cache")
FIXTURES = os.path.join(ROOT, "samples", "fixtures")
QC_BASE = "https://mobile.fmcsa.dot.gov/qc/services/carriers"
VPIC_BATCH = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVINValuesBatch/"
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

# ---------------- FMCSA carrier ----------------
def fetch_carrier(usdot: int) -> dict:
    """Returns dict with keys: found, raw, degraded, source, and parsed fields."""
    cached = _read("carrier", str(usdot))
    if cached:
        return {**_parse_carrier(cached), "source": "cache_or_fixture", "degraded": False}
    if OFFLINE or not WEBKEY:
        return {"found": None, "degraded": True, "source": "none", "raw": None}
    try:
        raw = {}
        try:
            raw["carrier"] = _get(f"{QC_BASE}/{usdot}", {"webKey": WEBKEY})
        except Exception as e:
            if "404" in str(e):   # VERIFY: QCMobile returns 404 (or empty content) for unknown DOT
                _write("carrier", str(usdot), {"carrier": {"content": None}, "_not_found": True})
                return {"found": False, "degraded": False, "source": "live_not_found", "raw": None}
            raise
        for ep in ("basics", "authority", "cargo-carried", "operation-classification"):
            try:
                raw[ep] = _get(f"{QC_BASE}/{usdot}/{ep}", {"webKey": WEBKEY})
            except Exception as e:  # sub-endpoints optional
                raw[ep] = {"_error": str(e)}
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

def _parse_carrier(raw: dict) -> dict:
    c = _g(raw, "carrier", "content", "carrier") or _g(raw, "carrier", "content") or _g(raw, "carrier") or {}
    if not c or not isinstance(c, dict) or not (c.get("dotNumber") or c.get("legalName")):
        return {"found": False, "raw": raw}
    basics = {}
    for b in (_g(raw, "basics", "content") or []):
        bb = b.get("basic", b) if isinstance(b, dict) else {}
        name = str(_g(bb, "basicsType", "basicsCodeMcmis") or _g(bb, "basicsType", "basicsShortDesc") or "").lower()
        pct = bb.get("basicsPercentile")
        if name and pct not in (None, ""):
            try: basics[name] = float(pct)
            except ValueError: pass
    cargo = [str(_g(x, "cargoClassDesc") or _g(x, "cargoClassification", "cargoClassDesc") or "").lower()
             for x in (_g(raw, "cargo-carried", "content") or [])]
    opclass = [str(_g(x, "operationClassDesc") or _g(x, "operationClassification", "operationClassDesc") or "").lower()
               for x in (_g(raw, "operation-classification", "content") or [])]
    auth = _g(raw, "authority", "content") or []
    return {
        "found": True, "raw": raw,
        "legal_name": c.get("legalName"), "state": c.get("phyState"),
        "allowed_to_operate": (str(c.get("allowedToOperate", "Y")).upper() == "Y"),
        "status_code": c.get("statusCode"),
        "power_units": c.get("totalPowerUnits"), "drivers": c.get("totalDrivers"),
        "driver_oos_rate": _pct(c.get("driverOosRate")), "vehicle_oos_rate": _pct(c.get("vehicleOosRate")),
        "driver_inspections": c.get("driverInsp"), "vehicle_inspections": c.get("vehicleInsp"),
        "crashes_total": c.get("crashTotal"), "fatal_crashes": c.get("fatalCrash"),
        "injury_crashes": c.get("injCrash"), "towaway_crashes": c.get("towawayCrash"),
        "safety_rating": (str(c.get("safetyRating") or "").upper() or None),
        "oos_date": c.get("oosDate"), "mcs150_outdated": (str(c.get("mcs150Outdated", "N")).upper() == "Y"),
        "mcs150_date": c.get("mcs150Date"), "mcs150_mileage": c.get("mcs150Mileage"),
        "add_date": c.get("addDate"),  # VERIFY: authority grant date lives in /authority or L&I, addDate is registration
        "carrier_operation": _g(c, "carrierOperation", "carrierOperationDesc"),
        "hazmat_flag": (str(c.get("hazmatFlag") or c.get("hmFlag") or "N").upper() == "Y"),
        "passenger_flag": (str(c.get("pcFlag") or "N").upper() == "Y"),
        "basics": basics, "cargo": cargo, "operation_classification": opclass, "authority": auth,
    }

def _pct(v):
    try:
        v = float(v)
        return v / 100.0 if v > 1.0 else v
    except (TypeError, ValueError):
        return None

# ---------------- NHTSA vPIC ----------------
def decode_vins(vins: list) -> list:
    """Returns list of dicts per VIN: vin, model_year, make, model, gvwr_class, body_class, vehicle_type, decoded(bool)."""
    out, todo = {}, []
    for v in vins:
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
                    v = res.get("VIN", "").upper()
                    parsed = _parse_vin(v, res)
                    _write("vin", v, parsed); out[v] = parsed
        except Exception as e:
            pass  # degrade below
    return [out.get(v, {"vin": v, "decoded": False}) for v in vins]

def _parse_vin(v, res):
    gvwr = str(res.get("GVWR") or "")
    return {"vin": v, "decoded": bool(res.get("Make")), "make": res.get("Make"), "model": res.get("Model"),
            "model_year": _int(res.get("ModelYear")), "gvwr": gvwr, "body_class": res.get("BodyClass"),
            "vehicle_type": res.get("VehicleType"), "error_code": res.get("ErrorCode")}

def _int(x):
    try: return int(x)
    except (TypeError, ValueError): return None
