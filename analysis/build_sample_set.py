"""Draw a stratified sample of REAL carriers from the census file for samples/submissions/, then enrich + cache them.
Run after downloading census.csv:  python -m analysis.build_sample_set --n 40
Requires FMCSA_WEBKEY for enrichment (or run with --no-enrich and enrich later)."""
import argparse, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.build_frequency_tables import load_census, ROOT
from rater import enrich

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=40); ap.add_argument("--no-enrich", action="store_true")
    a = ap.parse_args()
    cen = load_census(); now = pd.Timestamp.today()
    cen["auth_age"] = (now - cen["add_date"]).dt.days / 365.25
    strata = {"new": cen[cen.auth_age < 1], "mid": cen[(cen.auth_age >= 1) & (cen.auth_age < 3)], "est": cen[cen.auth_age >= 3]}
    focus_states = ["TX", "CA", "FL", "GA", "IL", "LA", "NY", "IA", "OH", "PA"]
    rows = []
    for name, s in strata.items():
        k = a.n // 3
        s2 = s[s["state"].isin(focus_states)]
        rows.append(s2.sample(min(k, len(s2)), random_state=1))
    samp = pd.concat(rows)
    out = os.path.join(ROOT, "samples", "submissions_real"); os.makedirs(out, exist_ok=True)
    for _, r in samp.iterrows():
        sub = {"submission_id": f"real-{int(r.dot)}", "usdot": int(r.dot), "driver_count": int(r.get("drivers") or r.units),
               "units": [], "radius": "intermediate_51_200", "commodity": "dry_van", "garaging_state": str(r.state),
               "limit": 1000000, "_note": "radius/commodity defaulted; VINs not public — add from submission if given"}
        with open(os.path.join(out, f"{int(r.dot)}.json"), "w") as f: json.dump(sub, f, indent=1)
        if not a.no_enrich: enrich.fetch_carrier(int(r.dot))
    print(f"wrote {len(samp)} real-carrier submissions to {out}")

if __name__ == "__main__":
    main()
