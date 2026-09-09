"""Tornado: one-at-a-time swings of key assumptions on the reference carrier's premium.
Run: python -m analysis.sensitivity [path/to/submission.json]"""
import copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rater.config import rates
from rater.price import price

SWINGS = [  # (label, path in cfg, low, high)
    ("Crash rate / unit-yr", ["loss_cost", "crash_rate_per_unit_year"], 0.036, 0.055),   # measured floor .. grossed-up + lag
    ("Crash->claim ratio", ["loss_cost", "crash_to_claim_ratio"], 1.2, 3.4),              # market back-out range, MARKET_BENCHMARK.md
    ("Injury mean severity", ["loss_cost", "severity", "injury", "mean"], 90000, 220000),
    ("Fatal tail alpha (lower=fatter)", ["loss_cost", "severity", "fatal", "alpha"], 1.3, 2.2),
    ("Fatal share of crashes", ["loss_cost", "severity", "fatal", "share"], 0.008, 0.03),
    ("Severity trend p.a.", ["loss_cost", "severity_trend_annual"], 0.03, 0.14),
    ("New-venture factor (<1y)", ["relativities", "authority_age_years", 0, "factor"], 1.3, 2.2),
    ("High-venue factor", ["relativities", "venue_state", "high", "factor"], 1.15, 1.7),
    ("Expense ratio", ["loadings", "expense_ratio"], 0.17, 0.30),
    ("Minimum premium / unit", ["loadings", "minimum_premium_per_unit"], 5000, 9000),
]

def setp(cfg, path, v):
    d = cfg
    for p in path[:-1]: d = d[p]
    d[path[-1]] = v

def main():
    sub_path = sys.argv[1] if len(sys.argv) > 1 else "samples/submissions/02_new_venture_ga.json"
    with open(sub_path) as f: sub = json.load(f)
    base_cfg = rates(); base = price(sub, base_cfg)["premium_if_written"]
    print(f"Reference: {sub.get('submission_id')}  base premium {base:,.0f}\n")
    out = []
    for label, path, lo, hi in SWINGS:
        c1, c2 = copy.deepcopy(base_cfg), copy.deepcopy(base_cfg); setp(c1, path, lo); setp(c2, path, hi)
        p1, p2 = price(sub, c1)["premium_if_written"], price(sub, c2)["premium_if_written"]
        out.append((label, p1 - base, p2 - base, lo, hi))
    out.sort(key=lambda r: -(abs(r[1]) + abs(r[2])))
    print(f"{'assumption':34} {'low':>10} {'high':>10}   swing")
    for label, d1, d2, lo, hi in out:
        bar = "#" * int(30 * (abs(d1) + abs(d2)) / (abs(out[0][1]) + abs(out[0][2]) or 1))
        print(f"{label:34} {d1:>+10,.0f} {d2:>+10,.0f}   {bar}   [{lo}..{hi}]")
    with open("data/derived/tornado.csv", "w") as f:
        f.write("assumption,delta_low,delta_high,low_value,high_value\n")
        for r in out: f.write(",".join(str(x) for x in r) + "\n")

if __name__ == "__main__":
    main()
