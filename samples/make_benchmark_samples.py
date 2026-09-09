"""Synthetic submissions that mirror the observed market price points in docs/MARKET_BENCHMARK.md.

Same fixture format as make_synthetic_samples.py (fake QCMobile/vPIC responses so the pipeline runs offline).
USDOTs 9900101+ are fake and do not collide with the 9900001+ range used by the main synthetic set.

  python samples/make_benchmark_samples.py          # write fixtures + submissions
  python samples/make_benchmark_samples.py --run    # ...then run `python -m rater` on each and tabulate vs observed

Observed figures are entered here only so the table can be printed; the source of truth for each is the doc."""
import json, os, random, subprocess, sys, datetime as dt
random.seed(23)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FX_C, FX_V, SUBS = [os.path.join(HERE, "fixtures", "carrier"), os.path.join(HERE, "fixtures", "vin"), os.path.join(HERE, "submissions_benchmark")]
for d in (FX_C, FX_V, SUBS): os.makedirs(d, exist_ok=True)
today = dt.date.today()
def dstr(years_ago): return (today - dt.timedelta(days=int(years_ago * 365.25))).strftime("%Y-%m-%d")
def vin(i): return f"1FUJGLDR{str(i).zfill(2)}MLA{random.randint(10000,99999)}"[:17].ljust(17, "0")

# id, units, drivers, cdl_years per driver, authority_age_yrs, state, radius, commodity, crashes(fatal,inj,tot), insp(d,v),
# oos(d,v), model_years, mileage_per_unit, observed_annual_per_unit (all-in as published), observed_liability_est_per_unit, label
P = [
 ("B01_progressive_transport_2025", 1, 1, [8],  3.0, "CO", "long_haul_500_plus", "dry_van", (0,0,0), (4,5), (.05,.20), [2019], 100000,
  11112, 7800, "Progressive: 2025 new for-hire transport policies, $926/mo per power unit, liability+PD, no violations"),
 ("B02_progressive_specialty_2025", 1, 1, [12], 5.0, "CO", "local_0_50", "building_materials", (0,0,0), (3,4), (.05,.20), [2017], 40000,
  8808, 6200, "Progressive: 2025 new for-hire specialty policies, $734/mo per power unit, liability+PD, no violations"),
 ("B03_overdrive_castaldi_fl_reefer", 1, 2, [40, 15], 39.0, "FL", "long_haul_500_plus", "reefer", (0,0,0), (8,10), (.0,.10), [2003], 150000,
  15000, 12000, "Overdrive 2025-03-21: M. Castaldi, 1 truck (2003 Pete), FL, authority since 1986, reefer FL-AZ team, ~150k mi/yr, 'just north of $15,000'"),
 ("B04_overdrive_poll_median_ga", 1, 1, [10], 6.0, "GA", "regional_201_500", "dry_van", (0,0,0), (5,6), (.05,.20), [2018], 90000,
  12500, 12500, "Overdrive 2024 reader poll (pub. 2025-03): liability, 24% >$15k, 48% <$10k -> modal band $10-15k, one-truck independents"),
 ("B05_overdrive_new_authority_tx", 1, 1, [6],  0.3, "TX", "long_haul_500_plus", "dry_van", (0,0,0), (0,0), (None,None), [2020], 100000,
  14000, 14000, "Overdrive insurance guide (2025): new-authority quotes $8k-$20k+, '$10,000 or more a year for $1M primary liability'"),
 ("B06_freightwaves_established_in", 1, 1, [9],  5.0, "IN", "intermediate_51_200", "dry_van", (0,0,0), (6,7), (.03,.15), [2023], 80000,
  11250, 11250, "FreightWaves Checkpoint 2026-03-26: auto liability $7,500-$15,000+/tractor, experienced OO, established authority, late-model tractor"),
 ("B07_freightwaves_one_truck_il", 1, 1, [7],  2.0, "IL", "regional_201_500", "dry_van", (0,0,0), (3,3), (.0,.33), [2019], 95000,
  14500, 12500, "FreightWaves 2025-05-08 (MarketWatch): one-truck liability+cargo $12-17k in 2025 (was $11-16k late-2023)"),
 ("B08_atri_small_fleet_pa", 5, 6, [4, 6, 9, 12, 15, 20], 8.0, "PA", "long_haul_500_plus", "general_freight", (0,0,1), (22,26), (.06,.22), [2018, 2019, 2020, 2021, 2021], 86000,
  18137, 18137, "ATRI 2025 Ops Costs via CCJ: fleets <=25 trucks 20.3c/mi liability premiums (2024) x 85,991 mi = $17,456; +3.9% for 2025 = $18,137"),
 ("B09_atri_industry_avg_wi", 3, 3, [8, 14, 22], 10.0, "WI", "regional_201_500", "dry_van", (0,0,0), (10,12), (.05,.20), [2019, 2020, 2022], 86000,
  8600, 8600, "ATRI 2026 update via FleetOwner 2026-07-22: $0.106/mi all-fleet 2025; Midwest $0.10 x 85,991 mi = $8,600/unit (liability+cargo)"),
 ("B10_geotab_small_fleet_nc", 3, 3, [5, 9, 11], 3.0, "NC", "long_haul_500_plus", "dry_van", (0,0,0), (9,10), (.05,.20), [2019, 2021, 2022], 100000,
  14400, 11500, "Geotab 2026-08-20: small fleet $10,800-$18,000+/truck bundled; OO with authority $9,000-$17,000"),
]

