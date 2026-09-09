#!/usr/bin/env bash
# Reproduce everything. Offline mode uses samples/fixtures; set FMCSA_WEBKEY and unset RATER_OFFLINE for live enrichment.
set -e
export RATER_OFFLINE=${RATER_OFFLINE:-1}
python samples/make_synthetic_samples.py
python -m analysis.render_manual > /dev/null
python -m analysis.fit_severity
python -m analysis.sensitivity
python -m analysis.synthetic_backtest
python -m analysis.portfolio
python -m pytest -q tests
python -m rater.book samples/submissions --csv data/derived/book_check.csv --jsonl data/derived/book_check.jsonl
[ -d samples/submissions_real ] && python -m rater.book samples/submissions_real --csv data/derived/book_check_real.csv || echo "(no real sample set yet — run analysis/build_sample_set.py after downloading census.csv)"
