"""Draw a HOLDOUT set of real carriers the rater has never seen.

Rules of the draw:
  - in-segment: interstate (A), authorized for hire, not HM, not PC, 1-5 power units
  - EXCLUDE every DOT already in data/cache/carrier or any samples/ folder
  - EXCLUDE the 10 focus states the original real sample drew from, so the geography is new
  - stratify by authority age (new / mid / established) and fleet size
  - Track B carriers additionally appear in the MCMIS crash file, so we can attach their OWN
    real power-unit VINs (vehicle_identification_number) and exercise the VIN-decode path.
"""
import json, os, sys, glob
import pandas as pd

ROOT = r"C:\Users\sophi\trucking-rater\trucking-rater"
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "samples", "submissions_holdout")
FOCUS_ALREADY_USED = {"TX", "CA", "FL", "GA", "IL", "LA", "NY", "IA", "OH", "PA"}

# ---- what the rater has already seen -------------------------------------------------
seen = set()
for p in glob.glob(os.path.join(ROOT, "data", "cache", "carrier", "*.json")):
    seen.add(int(os.path.basename(p)[:-5]))
for p in glob.glob(os.path.join(ROOT, "samples", "**", "*.json"), recursive=True):
    try:
        obj = json.load(open(p))
    except Exception:
        continue
    for o in (obj if isinstance(obj, list) else [obj]):
        if isinstance(o, dict):
            for k in ("usdot", "dot", "dot_number", "usdot_number"):
                if k in o:
                    try: seen.add(int(float(str(o[k]).strip().split()[-1])))
                    except Exception: pass
print(f"already-seen DOTs: {len(seen)}")

# ---- census, in-segment ---------------------------------------------------------------
USE = ["dot_number", "legal_name", "phy_state", "nbr_power_unit", "driver_total",
       "carrier_operation", "hm_flag", "pc_flag", "authorized_for_hire", "add_date",
       "mcs150_mileage"]
cen = pd.read_csv(os.path.join(RAW, "census.csv"), usecols=USE, low_memory=False,
                  encoding_errors="ignore")
cen["units"] = pd.to_numeric(cen["nbr_power_unit"], errors="coerce")
cen = cen[(cen.units >= 1) & (cen.units <= 5)]
T = {"Y", "TRUE", "1", "T"}
cen = cen[~cen.hm_flag.astype(str).str.upper().isin(T)]
cen = cen[~cen.pc_flag.astype(str).str.upper().isin(T)]
cen = cen[cen.carrier_operation.astype(str).str.upper().str.startswith("A")]
cen = cen[cen.authorized_for_hire.astype(str).str.upper().isin(T)]
cen["add_date"] = pd.to_datetime(cen["add_date"], format="%d-%b-%y", errors="coerce")
cen["dotn"] = pd.to_numeric(cen["dot_number"], errors="coerce")
cen = cen[cen["dotn"].notna()]
cen["dotn"] = cen["dotn"].astype(int)
cen = cen[~cen["dotn"].isin(seen)]
cen = cen[~cen.phy_state.isin(FOCUS_ALREADY_USED)]
now = pd.Timestamp.today()
cen["auth_age"] = (now - cen["add_date"]).dt.days / 365.25
cen = cen[cen.auth_age.notna()]
print(f"in-segment, unseen, non-focus-state carriers: {len(cen):,}")

# ---- Track B pool: carriers with their own real VINs in the crash file ----------------
cr = pd.concat([
    pd.read_csv(os.path.join(RAW, f), low_memory=False, encoding_errors="ignore",
                usecols=["dot_number", "vehicle_identification_number", "report_date"])
    for f in ("crash_2025.csv", "crash_2026.csv")
])
cr["dotn"] = pd.to_numeric(cr["dot_number"], errors="coerce")
cr = cr[cr["dotn"].notna() & cr.vehicle_identification_number.notna()]
cr["dotn"] = cr["dotn"].astype(int)
cr["vin"] = cr["vehicle_identification_number"].astype(str).str.strip().str.upper()
cr = cr[cr.vin.str.len() == 17]
vins = cr.groupby("dotn")["vin"].apply(lambda s: sorted(set(s))).to_dict()
print(f"crash-file carriers with a valid 17-char VIN: {len(vins):,}")

with_vin = cen[cen["dotn"].isin(vins.keys())]
print(f"  ...of which unseen + in-segment + non-focus-state: {len(with_vin):,}")

# ---- the draw --------------------------------------------------------------------------
SEED = 20260910
def strat(df, n, seed):
    buckets = {"new": df[df.auth_age < 1],
               "mid": df[(df.auth_age >= 1) & (df.auth_age < 3)],
               "est": df[df.auth_age >= 3]}
    out = []
    for name, b in buckets.items():
        if len(b):
            out.append(b.sample(min(n, len(b)), random_state=seed).assign(bucket=name))
    return pd.concat(out)

trackA = strat(cen[~cen["dotn"].isin(vins.keys())], 6, SEED)          # clean, no VINs supplied
trackB = strat(with_vin, 4, SEED + 1)                              # real own VINs, crash-involved

RADII = ["local_0_50", "intermediate_51_200", "regional_201_500", "long_haul_500_plus"]
COMMODITIES = ["general_freight", "dry_van", "reefer", "general_freight", "flatbed", "dry_van",
               "general_freight", "reefer", "dry_van", "flatbed", "general_freight", "dry_van",
               "auto_hauler", "general_freight", "tanker_non_haz"]   # 2 of 15 deliberately out of appetite

os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, "*")): os.remove(f)

def write(df, track, attach_vins):
    n = 0
    for i, (_, r) in enumerate(df.iterrows()):
        dot = int(r["dotn"])
        drv = pd.to_numeric(r.driver_total, errors="coerce")
        sub = {
            "submission_id": f"holdout-{track}-{dot}",
            "usdot": dot,
            "driver_count": int(drv) if pd.notna(drv) and drv > 0 else int(r.units),
            "radius": RADII[i % len(RADII)],
            "commodity": COMMODITIES[i % len(COMMODITIES)],
            "garaging_state": str(r.phy_state),
            "limit": 1000000,
        }
        if attach_vins:
            sub["units"] = [{"vin": v} for v in vins[dot][: int(r.units)]]
            sub["power_units"] = int(r.units)
        else:
            sub["power_units"] = int(r.units)
        json.dump(sub, open(os.path.join(OUT, f"{track}_{dot}.json"), "w"), indent=1)
        n += 1
    return n

a = write(trackA, "A", False)
b = write(trackB, "B", True)
print(f"\nwrote {a} Track-A (no VINs) + {b} Track-B (own real VINs) = {a+b} holdout submissions -> {OUT}")
print("\nstates drawn:", sorted(set(trackA.phy_state) | set(trackB.phy_state)))
print("auth-age buckets:", pd.concat([trackA, trackB]).bucket.value_counts().to_dict())