for i, (name, units, drivers, cdl, age, st, radius, comm, (fat, inj, tot), (di, vi), (dr, vr), mys, mpu, obs_all, obs_liab, label) in enumerate(P):
    dot = 9900101 + i
    carrier = {"dotNumber": dot, "legalName": name.upper().replace("_", " ") + " LLC", "phyState": st,
               "allowedToOperate": "Y", "statusCode": "A", "totalPowerUnits": units, "totalDrivers": drivers,
               "driverOosRate": None if dr is None else round(dr * 100, 2), "vehicleOosRate": None if vr is None else round(vr * 100, 2),
               "driverOosRateNationalAverage": "6.67", "vehicleOosRateNationalAverage": "22.26",
               "driverInsp": di, "vehicleInsp": vi, "crashTotal": tot, "fatalCrash": fat, "injCrash": inj, "towawayCrash": tot - fat - inj,
               "safetyRating": None, "oosDate": None, "addDate": dstr(age),
               "mcs150Date": dstr(0.5), "mcs150Mileage": mpu * units,
               "hazmatFlag": "N", "pcFlag": "N", "carrierOperation": {"carrierOperationDesc": "Interstate"}}
    raw = {"_synthetic": True, "_benchmark": label, "carrier": {"content": {"carrier": carrier}}, "basics": {"content": []},
           "cargo-carried": {"content": [{"cargoClassDesc": "General Freight"}]},
           "operation-classification": {"content": [{"operationClassDesc": "Auth. For Hire"}]},
           "authority": {"content": []}}
    with open(os.path.join(FX_C, f"{dot}.json"), "w") as f: json.dump(raw, f, indent=1)
    vins = []
    for u in range(units):
        v = vin(50 + i * 10 + u)
        dec = {"vin": v, "decoded": True, "make": "FREIGHTLINER", "model": "Cascadia", "model_year": mys[u % len(mys)],
               "gvwr": "Class 8: 33,001 lb & above", "body_class": "Truck-Tractor", "vehicle_type": "TRUCK", "error_code": "0"}
        with open(os.path.join(FX_V, f"{v}.json"), "w") as f: json.dump(dec, f)
        vins.append({"vin": v})
    drv = [{"age": random.randint(30, 58), "cdl_years": cdl[k % len(cdl)]} for k in range(drivers)]
    sub = {"submission_id": name, "usdot": dot, "drivers": drv, "units": vins, "radius": radius, "commodity": comm,
           "garaging_state": st, "limit": 1000000,
           "_benchmark": {"observed_annual_per_unit_as_published": obs_all, "observed_liability_est_per_unit": obs_liab, "source": label}}
    with open(os.path.join(SUBS, f"{i:02d}_{name}.json"), "w") as f: json.dump(sub, f, indent=1)
print("wrote", len(P), "benchmark carriers ->", SUBS)

if "--run" in sys.argv:
    env = {**os.environ, "RATER_OFFLINE": "1"}
    rows = []
    for fn in sorted(os.listdir(SUBS)):
        p = os.path.join(SUBS, fn)
        out = subprocess.run([sys.executable, "-m", "rater", p], cwd=ROOT, env=env, capture_output=True, text=True)
        r = json.loads(out.stdout)
        with open(p) as f: b = json.load(f)["_benchmark"]
        bd = r.get("breakdown", {})
        units = bd.get("units", 1)
        ours_unit = (r["premium_if_written"] - bd.get("policy_fee", 0)) / units
        rows.append({"id": r["submission_id"], "decision": r["decision"], "rules": ",".join(x.get("id", str(x)) if isinstance(x, dict) else str(x) for x in r["rules_fired"]), "units": units,
                     "ours_total": r["premium_if_written"], "ours_per_unit": round(ours_unit),
                     "tech_per_unit": bd.get("technical_premium_per_unit"), "min_binding": bd.get("min_premium_binding"),
                     "rel_product": bd.get("relativity_product_capped"),
                     "obs_all_in": b["observed_annual_per_unit_as_published"], "obs_liab": b["observed_liability_est_per_unit"],
                     "gap_vs_liab_pct": round(100 * (ours_unit / b["observed_liability_est_per_unit"] - 1), 1),
                     "gap_vs_all_in_pct": round(100 * (ours_unit / b["observed_annual_per_unit_as_published"] - 1), 1)})
    import csv
    outp = sys.argv[sys.argv.index("--run") + 1] if len(sys.argv) > sys.argv.index("--run") + 1 else os.path.join(ROOT, "data", "derived", "market_benchmark.csv")
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    with open(outp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    for r in rows: print(json.dumps(r))
    print("->", outp)
