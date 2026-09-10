"""Book check: python -m rater.book samples/submissions [--csv out.csv]

A file may hold one submission (JSON object), many (JSON array, .jsonl, or .csv with one row per carrier).
Anything unreadable becomes an error row rather than stopping the run."""
import argparse, csv as csvmod, glob, json, os, statistics, collections
from .price import price

EXTS = ("*.json", "*.jsonl", "*.ndjson", "*.csv")

def _err(name, msg):
    return {"submission_id": name, "_file": name, "decision": "error", "error": msg,
            "premium": None, "rules_fired": [], "flags": [], "breakdown": {}}

def _load(fp):
    """(list of submission dicts, error message or None). One file may carry many carriers."""
    ext = os.path.splitext(fp)[1].lower()
    try:
        if ext in (".jsonl", ".ndjson"):
            subs, bad = [], 0
            with open(fp, encoding="utf-8-sig") as f:
                for line in f:
                    if not line.strip(): continue
                    try: subs.append(json.loads(line))
                    except Exception: bad += 1
            if bad and not subs: return [], f"unreadable jsonl: {bad} bad lines, none parsed"
            return subs, (f"{bad} unparseable line{'s' if bad != 1 else ''} skipped" if bad else None)
        if ext == ".csv":
            with open(fp, newline="", encoding="utf-8-sig") as f:
                # ingest.py resolves header spellings (dot_number, vins, state, power_units, ...) via its alias table
                return [{k: v for k, v in row.items() if k and str(v).strip() != ""} for row in csvmod.DictReader(f)], None
        with open(fp, encoding="utf-8-sig") as f:
            data = json.load(f)
        return (data if isinstance(data, list) else [data]), None
    except Exception as e:
        return [], f"unreadable {ext.lstrip('.') or 'file'}: {e}"

def run(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for pat in EXTS: files += glob.glob(os.path.join(p, pat))
        else:
            files.append(p)
    results = []
    for fp in sorted(set(files)):
        name = os.path.basename(fp)
        subs, note = _load(fp)
        if not subs:
            results.append(_err(name, note or "no submissions in file")); continue
        for i, sub in enumerate(subs):
            r = price(sub if isinstance(sub, dict) else {})
            r["_file"] = name if len(subs) == 1 else f"{name}#{i}"
            if not r.get("submission_id") or r["submission_id"] == "sub-?":
                r["submission_id"] = r["_file"]
            if note:
                r.setdefault("flags", []).append(note)
                # Also carried structurally: a row silently dropped from a feed must show in the printed
                # summary, not only in a flags column nobody reads.
                r["_file_note"] = f"{name}: {note}"
            results.append(r)
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
    notes = sorted({r["_file_note"] for r in results if r.get("_file_note")})
    if notes:
        lines += ["", f"Files read only in part ({len(notes)}) - these rows never reached the rater:"] + [f"  {x}" for x in notes]
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
