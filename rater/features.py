"""Turn (normalised submission, carrier enrichment, VIN decodes) into a flat feature dict used by rules and pricing."""
import datetime as dt
from .config import rates

def _years_since(s, today=None):
    if not s: return None
    today = today or dt.date.today()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%d-%b-%y"):
        try:
            d = dt.datetime.strptime(str(s)[:19], fmt).date()
            return max(0.0, (today - d).days / 365.25)
        except ValueError:
            continue
    return None

def _first(*vals):
    for v in vals:
        if v is not None: return v
    return None

def build(sub: dict, car: dict, vins: list, cfg=None) -> dict:
    cfg = cfg or rates()
    f = {"submission_id": sub["submission_id"], "usdot": sub["usdot"], "flags": list(sub["ingest_flags"])}
    found = car.get("found")
    f["carrier_found"] = False if found is False else True   # degraded (None) is not "not found"
    f["enrichment_degraded"] = bool(car.get("degraded"))
    if f["enrichment_degraded"]:
        f["flags"].append("enrichment_degraded_segment_defaults")
    # exposure
    census_units = car.get("power_units") if found else None
    f["census_units"] = census_units
    f["power_units"] = _first(sub.get("declared_units"), census_units, 1)
    if sub.get("declared_units") is None and census_units is None:
        f["flags"].append("units_defaulted_to_1")
    f["drivers"] = _first(sub.get("driver_count"), car.get("drivers") if found else None, f["power_units"])
    f["driver_unit_ratio"] = (f["drivers"] / f["power_units"]) if f["power_units"] else 1.0
    # census 0 is a real value (dormant / stale MCS-150), so test `is not None`, not truthiness
    f["unit_count_mismatch"] = bool(sub.get("declared_units") is not None and census_units is not None and
                                    (abs(sub["declared_units"] - census_units) > 3 or
                                     max(sub["declared_units"], census_units) > 2 * min(sub["declared_units"], census_units)))
    if found and census_units == 0:
        f["flags"].append("census_units_zero")
    # authority / status
    f["allowed_to_operate"] = car.get("allowed_to_operate", True) if found else True
    # allowedToOperate only reflects OOS orders / revocation; an inactive USDOT registration still says "Y"
    f["usdot_status_active"] = (str(car.get("status_code") or "A").upper() == "A") if found else True
    # enrich returns None when the signal is unavailable (synthetic fixture, no census file); None = no signal
    f["active_for_hire_authority"] = _first(car.get("active_for_hire_authority"), True) if found else True
    # census snapshot holds active carriers only; absence = registered after the snapshot or inactive
    f["in_census"] = _first(car.get("in_census"), True) if found else True
    f["oos_order"] = bool(car.get("oos_date")) if found else False
    f["safety_rating"] = car.get("safety_rating") if found else None
    f["authority_age_years"] = _years_since(car.get("add_date")) if found else None
    if f["authority_age_years"] is None:
        f["authority_age_years"] = 0.5; f["flags"].append("authority_age_unknown_assumed_0.5y")
    f["mcs150_age_years"] = _years_since(car.get("mcs150_date")) if found else None
    if f["mcs150_age_years"] is None: f["mcs150_age_years"] = 0.0
    op = " ".join(car.get("operation_classification") or []) + " " + str(car.get("carrier_operation") or "")
    f["for_hire_interstate"] = True
    if found and op.strip():
        if "auth. for hire" not in op and "authorized for hire" not in op:
            f["for_hire_interstate"] = False
        if "intrastate" in op and "interstate" not in op:
            f["for_hire_interstate"] = False
    # commodity appetite from submission + census cargo flags
    cargo = " ".join(car.get("cargo") or [])
    f["out_of_appetite_commodity"] = sub["out_of_appetite_commodity"] or bool(car.get("hazmat_flag")) or bool(car.get("passenger_flag")) \
        or any(k in cargo for k in ("passengers", "household goods", "liquids/gases", "explosives", "motor vehicles"))
    f["commodity"] = sub["commodity"]
    f["radius"] = sub["radius"]
    f["state"] = sub.get("garaging_state") or car.get("state") or None
    f["limit"] = sub["limit"]
    # crashes
    f["crashes_24m"] = int(_first(car.get("crashes_total"), 0)) if found else 0
    f["fatal_crashes"] = int(_first(car.get("fatal_crashes"), 0)) if found else 0
    f["injury_crashes"] = int(_first(car.get("injury_crashes"), 0)) if found else 0
    # inspections / OOS
    f["driver_inspections"] = int(_first(car.get("driver_inspections"), 0)) if found else 0
    f["vehicle_inspections"] = int(_first(car.get("vehicle_inspections"), 0)) if found else 0
    f["total_inspections"] = f["driver_inspections"] + f["vehicle_inspections"]
    seg = cfg["segment_averages"]
    dr, vr = car.get("driver_oos_rate"), car.get("vehicle_oos_rate")
    f["driver_oos_ratio"] = (dr / seg["driver_oos_rate"]) if (found and dr is not None and seg["driver_oos_rate"]) else 1.0
    f["vehicle_oos_ratio"] = (vr / seg["vehicle_oos_rate"]) if (found and vr is not None and seg["vehicle_oos_rate"]) else 1.0
    for k, v in (car.get("basics") or {}).items():
        key = "basic_" + k.replace(" ", "_").replace("-", "_")
        f[key] = v
    # mileage
    mil = car.get("mcs150_mileage") if found else None
    try:
        mil = float(mil) if mil is not None else None
    except ValueError:
        mil = None
    f["mileage_per_unit"] = (mil / max(1, census_units or f["power_units"])) if mil else None
    # drivers detail
    f["driver_experience_min"] = sub.get("driver_experience_min")
    # vehicles
    decoded = [v for v in vins if v.get("decoded")]
    years = [v["model_year"] for v in decoded if v.get("model_year")]
    thisyear = dt.date.today().year
    f["vehicle_age_avg"] = (sum(thisyear - y for y in years) / len(years)) if years else None
    noncomm = [v for v in decoded if _is_non_commercial(v)]
    f["non_commercial_vin_share"] = (len(noncomm) / len(decoded)) if decoded else 0.0
    f["vins_decoded"] = len(decoded); f["vins_submitted"] = len(vins)
    if vins and not decoded:
        f["flags"].append("no_vins_decoded")
    f["insurance_cancellation_24m"] = sub.get("insurance_cancellation_24m", False)
    f["chameleon_flag"] = False   # VERIFY/TODO: analysis/chameleon.py builds address->revoked-DOT index from census file
    return f

def _is_non_commercial(v):
    vt = str(v.get("vehicle_type") or "").upper()
    bc = str(v.get("body_class") or "").upper()
    gv = str(v.get("gvwr") or "").upper()
    if "TRAILER" in vt or "TRAILER" in bc: return True
    if "PASSENGER CAR" in vt or "MOTORCYCLE" in vt: return True
    if "CLASS 1" in gv or "CLASS 2" in gv: return True   # pickups / light duty
    return False
