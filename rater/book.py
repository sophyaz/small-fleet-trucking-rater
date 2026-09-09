"""Book check: python -m rater.book samples/submissions [--csv out.csv]"""
import argparse, glob, json, os, statistics, collections
from .price import price

def run(paths):
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, "*.json"))) if os.path.isdir(p) else [p]
    results = []
    for fp in files:
        try:
            with open(fp) as f: sub = json.load(f)
        except Exception as e:
            results.append({"submission_id": os.path.basename(fp), "decision": "error", "error": f"unreadable json: {e}", "premium": None, "rules_fired": [], "breakdown": {}})
            continue
        r = price(sub); r["_file"] = os.path.basename(fp); results.append(r)
    return results

def summarise(results):
    counts = collections.Counter(r["decision"] for r in results)
    n = len(results) or 1
    prem = [r["premium"] for r in results if r.get("premium")]
    per_unit = [r["breakdown"]["unit_premium"] for r in results if r.get("premium") and r.get("breakdown")]
    reasons = collections.Counter(x["id"] + " " + x["reason"] for r in results for x in r.get("rules_fired", []))
    minbind = sum(1 for r in results if r.get("breakdown", {}).get("min_premium_binding"))
    def q(xs, p):
        if not xs: return None
        xs = sorted(xs); i = max(0, min(len(xs) - 1, round(p * (len(xs) - 1)))); return xs[i]
    lines = ["=" * 64, "BOOK CHECK", "=" * 64,
             f"Submissions: {n}  priced={counts['price']}  referred={counts['refer']}  declined={counts['decline']}  errored={counts['error']}",
             f"Decline rate: {counts['decline']/n:.1%}   Refer rate: {counts['refer']/n:.1%}   Min-premium binding: {minbind}",
             "", "Premium distribution (priced + referred, total policy):"]
    if prem:
        lines += [f"  min {min(prem):,.0f}  p25 {q(prem,.25):,.0f}  median {statistics.median(prem):,.0f}  p75 {q(prem,.75):,.0f}  max {max(prem):,.0f}",
                  f"  per power unit: min {min(per_unit):,.0f}  median {statistics.median(per_unit):,.0f}  max {max(per_unit):,.0f}"]
    else:
        lines.append("  (none priced)")
    lines += ["", "Rules fired:"] + [f"  {k}: {v}" for k, v in reasons.most_common()]
    errs = [r for r in results if r["decision"] == "error"]
    lines += ["", f"Errored submissions ({len(errs)}):"] + [f"  {r.get('_file', r.get('submission_id'))}: {r['error']}" for r in errs]
    lines += ["", "Per submission:"]
    for r in results:
        rf = ",".join(x["id"] for x in r.get("rules_fired", []))
        p = f"{r['premium']:,.0f}" if r.get("premium") else "-"
        lines.append(f"  {r.get('_file', ''):32s} dot={str(r.get('usdot')):10s} {r['decision']:8s} premium={p:>10s} rules=[{rf}]")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+"); ap.add_argument("--csv"); ap.add_argument("--jsonl")
    a = ap.parse_args()
    res = run(a.paths); print(summarise(res))
    if a.csv:
        import csv
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["file", "usdot", "decision", "premium", "units", "unit_premium", "rel_product", "rules", "flags", "error"])
            for r in res:
                b = r.get("breakdown", {})
                w.writerow([r.get("_file"), r.get("usdot"), r["decision"], r.get("premium"), b.get("units"), b.get("unit_premium"),
                            b.get("relativity_product_capped"), ";".join(x["id"] for x in r.get("rules_fired", [])), ";".join(r.get("flags", [])), r.get("error")])
    if a.jsonl:
        with open(a.jsonl, "w") as f:
            for r in res: f.write(json.dumps({k: v for k, v in r.items() if k != "features"}, default=str) + "\n")

if __name__ == "__main__":
    main()
