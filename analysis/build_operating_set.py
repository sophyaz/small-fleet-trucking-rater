"""Track C: a draw that mimics a REAL broker submission flow.

The census `authorized_for_hire` flag is self-declared on the MCS-150 and goes stale, so a
random census draw over-samples dormant shells (authority lapsed, no BI/PD filing) that no
broker would ever submit. This draws candidates, enriches them, and keeps only carriers that
look like they are actually operating:
    commonAuthorityStatus == 'A' (or contract authority active)  AND  bipdInsuranceOnFile > 0
It reports the keep rate, which is the number that tells us how much a random census draw
overstates the decline rate.
"""
import json, os, glob, sys
import pandas as pd
sys.path.insert(0, r"C:\Users\sophi\trucking-rater\trucking-rater")
from rater import enrich

ROOT = r"C:\Users\sophi\trucking-rater\trucking-rater"
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "samples", "submissions_operating")
FOCUS = {"TX", "CA", "FL", "GA", "IL", "LA", "NY", "IA", "OH", "PA"}

seen = set()
for p in glob.glob(os.path.join(ROOT, "data", "cache", "carrier", "*.json")):
    seen.add(int(os.path.basename(p)[:-5]))
for p in glob.glob(os.path.join(ROOT, "samples", "**", "*.json"), recursive=True):
    try: obj = json.load(open(p))
    except Exception: continue
    for o in (obj if isinstance(obj, list) else [obj]):
        if isinstance(o, dict) and "usdot" in o:
            try: seen.add(int(o["usdot"]))
            except Exception: pass

USE = ["dot_number", "phy_state", "nbr_power_unit", "driver_total", "carrier_operation",
       "hm_flag", "pc_flag", "authorized_for_hire", "add_date", "mcs150_date"]
cen = pd.read_csv(os.path.join(RAW, "census.csv"), usecols=USE, low_memory=False, encoding_errors="ignore")
cen["units"] = pd.to_numeric(cen["nbr_power_unit"], errors="coerce")
cen = cen[(cen.units >= 1) & (cen.units <= 5)]
T = {"Y", "TRUE", "1", "T"}
cen = cen[~cen.hm_flag.astype(str).str.upper().isin(T)]
cen = cen[~cen.pc_flag.astype(str).str.upper().isin(T)]
cen = cen[cen.carrier_operation.astype(str).str.upper().str.startswith("A")]
cen = cen[cen.authorized_for_hire.astype(str).str.upper().isin(T)]
cen["add_date"] = pd.to_datetime(cen["add_date"], format="%d-%b-%y", errors="coerce")
cen["mcs150"] = pd.to_datetime(cen["mcs150_date"], format="%d-%b-%y", errors="coerce")
cen["dotn"] = pd.to_numeric(cen["dot_number"], errors="coerce")
cen = cen[cen["dotn"].notna()]
cen["dotn"] = cen["dotn"].astype(int)
cen = cen[~cen["dotn"].isin(seen) & ~cen.phy_state.isin(FOCUS) & cen.add_date.notna()]

now = pd.Timestamp.today()
cen["auth_age"] = (now - cen["add_date"]).dt.days / 365.25
# A broker's submission flow skews to carriers that filed an MCS-150 recently -> still trading.
cen = cen[cen.mcs150.notna() & ((now - cen.mcs150).dt.days / 365.25 < 2)]
print(f"candidate pool (MCS-150 filed within 2y, unseen, non-focus state): {len(cen):,}")

CANDIDATES = 60
cand = pd.concat([
    b.sample(min(CANDIDATES // 3, len(b)), random_state=777).assign(bucket=n)
    for n, b in {"new": cen[cen.auth_age < 1],
                 "mid": cen[(cen.auth_age >= 1) & (cen.auth_age < 3)],
                 "est": cen[cen.auth_age >= 3]}.items() if len(b)
])
print(f"enriching {len(cand)} candidates...")

def operating(dot):
    try: rec = enrich.fetch_carrier(int(dot))
    except Exception as e: return None, f"fetch_error:{e}"
    if not rec.get("found"): return None, "not_found_in_qcmobile"
    common = rec.get("common_authority_status"); contract = rec.get("contract_authority_status")
    bipd = rec.get("bipd_insurance_on_file_k") or 0
    ok = bool(rec.get("active_for_hire_authority")) and bipd > 0
    return ok, (f"common={common} contract={contract} bipd_k={bipd:g} "
                f"active_auth={rec.get('active_for_hire_authority')} allowed={rec.get('allowed_to_operate')}")

kept, reasons = [], []
for _, r in cand.iterrows():
    ok, why = operating(r["dotn"])
    reasons.append((int(r["dotn"]), ok, why))
    if ok: kept.append(r)
print(f"\noperating (active authority + BI/PD on file): {len(kept)} / {len(cand)}  = {100*len(kept)/len(cand):.0f}% keep rate")
for dot, ok, why in reasons[:12]:
    print(f"  {dot}  {'KEEP' if ok else 'drop'}  {why}")

RADII = ["local_0_50", "intermediate_51_200", "regional_201_500", "long_haul_500_plus"]
COMMOD = ["general_freight", "dry_van", "reefer", "general_freight", "flatbed", "dry_van"]
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, "*")): os.remove(f)
for i, r in enumerate(kept):
    dot = int(r["dotn"])
    drv = pd.to_numeric(r.driver_total, errors="coerce")
    json.dump({"submission_id": f"op-{dot}", "usdot": dot,
               "driver_count": int(drv) if pd.notna(drv) and drv > 0 else int(r.units),
               "power_units": int(r.units), "radius": RADII[i % 4], "commodity": COMMOD[i % 6],
               "garaging_state": str(r.phy_state), "limit": 1000000},
              open(os.path.join(OUT, f"{dot}.json"), "w"), indent=1)
print(f"\nwrote {len(kept)} operating-carrier submissions -> {OUT}")
