"""Validate and normalise a submission. Never raises on bad user data: coerces, defaults, and flags."""
import re
from .config import schema

RADII = ["local_0_50", "intermediate_51_200", "regional_201_500", "long_haul_500_plus"]
RADIUS_ALIASES = {"local": "local_0_50", "intermediate": "intermediate_51_200", "regional": "regional_201_500",
                  "long": "long_haul_500_plus", "long_haul": "long_haul_500_plus", "longhaul": "long_haul_500_plus"}
COMMODITY_ALIASES = {"dryvan": "dry_van", "van": "dry_van", "refrigerated": "reefer", "reefer": "reefer",
                     "flat": "flatbed", "flatbed": "flatbed", "general": "general_freight", "lumber": "logs_lumber",
                     "logs": "logs_lumber", "machinery": "machinery_heavy", "grain": "grain_feed"}
OUT_OF_APPETITE = {"hazmat", "tanker", "passenger", "household_goods", "hhg", "auto_hauler", "autos", "livestock", "oilfield", "garbage"}
VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

def normalise(sub: dict) -> dict:
    flags = []
    out = {"submission_id": str(sub.get("submission_id") or f"sub-{sub.get('usdot','?')}")}
    # USDOT
    raw = str(sub.get("usdot", "")).strip()
    digits = re.sub(r"\D", "", raw)
    out["usdot"] = int(digits) if digits else None
    if out["usdot"] is None:
        flags.append("usdot_missing_or_invalid")
    # drivers
    drivers = sub.get("drivers")
    if drivers is not None and not isinstance(drivers, list):
        flags.append("drivers_not_a_list_ignored"); drivers = None
    if isinstance(drivers, list):
        out["drivers_list"] = [d for d in drivers if isinstance(d, dict)]
        out["driver_count"] = len(out["drivers_list"])
    else:
        out["drivers_list"] = []
        dc = sub.get("driver_count")
        out["driver_count"] = int(dc) if isinstance(dc, (int, float)) and dc >= 0 else None
        if out["driver_count"] is None:
            flags.append("driver_count_missing_use_census")
    exp = [d.get("cdl_years") for d in out["drivers_list"] if isinstance(d.get("cdl_years"), (int, float))]
    out["driver_experience_min"] = min(exp) if exp else None
    ages = [d.get("age") for d in out["drivers_list"] if isinstance(d.get("age"), (int, float))]
    out["driver_age_min"] = min(ages) if ages else None
    # units / VINs
    units = sub.get("units")
    if not isinstance(units, list):
        if units: flags.append("units_not_a_list_ignored")
        units = []
    vins = []
    for u in units:
        v = (u.get("vin") if isinstance(u, dict) else u) or ""
        v = str(v).strip().upper()
        if VIN_RE.match(v):
            vins.append(v)
        else:
            flags.append(f"invalid_vin:{v[:17]}")
    out["vins"] = vins
    out["declared_units"] = len(units) if units else None
    if not units:
        flags.append("units_missing_use_census")
    # radius
    r = str(sub.get("radius") or "").strip().lower()
    out["radius"] = r if r in RADII else RADIUS_ALIASES.get(r)
    if out["radius"] is None:
        out["radius"] = "intermediate_51_200"; flags.append("radius_missing_default_intermediate")
    # commodity
    c = str(sub.get("commodity") or "").strip().lower().replace(" ", "_")
    out["commodity_raw"] = c
    out["out_of_appetite_commodity"] = any(k in c for k in OUT_OF_APPETITE)
    out["commodity"] = COMMODITY_ALIASES.get(c, c) if c else "unknown"
    if not c:
        flags.append("commodity_missing_default_unknown")
    # state
    st = str(sub.get("garaging_state") or "").strip().upper()
    out["garaging_state"] = st if len(st) == 2 else None
    if out["garaging_state"] is None:
        flags.append("garaging_state_missing_use_census")
    # limit
    lim = sub.get("limit")
    out["limit"] = int(lim) if isinstance(lim, (int, float)) and lim > 0 else 1000000
    ih = sub.get("insurance_history") or {}
    out["insurance_cancellation_24m"] = bool(ih.get("cancellation_24m", False))
    out["ingest_flags"] = flags
    return out
