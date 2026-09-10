"""Reproduce everything, on any OS:  python run_all.py

Offline by default (RATER_OFFLINE=1 -> samples/fixtures + data/cache only). For live enrichment set FMCSA_WEBKEY
in .env and run with RATER_OFFLINE=0. Steps mirror the old run_all.sh: synthetic samples, manual render, ILFs,
tornado, backtest, portfolio, tests, then seven book checks - synthetic, market benchmark, reviewer formats,
the cold-start holdout and operating draws, the curveball inputs, and the real census draw."""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
env = {**os.environ}
env.setdefault("RATER_OFFLINE", "1")
env.setdefault("PYTHONIOENCODING", "utf-8")   # Windows console is cp1252; the manual renderer prints Σ / ≤

STEPS = [
    ("synthetic samples", [PY, "samples/make_synthetic_samples.py"]),
    ("benchmark samples", [PY, "samples/make_benchmark_samples.py"]),
    ("render manual", [PY, "-m", "analysis.render_manual"]),
    ("severity / ILFs", [PY, "-m", "analysis.fit_severity"]),
    ("tornado", [PY, "-m", "analysis.sensitivity"]),
    ("synthetic backtest", [PY, "-m", "analysis.synthetic_backtest"]),
    ("portfolio", [PY, "-m", "analysis.portfolio"]),
    ("tests", [PY, "-m", "pytest", "-q", "tests"]),
    ("book check: synthetic", [PY, "-m", "rater.book", "samples/submissions", "--csv", "data/derived/book_check.csv", "--jsonl", "data/derived/book_check.jsonl"]),
    ("book check: market benchmark", [PY, "samples/make_benchmark_samples.py", "--run"]),
    # reviewer-shaped inputs: array / jsonl / csv / wrapped / spreadsheet exports, plus one deliberately broken file
    ("book check: reviewer formats", [PY, "-m", "rater.book", "samples/reviewer_formats",
                                      "--csv", "data/derived/book_check_formats.csv"]),
    # cold start: carriers the rater had never seen when the rules were written. Tracks A and B are drawn
    # outside the 10 focus states of the real sample; track C keeps only carriers that look like they operate.
    ("book check: cold-start holdout", [PY, "-m", "rater.book", "samples/submissions_holdout",
                                        "--csv", "data/derived/book_check_holdout.csv"]),
    ("book check: operating draw", [PY, "-m", "rater.book", "samples/submissions_operating",
                                    "--csv", "data/derived/book_check_operating.csv"]),
    # deliberately hostile inputs: broker csv, nested arrays, a jsonl with an unparseable line, two empty files
    ("book check: curveball inputs", [PY, "-m", "rater.book", "samples/submissions_curveball",
                                      "--csv", "data/derived/book_check_curveball.csv"]),
]
if os.path.isdir(os.path.join(ROOT, "samples", "submissions_real")):
    STEPS.append(("book check: real carriers", [PY, "-m", "rater.book", "samples/submissions_real", "--csv", "data/derived/book_check_real.csv", "--jsonl", "data/derived/book_check_real.jsonl"]))
else:
    print("(no samples/submissions_real - run analysis/build_sample_set.py after downloading census.csv)")

def main():
    failed = []
    for name, cmd in STEPS:
        print(f"\n{'=' * 70}\n{name}: {' '.join(os.path.relpath(c, ROOT) if os.path.isabs(c) else c for c in cmd)}\n{'=' * 70}", flush=True)
        rc = subprocess.run(cmd, cwd=ROOT, env=env).returncode
        if rc != 0:
            failed.append(name); print(f"!! step failed (exit {rc}): {name}", flush=True)
    print("\n" + ("ALL STEPS OK" if not failed else "FAILED: " + ", ".join(failed)))
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
