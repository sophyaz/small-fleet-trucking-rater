"""Generates SYNTHETIC fixtures (fake QCMobile/vPIC responses) + submissions so the pipeline runs offline.
USDOTs 9900001+ are fake. Replace with real carriers via analysis/build_sample_set.py once the census file is downloaded.
Run: python samples/make_synthetic_samples.py"""
import json, os, random, datetime as dt
random.seed(11)
HERE = os.path.dirname(os.path.abspath(__file__))
FX_C, FX_V, SUBS = [os.path.join(HERE, "fixtures", "carrier"), os.path.join(HERE, "fixtures", "vin"), os.path.join(HERE, "submissions")]
for d in (FX_C, FX_V, SUBS): os.makedirs(d, exist_ok=True)
today = dt.date.today()
def dstr(years_ago): return (today - dt.timedelta(days=int(years_ago * 365.25))).strftime("%Y-%m-%d")
def vin(i): return f"1FUJGLDR{str(i).zfill(2)}LLA{random.randint(10000,99999)}"[:17].ljust(17, "0")

profiles = []
# name, units, drivers, auth_age, state, radius, commodity, crashes(fatal,inj,tot), insp(d,v), oos(d,v), rating, extras
P = [
 ("established_clean_ia", 3, 3, 8, "IA", "intermediate_51_200", "dry_van", (0,0,0), (12,15), (.03,.15), None, {}),
 ("established_clean_tx", 4, 4, 6, "TX", "regional_201_500", "reefer", (0,0,1), (10,12), (.05,.20), None, {}),
 ("new_venture_ga", 1, 1, 0.3, "GA", "long_haul_500_plus", "dry_van", (0,0,0), (0,0), (None,None), None, {}),
 ("new_venture_ca_2units", 2, 2, 0.8, "CA", "long_haul_500_plus", "flatbed", (0,0,0), (2,2), (.0,.5), None, {}),
 ("owner_op_local_oh", 1, 1, 12, "OH", "local_0_50", "building_materials", (0,0,0), (6,7), (.0,.14), None, {}),
 ("mid_age_fl_one_crash", 2, 2, 2.5, "FL", "regional_201_500", "dry_van", (0,1,1), (5,6), (.2,.33), None, {}),
 ("high_crash_la", 3, 4, 4, "LA", "long_haul_500_plus", "dry_van", (0,2,4), (9,11), (.22,.45), None, {}),
 ("fatal_plus_one_tx", 2, 2, 5, "TX", "long_haul_500_plus", "flatbed", (1,0,2), (8,9), (.12,.3), None, {}),
 ("conditional_rating_il", 5, 6, 9, "IL", "intermediate_51_200", "general_freight", (0,0,1), (20,25), (.10,.28), "CONDITIONAL", {}),
 ("unsat_rating_mo", 3, 3, 7, "MO", "regional_201_500", "dry_van", (0,1,2), (15,18), (.3,.5), "UNSATISFACTORY", {}),
 ("oos_order_nj", 2, 2, 3, "NJ", "intermediate_51_200", "dry_van", (0,0,0), (4,4), (.5,.75), None, {"oosDate": dstr(0.2)}),
 ("stale_mcs150_ky", 2, 2, 10, "KY", "intermediate_51_200", "logs_lumber", (0,0,0), (3,4), (.0,.25), None, {"mcs150_years": 3.5}),
 ("hazmat_flag_ok", 2, 2, 6, "OK", "regional_201_500", "dry_van", (0,0,0), (5,5), (.0,.2), None, {"hazmat": True}),
 ("six_units_pa", 6, 7, 5, "PA", "regional_201_500", "dry_van", (0,0,1), (18,20), (.05,.2), None, {}),
 ("private_carrier_wi", 3, 3, 15, "WI", "local_0_50", "grain_feed", (0,0,0), (4,4), (.0,.25), None, {"opclass": ["private(property)"]}),
 ("basic_alert_unsafe_az", 4, 5, 6, "AZ", "long_haul_500_plus", "reefer", (0,1,2), (25,30), (.12,.3), None, {"basics": {"unsafe driving": 93}}),
 ("basic_elevated_hos_nc", 3, 3, 4, "NC", "regional_201_500", "dry_van", (0,0,0), (14,16), (.08,.22), None, {"basics": {"hos compliance": 72, "vehicle maintenance": 60}}),
 ("cancelled_insurance_sc", 2, 2, 3, "SC", "regional_201_500", "dry_van", (0,0,0), (6,6), (.05,.2), None, {"cancel": True}),
 ("more_drivers_than_units_ny", 2, 5, 4, "NY", "local_0_50", "dry_van", (0,0,1), (10,10), (.1,.3), None, {}),
 ("old_trucks_mt", 2, 2, 20, "MT", "regional_201_500", "logs_lumber", (0,0,0), (5,5), (.0,.3), None, {"model_years": [2004, 2006]}),
 ("young_driver_nv", 1, 1, 1.5, "NV", "long_haul_500_plus", "dry_van", (0,0,0), (3,3), (.0,.33), None, {"cdl_years": [1]}),
 ("intermodal_wa", 3, 3, 5, "WA", "local_0_50", "intermodal", (0,0,1), (11,13), (.09,.23), None, {}),
 ("trailer_vin_submitted_tn", 2, 2, 5, "TN", "regional_201_500", "dry_van", (0,0,0), (6,6), (.0,.2), None, {"trailer_vins": True}),
 ("unit_mismatch_mi", 2, 2, 5, "MI", "regional_201_500", "dry_van", (0,0,0), (6,6), (.0,.2), None, {"census_units": 9}),
 ("high_mileage_ne", 2, 2, 7, "NE", "long_haul_500_plus", "dry_van", (0,0,0), (9,9), (.0,.2), None, {"mileage": 380000}),
]
for i, (name, units, drivers, age, st, radius, comm, (fat, inj, tot), (di, vi), (dr, vr), rating, ex) in enumerate(P):
    dot = 9900001 + i
    census_units = ex.get("census_units", units)
    carrier = {"dotNumber": dot, "legalName": name.upper().replace("_", " ") + " LLC", "phyState": st,
               "allowedToOperate": "Y", "statusCode": "A", "totalPowerUnits": census_units, "totalDrivers": drivers,
               "driverOosRate": None if dr is None else round(dr * 100, 2), "vehicleOosRate": None if vr is None else round(vr * 100, 2),
               "driverOosRateNationalAverage": "6.67", "vehicleOosRateNationalAverage": "22.26",
               "driverInsp": di, "vehicleInsp": vi, "crashTotal": tot, "fatalCrash": fat, "injCrash": inj, "towawayCrash": tot - fat - inj,
               "safetyRating": rating, "oosDate": ex.get("oosDate"), "addDate": dstr(age),
               "mcs150Date": dstr(ex.get("mcs150_years", 0.6)), "mcs150Mileage": ex.get("mileage", units * 85000),
               "hazmatFlag": "Y" if ex.get("hazmat") else "N", "pcFlag": "N",
               "carrierOperation": {"carrierOperationDesc": "Interstate"}}
    basics = [{"basic": {"basicsType": {"basicsShortDesc": k}, "basicsPercentile": v}} for k, v in ex.get("basics", {}).items()]
    raw = {"_synthetic": True, "carrier": {"content": {"carrier": carrier}}, "basics": {"content": basics},
           "cargo-carried": {"content": [{"cargoClassDesc": "General Freight"}]},
           "operation-classification": {"content": [{"operationClassDesc": x} for x in ex.get("opclass", ["Auth. For Hire"])]},
           "authority": {"content": []}}
    with open(os.path.join(FX_C, f"{dot}.json"), "w") as f: json.dump(raw, f, indent=1)
    vins = []
    for u in range(units):
        v = vin(i * 10 + u)
        my = ex.get("model_years", [random.randint(2015, 2023)] * units)[u % len(ex.get("model_years", [1]))] if "model_years" in ex else random.randint(2015, 2023)
        dec = {"vin": v, "decoded": True, "make": "FREIGHTLINER", "model": "Cascadia", "model_year": my,
               "gvwr": "Class 8: 33,001 lb & above", "body_class": "Truck-Tractor", "vehicle_type": "TRUCK", "error_code": "0"}
        if ex.get("trailer_vins"):
            dec.update({"make": "GREAT DANE", "model": "Van", "body_class": "Trailer", "vehicle_type": "TRAILER", "gvwr": "Class 8"})
        with open(os.path.join(FX_V, f"{v}.json"), "w") as f: json.dump(dec, f)
        vins.append({"vin": v})
    drv = [{"age": random.randint(28, 58), "cdl_years": ex.get("cdl_years", [random.randint(4, 25)])[0] if "cdl_years" in ex else random.randint(4, 25)} for _ in range(drivers)]
    sub = {"submission_id": name, "usdot": dot, "drivers": drv, "units": vins, "radius": radius, "commodity": comm,
           "garaging_state": st, "limit": 1000000}
    if ex.get("cancel"): sub["insurance_history"] = {"cancellation_24m": True, "prior_carrier": "Progressive"}
    with open(os.path.join(SUBS, f"{i:02d}_{name}.json"), "w") as f: json.dump(sub, f, indent=1)

