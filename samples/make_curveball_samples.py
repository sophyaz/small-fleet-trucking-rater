"""Simulate the file Corgi actually hands you at the presentation: their shape, not yours.
Real unseen DOTs, messy headers, human-typed values, and a few genuinely bad rows."""
import csv, json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "samples", "submissions_curveball")
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, "*")): os.remove(f)

# real, already-enriched holdout DOTs so this runs offline too
dots = [int(os.path.basename(p).split("_")[1][:-5])
        for p in sorted(glob.glob(os.path.join(ROOT, "samples", "submissions_holdout", "*.json")))][:8]

# 1) a broker's CSV export: alias headers, commas in numbers, "1M" limit, miles not bands
with open(os.path.join(OUT, "01_broker_export.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["DOT Number", "Company", "# Trucks", "Drivers", "Radius (mi)", "Freight", "State", "Limit"])
    rows = [
        (dots[0], "Acme Hauling LLC", "2", "2", "250", "Dry Van", "Tennessee", "1,000,000"),
        (dots[1], "Bell Transport",   "1", "1", "45",  "reefer",  "co",        "1M"),
        (dots[2], "Cobb Freight Inc", "3", "4", "600", "Flat Bed","KANSAS",    "750k"),
        (dots[3], "Dune Logistics",   "1", "1", "",    "",        "",          ""),   # sparse but valid
    ]
    for r in rows: w.writerow(r)

# 2) JSON array, nested one level, USDOT as a prefixed string, VIN list as bare strings
json.dump([
    {"carrier": {"USDOT": f"USDOT {dots[4]}", "vins": ["1FUJGLDR3CLBP8834"],
                 "operating_radius": "500+ miles", "cargo": "General Freight",
                 "domicile_state": "Indiana", "csl": 1000000, "num_drivers": 2}},
    {"carrier": {"dot_number": float(dots[5]), "power_units": 2, "driver_count": 2,
                 "radius": {"miles": 150}, "commodity": "dry van", "state": "MI"}},
], open(os.path.join(OUT, "02_nested_array.json"), "w"), indent=1)

# 3) JSONL feed with genuinely bad rows mixed in among good ones
with open(os.path.join(OUT, "03_feed.jsonl"), "w") as f:
    f.write(json.dumps({"usdot": dots[6], "power_units": 1, "radius": "local", "commodity": "dry_van"}) + "\n")
    f.write(json.dumps({"usdot": "not-a-number", "power_units": 1}) + "\n")          # unparseable DOT
    f.write(json.dumps({"power_units": 2, "commodity": "dry_van"}) + "\n")            # no DOT at all
    f.write(json.dumps({"usdot": 99999999, "power_units": 1}) + "\n")                 # DOT not in FMCSA
    f.write(json.dumps({"usdot": dots[7], "power_units": -4, "drivers": "three",
                        "radius": "banana", "limit": "lots", "commodity": 12345}) + "\n")  # every field wrong
    f.write("{ this is not json at all\n")                                            # corrupt line

# 4) a single bare VIN string + unit count disagreement
json.dump({"usdot": dots[0], "units": "1FUJGLDR3CLBP8834", "power_units": 4,
           "radius": "regional", "commodity": "dry_van", "state": "TN"},
          open(os.path.join(OUT, "04_vin_count_conflict.json"), "w"), indent=1)

# 5) empty file and an empty array — the classic "exported nothing"
open(os.path.join(OUT, "05_empty.json"), "w").close()
json.dump([], open(os.path.join(OUT, "06_empty_array.json"), "w"))

print("wrote curveballs:", sorted(os.path.basename(p) for p in glob.glob(os.path.join(OUT, "*"))))
print("using real unseen DOTs:", dots)
