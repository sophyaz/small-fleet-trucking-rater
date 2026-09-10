"""Build data/census_slim.csv.gz -- the committable subset of the FMCSA census snapshot.

Why this exists: QCMobile does NOT return addDate, mcs150Date, mcs150Mileage or the HM/PC flags (see the schema
notes in rater/enrich.py). They come from the census file, which is 731 MB and gitignored. Without it, every
live-fetched carrier loses its registration date, is assumed 0.5 years old, picks up the 1.65 new-venture factor
and refers on R01 -- so a fresh clone would price a different book from the one the docs describe.

This writes the same columns rater/enrich.py indexes, for carriers in and just above our segment (1-6 power
units), gzipped. rater/enrich.py falls back to it when census.csv is absent, so a clone reproduces our answers.

    python -m analysis.build_census_slim [--max-units 6]

Re-run after re-pulling census.csv (SOURCES S3). Rows with no add_date are dropped: they carry nothing the
fallback needs that QCMobile does not already return.
"""
import argparse, csv, gzip, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from rater.enrich import CENSUS_COLS, CENSUS_CSV, CENSUS_SLIM   # the exact columns the runtime index expects

# Written empty to keep the sqlite schema identical while dropping the widest column: enrich.py takes the legal
# name from QCMobile's legalName, never from the census row. Blanking it saves ~30% of the compressed file.
BLANK_COLS = {"legal_name"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-units", type=float, default=6, help="keep carriers at or below this power-unit count")
    ap.add_argument("--out", default=CENSUS_SLIM)
    a = ap.parse_args()
    if not os.path.exists(CENSUS_CSV):
        print(f"missing {CENSUS_CSV} -- pull it with the Socrata URL in docs/SOURCES.md S3"); return 1

    kept = skipped_units = skipped_nodate = 0
    with open(CENSUS_CSV, newline="", encoding="utf-8", errors="replace") as fin, \
         gzip.open(a.out, "wt", newline="", encoding="utf-8", compresslevel=9) as fout:
        w = csv.writer(fout)
        w.writerow(CENSUS_COLS)
        for row in csv.DictReader(fin):
            try:
                units = float(row.get("nbr_power_unit") or 0)
            except (TypeError, ValueError):
                units = 0
            if units > a.max_units:
                skipped_units += 1; continue
            if not (row.get("add_date") or "").strip():
                skipped_nodate += 1; continue
            try:
                dot = int(row["dot_number"])
            except (KeyError, TypeError, ValueError):
                continue
            w.writerow((dot,) + tuple("" if c in BLANK_COLS else row.get(c) for c in CENSUS_COLS[1:]))
            kept += 1

    mb = os.path.getsize(a.out) / 1e6
    print(f"wrote {a.out}: {kept:,} rows, {mb:.1f} MB "
          f"(skipped {skipped_units:,} over {a.max_units:g} units, {skipped_nodate:,} with no add_date)")
    if mb > 40:
        print("!! over the 40 MB target for a committed file -- lower --max-units or drop columns")
    return 0

if __name__ == "__main__":
    sys.exit(main())
