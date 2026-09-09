# Small-Fleet Trucking Rater

Primary auto liability rater for for-hire trucking carriers with 1–5 power units. Submission in (USDOT + drivers + VINs + radius + commodity), enrichment from FMCSA and NHTSA, loss-cost view, and a **price / refer / decline** decision with a full breakdown.

```
pip install -r requirements.txt
export RATER_OFFLINE=1                      # uses samples/fixtures; unset and set FMCSA_WEBKEY for live enrichment
python samples/make_synthetic_samples.py    # synthetic carriers + edge cases
python -m rater samples/submissions/00_established_clean_ia.json     # one submission, full breakdown
python -m rater.book samples/submissions --csv out.csv               # book check
./run_all.sh                                # everything: manual, ILFs, tornado, backtest, portfolio, tests, book check
```

Layout: `config/` (rates.yaml = the rating manual, rules.yaml = decline/refer rules, schema.json), `rater/` (ingest → enrich → features → rules → losscost → price; `book.py` CLI), `analysis/` (frequency tables from FMCSA bulk files, severity/ILFs, sensitivity, backtest, portfolio, manual renderer), `samples/`, `docs/` (RATIONALE, RATING_MANUAL, SOURCES, DEFENCE_NOTES, PRESENTATION_OUTLINE, CLAUDE_CODE_PROMPTS), `tests/`.

Live enrichment: `rater/enrich.py` calls QCMobile and vPIC, caches every response under `data/cache/`, and degrades to segment defaults (→ refer R02) on any failure. `analysis/build_sample_set.py` draws real carriers from the census file. Every value in `config/rates.yaml` is tagged [E]stimated / [S]elected / [B]enchmark; `VERIFY` marks anything I could not confirm against live data when this was built.

Reproducibility: `docs/SOURCES.md` lists every dataset with URL, status and what it feeds; `data/raw/` holds archived downloads (git-ignored).