# edge cases with no fixture
edge = [
 ("50_edge_unknown_dot", {"submission_id": "unknown_dot", "usdot": 9999999, "units": [{"vin": "1FUJGLDR11LLA12345"}], "radius": "regional", "commodity": "dry van", "garaging_state": "TX"}),
 ("51_edge_missing_usdot", {"submission_id": "missing_usdot", "drivers": [], "units": []}),
 ("52_edge_bad_vins_no_radius", {"submission_id": "bad_vins", "usdot": "USDOT 9900001", "units": [{"vin": "NOTAVIN"}, {"vin": ""}], "commodity": ""}),
 ("53_edge_zero_drivers", {"submission_id": "zero_drivers", "usdot": 9900005, "driver_count": 0, "units": [{"vin": "1FUJGLDR40LLA55555"}], "radius": "local", "commodity": "dry_van", "garaging_state": "OH"}),
 ("54_edge_garbage_types", {"submission_id": "garbage", "usdot": 9900001, "drivers": "three", "units": "two trucks", "radius": 200, "limit": "1m"}),
]
for fn, s in edge:
    with open(os.path.join(SUBS, fn + ".json"), "w") as f: json.dump(s, f, indent=1)
with open(os.path.join(SUBS, "55_edge_not_json.json"), "w") as f: f.write("{this is not json")
print("wrote", len(P), "synthetic carriers +", len(edge) + 1, "edge cases")
