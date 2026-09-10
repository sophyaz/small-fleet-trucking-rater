"""Validate and normalise a submission. Never raises on bad user data: coerces, defaults, and flags.

Accepted input shapes (config/schema.json documents the canonical form). Keys are matched case-insensitively and
through the alias tables below, so a reviewer's file that says "dot_number", "vins", "state" or "radius": 300 is
read the same way as the canonical "usdot", "units", "garaging_state", "radius": "regional_201_500". Every alias
or coercion that fires is recorded in ingest_flags so the breakdown shows what was assumed."""
import re

RADII = ["local_0_50", "intermediate_51_200", "regional_201_500", "long_haul_500_plus"]
RADIUS_ALIASES = {"local": "local_0_50", "intermediate": "intermediate_51_200", "regional": "regional_201_500",
                  "long": "long_haul_500_plus", "long_haul": "long_haul_500_plus", "longhaul": "long_haul_500_plus",
                  "0-50": "local_0_50", "51-200": "intermediate_51_200", "201-500": "regional_201_500", "500+": "long_haul_500_plus"}
COMMODITY_ALIASES = {"dryvan": "dry_van", "van": "dry_van", "refrigerated": "reefer", "reefer": "reefer",
                     "flat": "flatbed", "flatbed": "flatbed", "general": "general_freight", "lumber": "logs_lumber",
                     "logs": "logs_lumber", "machinery": "machinery_heavy", "grain": "grain_feed"}
OUT_OF_APPETITE = {"hazmat", "tanker", "passenger", "household_goods", "hhg", "auto_hauler", "autos", "livestock", "oilfield", "garbage"}
VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

# Canonical key -> accepted spellings (compared lower-case, with spaces/hyphens collapsed to underscores).
KEY_ALIASES = {
    "submission_id": ("submission_id", "id", "name", "carrier_name", "legal_name"),
    "usdot": ("usdot", "dot", "dot_number", "usdot_number", "usdotnumber", "dotnumber", "us_dot", "us_dot_number", "dot_no"),
    "units": ("units", "vins", "vehicles", "trucks", "tractors", "vin", "vin_list"),
    "unit_count": ("power_units", "unit_count", "units_count", "num_units", "number_of_units", "n_units", "total_power_units",
                   "nbr_power_unit", "power_unit_count", "num_power_units", "number_of_power_units", "truck_count"),
    "drivers": ("drivers", "driver_list", "driver"),
    "driver_count": ("driver_count", "drivers_count", "num_drivers", "number_of_drivers", "n_drivers", "total_drivers"),
    "radius": ("radius", "operating_radius", "radius_miles", "radius_of_operation", "operating_radius_miles"),
    "commodity": ("commodity", "cargo", "commodity_type", "commodities", "hauled_commodity", "freight", "cargo_type"),
    "garaging_state": ("garaging_state", "state", "domicile_state", "phy_state", "garage_state", "home_state"),
    "limit": ("limit", "limit_csl", "csl", "liability_limit", "policy_limit"),
    "insurance_history": ("insurance_history", "insurance"),
}

def _norm_key(k) -> str:
    return re.sub(r"[\s\-]+", "_", str(k).strip().lower())

def _pick(sub: dict, canonical: str, flags: list):
    """Value for `canonical` from the submission, trying each alias case-insensitively. Flags a non-canonical hit.
    An alias whose value is null / empty string is skipped so a later alias can still supply the value."""
    if not isinstance(sub, dict):
        return None
    lookup = {_norm_key(k): (k, v) for k, v in sub.items()}
    for alias in KEY_ALIASES[canonical]:
        if alias in lookup:
            orig, v = lookup[alias]
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            if _norm_key(orig) != canonical:
                flags.append(f"alias:{orig}->{canonical}")
            return v
    return None

