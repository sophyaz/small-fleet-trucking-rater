"""Turn (normalised submission, carrier enrichment, VIN decodes) into a flat feature dict used by rules and pricing."""
import datetime as dt, re
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
    # D12 needs POSITIVE evidence of private / intrastate operation. Registrations under ~60 days old come back from
    # QCMobile with an empty operation-classification list and null authority fields (seen on 6 of 45 real carriers,
    # all June-July 2026 add dates); an empty list is "unknown", not "not for hire". Those fall through to R01 / R07.
    opclass = " ".join(car.get("operation_classification") or []).lower()
    carrier_op = str(car.get("carrier_operation") or "").lower()
    f["for_hire_interstate"] = True
    f["operation_classification_known"] = True
    if found:
        if opclass.strip():
            if "auth. for hire" not in opclass and "authorized for hire" not in opclass:
                f["for_hire_interstate"] = False
        elif car.get("census_authorized_for_hire") is False:   # QCMobile silent, census says not for-hire
            f["for_hire_interstate"] = False
        else:   # unknown -> refer (R09), never a clean price: DOT 8877502 had 2 inspections so R01 did not catch it
            f["operation_classification_known"] = False; f["flags"].append("operation_classification_missing")
        if "intrastate" in carrier_op and "interstate" not in carrier_op:
            f["for_hire_interstate"] = False
    # MC authority status letters (A active / I inactive / N none) and the BI/PD filing on record. None = unknown
    # (synthetic fixture); rules treat a missing field as not fired.
    f["common_authority_status"] = car.get("common_authority_status") if found else None
    f["contract_authority_status"] = car.get("contract_authority_status") if found else None
    f["bipd_insurance_on_file_k"] = car.get("bipd_insurance_on_file_k") if found else None
    f["bipd_required_k"] = car.get("bipd_required_k") if found else None
    # commodity appetite from submission + census cargo flags
    cargo = " ".join(car.get("cargo") or [])
    f["out_of_appetite_commodity"] = sub["out_of_appetite_commodity"] or bool(car.get("hazmat_flag")) or bool(car.get("passenger_flag")) \
        or any(k in cargo for k in ("passengers", "household goods", "liquids/gases", "explosives", "motor vehicles"))
    f["commodity"] = sub["commodity"]
    f["radius"] = sub["radius"]
    f["state"] = sub.get("garaging_state") or car.get("state") or None
    f["limit"] = sub["limit"]
    # limits.offered is enforced (D32 / R12 / R13). Without this the rater bound any limit through the mixture's
    # limited mean -- a $5m CSL came out 9.3% above $1m, against market trucking ILFs of 1.3-1.5 at $2m alone.
    lim_cfg = cfg.get("limits") or {}
    offered = lim_cfg.get("offered") or []
    base = lim_cfg.get("base") or cfg["meta"]["base_limit_csl"]
    f["limit_in_offered_set"] = (f["limit"] in offered) if offered else True
    # Three different problems, three different answers. Below the federal minimum we cannot legally write the
    # risk at all, and above the top offered limit they are asking for a layer we do not rate: both decline (D32).
    # A limit that is merely not one of the three we quote -- $900k, or $1,000,001, which is a typo, not a request
    # -- is a data-entry problem, and hard-declining an otherwise good submission over a stray digit is the wrong
    # answer when the brief grades handling of bad input. That refers (R13) and prices at the submitted limit.
    f["limit_outside_writable_range"] = bool(offered) and not (min(offered) <= f["limit"] <= max(offered))
    f["limit_off_grid"] = (not f["limit_in_offered_set"]) and not f["limit_outside_writable_range"]
    # R12 is about the $2m excess layer specifically, not about a limit that rounds a dollar above base
    f["limit_excess_layer"] = f["limit_in_offered_set"] and f["limit"] > base
    if not f["limit_in_offered_set"]:
        f["flags"].append(f"limit_not_offered:{f['limit']}")
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
    # MCS-150 mileage of 1, 2, 30 ... per year is a placeholder, not a low-mileage risk. Below the plausibility floor
    # treat it as unknown (factor 1.00) rather than granting the <=30k discount. Census 0 already maps to None above.
    floor = cfg["relativities"].get("mileage_min_plausible_per_unit", 0)
    if f["mileage_per_unit"] is not None and f["mileage_per_unit"] < floor:
        f["mileage_per_unit"] = None; f["flags"].append("mcs150_mileage_implausible")
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

_LIGHT_GVWR = re.compile(r"\bCLASS\s*[12][A-H]?\b")   # vPIC: "Class 1A".."Class 1D", "Class 2E".."Class 2H" (<=10,000 lb)

def _is_non_commercial(v):
    """True for VINs that are not a rated power unit: trailers, cars/SUVs/motorcycles, and light-duty (GVWR class 1-2)
    pickups/vans. Class 3+ pickups (F-350 etc.) stay commercial: hotshot fleets run them. Verified against live vPIC
    strings 2026-09-09 (see data/raw/vpic_sample.json): VehicleType is UPPER, BodyClass Title-case, GVWR empty for trailers."""
    vt = str(v.get("vehicle_type") or "").upper()
    bc = str(v.get("body_class") or "").upper()
    gv = str(v.get("gvwr") or "").upper()
    if "TRAILER" in vt or "TRAILER" in bc: return True
    if any(k in vt for k in ("PASSENGER CAR", "MULTIPURPOSE PASSENGER VEHICLE", "MOTORCYCLE", "LOW SPEED VEHICLE", "OFF ROAD")):
        return True
    if _LIGHT_GVWR.search(gv): return True   # pickups / light duty
    return False
