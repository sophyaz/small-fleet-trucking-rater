#!/usr/bin/env bash
# Reproduce everything. Thin wrapper; the steps live in run_all.py so Windows and Unix run the same thing.
# Offline by default (samples/fixtures + data/cache); set FMCSA_WEBKEY in .env and RATER_OFFLINE=0 for live enrichment.
exec python run_all.py "$@"