def _to_number(v):
    """int/float from a number or a numeric string ('3', '1,000,000', '1m', '750k', '$1M'). None if not numeric."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v or "").strip().lower().replace(",", "").replace("$", "").replace("_", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([km]?)", s)
    if not m:
        return None
    x = float(m.group(1)) * {"": 1, "k": 1_000, "m": 1_000_000}[m.group(2)]
    return int(x) if x == int(x) else x

def _radius_from_miles(miles: float) -> str:
    if miles <= 50: return "local_0_50"
    if miles <= 200: return "intermediate_51_200"
    if miles <= 500: return "regional_201_500"
    return "long_haul_500_plus"

def normalise(sub: dict) -> dict:
    flags = []
    sub = sub if isinstance(sub, dict) else {}
    usdot_raw = _pick(sub, "usdot", flags)
    sid = _pick(sub, "submission_id", flags)
    out = {"submission_id": str(sid or f"sub-{usdot_raw if usdot_raw is not None else '?'}")}
    # USDOT
    raw = str(usdot_raw if usdot_raw is not None else "").strip()
    digits = re.sub(r"\D", "", raw)
    out["usdot"] = int(digits) if digits else None
    if out["usdot"] is None:
        flags.append("usdot_missing_or_invalid")
    # drivers: a list of dicts (canonical), a list of names, a count, or a numeric string
    drivers = _pick(sub, "drivers", flags)
    driver_count_field = _pick(sub, "driver_count", flags)
    if drivers is not None and not isinstance(drivers, list):
        n = _to_number(drivers)
        if n is not None and n >= 0:
            flags.append("drivers_given_as_count"); driver_count_field = n if driver_count_field is None else driver_count_field
        else:
            flags.append("drivers_not_a_list_ignored")
        drivers = None
    if isinstance(drivers, list):
        out["drivers_list"] = [d for d in drivers if isinstance(d, dict)]
        if len(out["drivers_list"]) < len(drivers):
            flags.append("drivers_non_dict_entries_counted_only")
        out["driver_count"] = len(drivers)
    else:
        out["drivers_list"] = []
        dc = _to_number(driver_count_field)
        if driver_count_field is not None and dc is None:
            flags.append("driver_count_not_numeric_ignored")
        out["driver_count"] = int(dc) if dc is not None and dc >= 0 else None
        if out["driver_count"] is None:
            flags.append("driver_count_missing_use_census")
    exp = [d.get("cdl_years") for d in out["drivers_list"] if isinstance(d.get("cdl_years"), (int, float))]
    out["driver_experience_min"] = min(exp) if exp else None
    ages = [d.get("age") for d in out["drivers_list"] if isinstance(d.get("age"), (int, float))]
    out["driver_age_min"] = min(ages) if ages else None
    # units / VINs: list of {"vin": ...}, list of VIN strings, a single VIN string, or a bare unit count
    # (canonical "units" list; "power_units" & co. may carry either a count or a list)
    units = _pick(sub, "units", flags)
    count_field = _pick(sub, "unit_count", flags)
    if units is None and isinstance(count_field, list):
        units, count_field = count_field, None
    unit_count_only = None
    if isinstance(units, str) and VIN_RE.match(units.strip().upper()):
        units = [units]; flags.append("single_vin_string_wrapped")
    if not isinstance(units, list):
        n = _to_number(units)
        if n is not None and n >= 0:
            unit_count_only = int(n); flags.append("units_given_as_count_no_vins")
        elif units:
            flags.append("units_not_a_list_ignored")
        units = []
    if count_field is not None:
        n = _to_number(count_field)
        if n is None or n < 0:
            flags.append("unit_count_not_numeric_ignored")
        elif units and int(n) != len(units):
            # VIN list and declared count disagree: rate on the larger (never fewer units than VINs listed)
            flags.append(f"unit_count_{int(n)}_vs_{len(units)}_vins_use_max")
            unit_count_only = max(int(n), len(units))
        elif not units:
            unit_count_only = int(n); flags.append("units_given_as_count_no_vins")
    vins = []
    for u in units:
        v = (u.get("vin") if isinstance(u, dict) else u) or ""
        v = str(v).strip().upper()
        if VIN_RE.match(v):
            vins.append(v)
        else:
            flags.append(f"invalid_vin:{v[:17]}")
    out["vins"] = vins
    if unit_count_only:
        out["declared_units"] = unit_count_only
    elif units:
        out["declared_units"] = len(units)
    else:
        out["declared_units"] = None
        flags.append("units_missing_use_census")
    # radius: band name, alias, or a number of miles (int, float or numeric string)
    r_raw = _pick(sub, "radius", flags)
    r = str(r_raw if r_raw is not None else "").strip().lower().replace(" ", "_").replace("-", "_") if not isinstance(r_raw, (int, float)) or isinstance(r_raw, bool) else ""
    out["radius"] = r if r in RADII else RADIUS_ALIASES.get(r.replace("_", "-") if re.fullmatch(r"\d+_\d+", r) else r)
    if out["radius"] is None:
        miles = _to_number(r_raw)
        if miles is not None and miles >= 0:
            out["radius"] = _radius_from_miles(miles); flags.append(f"radius_miles:{miles}->{out['radius']}")
    if out["radius"] is None:
        m = re.search(r"(\d+)\s*(\+?)\s*(mi|mile)", str(r_raw or "").lower())   # "300 miles", "500+ mi" (+ = beyond)
        if m:
            miles = float(m.group(1)) + (1 if m.group(2) else 0)
            out["radius"] = _radius_from_miles(miles); flags.append(f"radius_miles:{m.group(1)}{m.group(2)}->{out['radius']}")
    if out["radius"] is None:
        out["radius"] = "intermediate_51_200"; flags.append("radius_missing_default_intermediate")
    # commodity
    c_raw = _pick(sub, "commodity", flags)
    if isinstance(c_raw, list):
        c_raw = ",".join(str(x) for x in c_raw); flags.append("commodity_list_joined")
    c = str(c_raw or "").strip().lower().replace(" ", "_")
    out["commodity_raw"] = c
    out["out_of_appetite_commodity"] = any(k in c for k in OUT_OF_APPETITE)
    out["commodity"] = COMMODITY_ALIASES.get(c, c) if c else "unknown"
    if not c:
        flags.append("commodity_missing_default_unknown")
    # state
    st = str(_pick(sub, "garaging_state", flags) or "").strip().upper()
    out["garaging_state"] = st if len(st) == 2 else None
    if out["garaging_state"] is None:
        flags.append("garaging_state_missing_use_census")
    # limit
    lim_raw = _pick(sub, "limit", flags)
    lim = _to_number(lim_raw)
    if lim_raw is not None and lim is None:
        flags.append("limit_not_numeric_default_1m")
    elif isinstance(lim_raw, str) and lim is not None:
        flags.append(f"limit_parsed:{lim_raw}->{int(lim)}")
    out["limit"] = int(lim) if lim is not None and lim > 0 else 1000000
    ih = _pick(sub, "insurance_history", flags) or {}
    ih = ih if isinstance(ih, dict) else {}
    out["insurance_cancellation_24m"] = bool(ih.get("cancellation_24m", False))
    out["ingest_flags"] = flags
    return out
